from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class RagIndexer:
    COLLECTION_NAME = "polynexus_evals"
    FALLBACK_STORE = "fallback_store.json"

    def __init__(self, db_path: str = "rag/chroma_db"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.collection = None
        self.backend = "fallback"
        self._init_chroma()

    def index_all(self, results_dir: str) -> int:
        records = self._load_records(results_dir)
        deduped = {record["case_id"]: record for record in records}
        if not deduped:
            return 0

        ids = []
        documents = []
        metadatas = []
        for record in deduped.values():
            ids.append(str(record["case_id"]))
            documents.append(self._to_document(record))
            metadatas.append(self._metadata(record))

        if self.collection is not None:
            try:
                self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
                self.backend = "chroma"
                return len(ids)
            except Exception:
                self.collection = None
                self.backend = "fallback"

        self._fallback_upsert(ids, documents, metadatas)
        return len(ids)

    def _to_document(self, result: dict[str, Any]) -> str:
        case = result.get("_case", {})
        output = result.get("output_parameters", {})
        technique = str(result.get("technique") or case.get("technique", "")).upper()
        polymer = str(case.get("polymer_name") or result.get("polymer_name") or "unknown")
        label = self._label(result)
        score = float(result.get("composite", result.get("score", 0.0)))
        params = self._params_summary(output)
        return (
            f"技术: {technique} | 聚合物: {polymer} | "
            f"参数: {params} | 评分: {score:.3f} | 标注: {label}"
        )

    def _init_chroma(self) -> None:
        try:
            import chromadb
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

            client = chromadb.PersistentClient(path=str(self.db_path))
            self.collection = client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=DefaultEmbeddingFunction(),
            )
            self.backend = "chroma"
        except Exception:
            self.collection = None
            self.backend = "fallback"

    def _load_records(self, results_dir: str) -> list[dict[str, Any]]:
        paths = self._result_paths(Path(results_dir))
        records: list[dict[str, Any]] = []
        for path in paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            records.extend(self._records_from_payload(payload))
        return records

    def _result_paths(self, results_dir: Path) -> list[Path]:
        paths: list[Path] = []
        if results_dir.exists():
            paths = sorted(path for path in results_dir.glob("*.json") if path.is_file())
        if paths:
            return paths

        sibling_reports = results_dir.parent / "reports"
        if sibling_reports.exists():
            paths = sorted(path for path in sibling_reports.glob("results_*.json") if path.is_file())
        return paths

    def _records_from_payload(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict) and "results" in payload:
            cases = {case.get("case_id"): case for case in payload.get("cases", []) if isinstance(case, dict)}
            records = []
            for result in payload.get("results", []):
                if not isinstance(result, dict) or "case_id" not in result:
                    continue
                record = dict(result)
                record["_case"] = cases.get(result["case_id"], {})
                records.append(record)
            return records
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict) and "case_id" in item]
        if isinstance(payload, dict) and "case_id" in payload:
            return [payload]
        return []

    def _metadata(self, record: dict[str, Any]) -> dict[str, Any]:
        case = record.get("_case", {})
        return {
            "technique": str(record.get("technique") or case.get("technique", "")).upper(),
            "polymer_name": str(case.get("polymer_name") or record.get("polymer_name") or "unknown"),
            "score": float(record.get("composite", record.get("score", 0.0))),
            "label": self._label(record),
        }

    def _label(self, record: dict[str, Any]) -> str:
        case = record.get("_case", {})
        explicit = case.get("human_annotation") or record.get("label")
        if explicit:
            return str(explicit).upper()
        composite = float(record.get("composite", 0.0))
        phys = float(record.get("phys_score", 1.0))
        if phys < 1.0 or composite < 0.60:
            return "FAIL"
        if composite < 0.85:
            return "WARN"
        return "PASS"

    def _params_summary(self, output: dict[str, Any]) -> str:
        if not output:
            return "none"
        parts = []
        for name in ("Xc_pct", "Tm_peak_C", "Tg_C", "Tc_peak_C", "L_nm", "lc_nm", "phi_c", "Rg_nm"):
            if name in output:
                parts.append(f"{name}={output[name]}")
        for name in ("peak_centers", "peak_wavenumbers", "peak_shifts"):
            if name in output:
                parts.append(f"{name}={output[name]}")
        return ", ".join(parts) if parts else json.dumps(output, ensure_ascii=False, sort_keys=True)

    def _fallback_upsert(self, ids: list[str], documents: list[str], metadatas: list[dict[str, Any]]) -> None:
        store_path = self.db_path / self.FALLBACK_STORE
        existing: dict[str, dict[str, Any]] = {}
        if store_path.exists():
            payload = json.loads(store_path.read_text(encoding="utf-8"))
            existing = {item["id"]: item for item in payload.get("records", [])}
        for doc_id, document, metadata in zip(ids, documents, metadatas):
            existing[doc_id] = {"id": doc_id, "document": document, "metadata": metadata}
        store_path.write_text(
            json.dumps({"collection": self.COLLECTION_NAME, "records": list(existing.values())}, indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Index PolyNexus eval results into the RAG database.")
    parser.add_argument("--results-dir", default="tests/eval/results/", help="Directory containing result JSON files.")
    parser.add_argument("--db-path", default="rag/chroma_db", help="Persistent ChromaDB path.")
    args = parser.parse_args(argv)

    indexer = RagIndexer(db_path=args.db_path)
    count = indexer.index_all(args.results_dir)
    print(f"索引 {count} 条记录 -> {indexer.db_path} OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
