from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from .indexer import RagIndexer


# ── BM25 helper (pure Python, no new dependencies) ──────────────────────
class _BM25:
    """Minimal BM25 using only stdlib + math."""

    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.N = len(corpus)
        self.avgdl = sum(len(d) for d in corpus) / max(self.N, 1)
        # Document frequencies
        df: dict[str, int] = {}
        for doc in corpus:
            for token in set(doc):
                df[token] = df.get(token, 0) + 1
        # IDF
        self._idf: dict[str, float] = {}
        for token, freq in df.items():
            self._idf[token] = math.log((self.N - freq + 0.5) / (freq + 0.5) + 1.0)

    def scores(self, query_tokens: list[str]) -> list[float]:
        result: list[float] = []
        for doc in self.corpus:
            dl = len(doc)
            s = 0.0
            for token in query_tokens:
                idf = self._idf.get(token, 0.0)
                if idf == 0.0:
                    continue
                tf = doc.count(token)
                num = tf * (self.k1 + 1.0)
                den = tf + self.k1 * (1.0 - self.b + self.b * dl / self.avgdl)
                s += idf * num / max(den, 1e-12)
            result.append(s)
        return result


# ── Tokenizer ──────────────────────────────────────────────────────────
_TOKEN_RE = re.compile(r"[a-zA-Z0-9_.+-]+|[\u4e00-\u9fff]")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


# ── Retriever ──────────────────────────────────────────────────────────
class RagRetriever:
    # Re-ranking weights
    _RERANK_POOL_FACTOR = 3
    _RERANK_ORIGINAL_WEIGHT = 0.7
    _BOOST_TECHNIQUE = 0.15
    _BOOST_POLYMER = 0.10
    _BOOST_LABEL_PASS = 0.05
    _BOOST_LABEL_FAIL = -0.05

    _CACHE_MAX = 128

    def __init__(self, db_path: str = "rag/chroma_db"):
        self.db_path = Path(db_path)
        self.collection = None
        self.backend = "fallback"
        self._cache: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
        self._init_chroma()

    # ── Public API ─────────────────────────────────────────────────────
    def retrieve(
        self,
        query: str,
        technique: str,
        top_k: int = 3,
        *,
        polymer_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve top_k similar cases, with re-ranking and caching."""
        technique_key = technique.upper()

        # Cache lookup
        cache_key = (query, technique_key, top_k)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        pool_size = max(top_k * self._RERANK_POOL_FACTOR, top_k)
        if self.collection is not None:
            try:
                pool = self._retrieve_chroma_pool(query, technique_key, pool_size)
            except Exception:
                self.collection = None
                self.backend = "fallback"
                pool = self._retrieve_fallback_pool(query, technique_key, pool_size)
        else:
            pool = self._retrieve_fallback_pool(query, technique_key, pool_size)

        result = self._rerank(pool, technique_key, polymer_name or "", top_k)
        self._cache[cache_key] = result
        self._evict_if_full()
        return result

    # ── ChromaDB path (vector search — unchanged embedding) ────────────
    def _init_chroma(self) -> None:
        try:
            import chromadb
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

            client = chromadb.PersistentClient(path=str(self.db_path))
            self.collection = client.get_or_create_collection(
                name=RagIndexer.COLLECTION_NAME,
                embedding_function=DefaultEmbeddingFunction(),
            )
            self.backend = "chroma"
        except Exception:
            self.collection = None
            self.backend = "fallback"

    def _retrieve_chroma_pool(
        self, query: str, technique: str, pool_size: int
    ) -> list[dict[str, Any]]:
        selected = self._query_chroma(query, pool_size, where={"technique": technique})
        if len(selected) < pool_size:
            seen = {item["case_id"] for item in selected}
            for item in self._query_chroma(
                query, max(pool_size * 2, pool_size), where=None
            ):
                if item["case_id"] not in seen:
                    selected.append(item)
                    seen.add(item["case_id"])
                if len(selected) >= pool_size:
                    break
        return selected

    def _query_chroma(
        self, query: str, top_k: int, where: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        response = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = response.get("ids", [[]])[0]
        documents = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]
        items: list[dict[str, Any]] = []
        for case_id, document, metadata, distance in zip(
            ids, documents, metadatas, distances
        ):
            items.append(
                {
                    "case_id": case_id,
                    "document": document,
                    "score": 1.0 / (1.0 + float(distance)),
                    "metadata": metadata or {},
                }
            )
        return items

    # ── Fallback / BM25 path ───────────────────────────────────────────
    def _retrieve_fallback_pool(
        self, query: str, technique: str, pool_size: int
    ) -> list[dict[str, Any]]:
        records = self._load_fallback_records()
        if not records:
            return []

        doc_texts = [rec["document"] for rec in records]
        doc_tokens = [_tokenize(text) for text in doc_texts]
        bm25 = _BM25(doc_tokens)
        query_tokens = _tokenize(query)
        scores = bm25.scores(query_tokens)

        ranked = sorted(
            (
                {
                    "case_id": rec["id"],
                    "document": rec["document"],
                    "score": scores[i],
                    "metadata": rec.get("metadata", {}),
                }
                for i, rec in enumerate(records)
            ),
            key=lambda item: item["score"],
            reverse=True,
        )
        return ranked[:pool_size]

    def _load_fallback_records(self) -> list[dict[str, Any]]:
        store_path = self.db_path / RagIndexer.FALLBACK_STORE
        if not store_path.exists():
            return []
        payload = json.loads(store_path.read_text(encoding="utf-8"))
        return [item for item in payload.get("records", []) if isinstance(item, dict)]

    # ── Re-ranking ─────────────────────────────────────────────────────
    def _rerank(
        self,
        pool: list[dict[str, Any]],
        technique: str,
        polymer_name: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        if not pool:
            return []

        polymer_key = (polymer_name or "").strip().lower().replace("_", "-")

        for item in pool:
            meta = item.get("metadata", {}) or {}
            boost = 0.0

            # Technique match
            meta_tech = str(meta.get("technique", "")).upper()
            if meta_tech == technique:
                boost += self._BOOST_TECHNIQUE

            # Polymer match (fuzzy — substring in either direction)
            meta_poly = (
                str(meta.get("polymer_name", ""))
                .strip()
                .lower()
                .replace("_", "-")
            )
            if polymer_key and meta_poly and (
                polymer_key == meta_poly
                or polymer_key in meta_poly
                or meta_poly in polymer_key
            ):
                boost += self._BOOST_POLYMER

            # Label boost
            label = str(meta.get("label", "")).upper()
            if label == "PASS":
                boost += self._BOOST_LABEL_PASS
            elif label == "FAIL":
                boost += self._BOOST_LABEL_FAIL

            # Composite score
            item["score"] = (
                item.get("score", 0.0) * self._RERANK_ORIGINAL_WEIGHT + boost
            )

        pool.sort(key=lambda item: item["score"], reverse=True)
        return pool[:top_k]

    # ── Cache eviction ─────────────────────────────────────────────────
    def _evict_if_full(self) -> None:
        if len(self._cache) <= self._CACHE_MAX:
            return
        # Evict oldest half
        to_remove = list(self._cache.keys())[: self._CACHE_MAX // 2]
        for k in to_remove:
            del self._cache[k]
