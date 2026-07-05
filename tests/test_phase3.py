from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from llm.llm_client import LLMClient
from llm.config import create_llm_client, default_ai_settings, load_ai_settings, save_ai_settings
from polynexus.gui.i18n import get_language, set_language, tr
from rag.advisor import Advisor
from rag.indexer import RagIndexer
from rag.polymer_knowledge import load_polymer_knowledge
from rag.prompt_builder import PromptBuilder
from rag.retriever import RagRetriever
from tests.eval.audit_reporter import AuditReporter
from tests.eval.runner import EvalRunner
from tests.eval.synth_generator import SynthGenerator


def _local_tmp_dir() -> Path:
    root = Path(__file__).resolve().parent / "_tmp_phase3"
    path = root / uuid.uuid4().hex
    path.mkdir(parents=True)
    return path


def _make_results(tmp_dir: Path) -> tuple[Path, Path]:
    eval_root = tmp_dir / "eval"
    SynthGenerator(output_dir=eval_root, seed=42).generate_all()
    reporter = AuditReporter(EvalRunner(eval_root=eval_root, project_root=tmp_dir))
    results_dir = eval_root / "results"
    reporter.batch_run(str(eval_root / "cases"), str(results_dir))
    return eval_root, results_dir


def _indexed_db(tmp_dir: Path) -> tuple[Path, Path, Path]:
    eval_root, results_dir = _make_results(tmp_dir)
    db_path = tmp_dir / "rag_db"
    count = RagIndexer(db_path=str(db_path)).index_all(str(results_dir))
    assert count == len(SynthGenerator.CASE_IDS)
    return eval_root, results_dir, db_path


def test_01_indexer_indexes_all_synthetic_cases() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        _, results_dir = _make_results(tmp_dir)
        count = RagIndexer(db_path=str(tmp_dir / "rag_db")).index_all(str(results_dir))
        assert count == len(SynthGenerator.CASE_IDS)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_02_retriever_returns_top_3_results() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        _, _, db_path = _indexed_db(tmp_dir)
        results = RagRetriever(db_path=str(db_path)).retrieve("PA6 alpha WAXS crystallinity peak", "WAXS", top_k=3)
        assert len(results) == 3
        assert all("case_id" in item and "document" in item and "metadata" in item for item in results)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_03_retriever_prioritizes_matching_technique() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        _, _, db_path = _indexed_db(tmp_dir)
        results = RagRetriever(db_path=str(db_path)).retrieve("polyamide melting and crystallinity", "DSC", top_k=3)
        assert len(results) == 3
        assert all(item["metadata"]["technique"] == "DSC" for item in results)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_04_prompt_builder_includes_history_and_current_sample() -> None:
    prompt = PromptBuilder().build(
        {
            "technique": "WAXS",
            "polymer_name": "PA6",
            "params": {"Xc_pct": 44.2},
            "residuals_pattern": "在 2θ=20.0° 附近存在系统性正残差",
            "polymer_knowledge": load_polymer_knowledge("PA6"),
        },
        [
            {
                "case_id": "waxs_synth_pa6_alpha",
                "document": "技术: WAXS | 聚合物: PA6 | 评分: 1.0",
                "score": 0.95,
                "metadata": {"technique": "WAXS"},
            }
        ],
    )
    assert "[SYSTEM]" in prompt
    assert "历史参考案例" in prompt
    assert "当前状态" in prompt
    assert "调参优先级" in prompt
    assert "waxs_synth_pa6_alpha" in prompt
    assert "PA6" in prompt
    assert "系统性正残差" in prompt
    assert "标准结晶度范围 35-55%" in prompt


def test_05_no_api_key_returns_false(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = LLMClient(timeout=1)
    assert client.is_available() is False


def test_06_advisor_falls_back_to_mock_when_llm_offline() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        _, _, db_path = _indexed_db(tmp_dir)
        advisor = Advisor(
            retriever=RagRetriever(db_path=str(db_path)),
            llm_client=LLMClient(base_url="http://127.0.0.1:9/v1", timeout=1),
        )
        advice = advisor.advise({"technique": "WAXS", "polymer_name": "PA6", "params": {"Xc_pct": 44.0}})
        assert advice["llm_used"] is False
        assert advice["assessment"] in {"PASS", "WARN", "FAIL"}
        assert advice["suggestions"]
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_07_advisor_output_matches_expected_schema() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        _, _, db_path = _indexed_db(tmp_dir)
        advisor = Advisor(
            retriever=RagRetriever(db_path=str(db_path)),
            llm_client=LLMClient(base_url="http://127.0.0.1:9/v1", timeout=1),
        )
        advice = advisor.advise({"technique": "IR", "polymer_name": "PA6", "params": {"peak_wavenumbers": [1635]}})
        assert set(advice) == {
            "assessment",
            "confidence",
            "reasoning",
            "changes",
            "expected_improvement",
            "risk",
            "suggestions",
            "reference_cases",
            "converge",
            "llm_used",
        }
        assert isinstance(advice["confidence"], float)
        assert isinstance(advice["changes"], dict)
        assert isinstance(advice["expected_improvement"], dict)
        assert isinstance(advice["suggestions"], list)
        assert isinstance(advice["reference_cases"], list)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_08_end_to_end_index_retrieve_advise() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        eval_root, _, db_path = _indexed_db(tmp_dir)
        case_path = eval_root / "cases" / "synth" / "waxs_synth_pa6_alpha.json"
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        retriever = RagRetriever(db_path=str(db_path))
        retrieved = retriever.retrieve("PA6 alpha WAXS", "WAXS", top_k=3)
        advisor = Advisor(
            retriever=retriever,
            llm_client=LLMClient(base_url="http://127.0.0.1:9/v1", timeout=1),
        )
        advice = advisor.advise(payload)
        assert len(retrieved) == 3
        assert advice["assessment"] in {"PASS", "WARN", "FAIL"}
        assert advice["reference_cases"]
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_09_env_example_documents_deepseek_key() -> None:
    env_example = Path(__file__).resolve().parent.parent / ".env.example"
    assert env_example.exists()
    content = env_example.read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY=your_deepseek_api_key_here" in content
    assert "OPENAI_API_KEY=your_openai_api_key_here" in content


def test_10_llm_client_reads_api_key_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "unit-test-key")
    client = LLMClient(base_url="http://127.0.0.1:9/v1", timeout=1)
    assert client.api_key == "unit-test-key"
    assert client.is_available() is True


def test_11_llm_client_reads_openai_api_key_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    client = LLMClient(base_url="https://api.openai.com/v1", model="gpt-5.4-mini", timeout=1)
    assert client.provider == "openai"
    assert client.api_key == "openai-test-key"
    assert client.is_available() is True


def test_12_ai_settings_round_trip_and_client_factory() -> None:
    class FakeSettings:
        def __init__(self):
            self.data = {}

        def value(self, key, default=None):
            return self.data.get(key, default)

        def setValue(self, key, value):
            self.data[key] = value

    settings = FakeSettings()
    save_ai_settings(
        settings,
        {
            "provider": "openai",
            "api_key": "abc123",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-5.4-mini",
            "allow_mock": False,
        },
    )
    loaded = load_ai_settings(settings)
    assert loaded["provider"] == "openai"
    assert loaded["api_key"] == "abc123"
    assert loaded["base_url"] == "https://api.openai.com/v1"
    assert loaded["model"] == "gpt-5.4-mini"
    assert loaded["allow_mock"] is False

    client = create_llm_client(loaded, timeout=1)
    assert client.provider == "openai"
    assert client.base_url == "https://api.openai.com/v1"
    assert client.model == "gpt-5.4-mini"
    assert client.api_key == "abc123"


def test_13_default_ai_settings_prefers_openai_when_only_openai_env(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-only-key")
    defaults = default_ai_settings()
    assert defaults["provider"] == "openai"
    assert defaults["base_url"] == "https://api.openai.com/v1"
    assert defaults["model"] == "gpt-5.4-mini"


def test_14_settings_dialog_exposes_both_ai_providers():
    from PySide6.QtWidgets import QApplication
    from polynexus.gui.widgets.settings_dialog import SettingsDialog

    app = QApplication.instance() or QApplication([])
    dlg = SettingsDialog()
    try:
        assert dlg._ai_provider_combo.count() == 2
        assert dlg._ai_provider_combo.itemData(0) == "deepseek"
        assert dlg._ai_provider_combo.itemData(1) == "openai"
        snapshot = dlg._collect_ai_settings()
        assert snapshot["provider"] in {"deepseek", "openai"}
    finally:
        dlg.deleteLater()
        app.processEvents()


def test_15_chinese_history_tab_label_is_present() -> None:
    previous = get_language()
    try:
        set_language("zh")
        assert tr("TAB_HISTORY") == "历史"
    finally:
        set_language(previous)
