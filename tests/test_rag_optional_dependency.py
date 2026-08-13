from __future__ import annotations

import builtins
from pathlib import Path
import tomllib

from rag.polymer_knowledge import load_polymer_knowledge
from rag.retriever import RagRetriever


def test_vector_backend_is_an_optional_install_extra() -> None:
    payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = payload["project"]["dependencies"]

    assert not any(str(value).startswith("chromadb") for value in dependencies)
    assert any(str(value).startswith("chromadb") for value in payload["project"]["optional-dependencies"]["rag"])


def test_retriever_uses_bm25_when_vector_backend_is_unavailable(tmp_path, monkeypatch) -> None:
    original_import = builtins.__import__

    def blocked_chroma_import(name, *args, **kwargs):
        if name == "chromadb" or name.startswith("chromadb."):
            raise ModuleNotFoundError("chromadb disabled")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_chroma_import)
    retriever = RagRetriever(db_path=str(tmp_path / "optional-rag"))

    assert retriever.backend == "fallback"
    assert retriever.retrieve("PA6 crystallization", "DSC") == []

    from polynexus.core.engine import get_engine

    assert get_engine("dsc") is not None


def test_polymer_reference_tables_remain_available_without_vector_backend() -> None:
    knowledge = load_polymer_knowledge("PA6")

    assert knowledge["name"]
    assert knowledge["ir"]["key_bands"]
