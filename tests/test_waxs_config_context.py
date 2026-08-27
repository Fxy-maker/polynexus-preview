from __future__ import annotations

from pathlib import Path
from polynexus.core.compute import ComputeRunService
from polynexus.core.waxs import WAXSEngine
from polynexus.core.waxs_engine import WAXSConfig


class _EmptyResult:
    parameters = {}
    figures = {}
    metadata = {}


class _FakeWAXSEngine:
    def __init__(self) -> None:
        self._waxs_config = WAXSConfig()
        self.calls = 0

    def run_pipeline(self, path: str, output_dir: str, **options: object) -> object:
        self.calls += 1
        return _EmptyResult()


def test_waxs_engine_preserves_supplied_config() -> None:
    config = WAXSConfig(polymer_type="PA6_alpha", peak_distance=1.7)

    engine = WAXSEngine(config=config)

    assert engine._waxs_config is config
    assert engine._waxs_config.polymer_type == "PA6_alpha"
    assert engine._waxs_config.peak_distance == 1.7


def test_compute_run_projects_explicit_waxs_context_hint(tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("two_theta,intensity\n20,1\n21,2\n", encoding="utf-8")
    engine = _FakeWAXSEngine()

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="waxs",
        path=source,
        output_dir=tmp_path / "out",
        project_context={
            "schema": "project-context.v1",
            "techniques": {"waxs": {"polymer_type": "PA6_alpha"}},
        },
    )

    assert run.status == "completed"
    assert engine._waxs_config.polymer_type == "PA6_alpha"
    assert engine.calls == 1


def test_explicit_waxs_config_wins_over_context_hint(tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("two_theta,intensity\n20,1\n21,2\n", encoding="utf-8")
    engine = _FakeWAXSEngine()
    engine._waxs_config.polymer_type = "PEEK"

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="waxs",
        path=source,
        output_dir=tmp_path / "out",
        project_context={
            "schema": "project-context.v1",
            "techniques": {"waxs": {"polymer_type": "PA6_alpha"}},
        },
    )

    assert run.status == "completed"
    assert engine._waxs_config.polymer_type == "PEEK"


def test_invalid_waxs_context_hint_blocks_provider(tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("two_theta,intensity\n20,1\n21,2\n", encoding="utf-8")
    engine = _FakeWAXSEngine()

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="waxs",
        path=source,
        output_dir=tmp_path / "out",
        project_context={
            "schema": "project-context.v1",
            "techniques": {"waxs": {"polymer_type": 123}},
        },
    )

    assert run.status == "needs_input"
    assert run.reasons == ("project_context_invalid",)
    assert engine.calls == 0
