from __future__ import annotations

import json
from pathlib import Path

import pytest

from polynexus.core.engine import get_engine
from polynexus.core.saxs_export_bundle import export_saxs_bundle


def _real_saxs_modes() -> tuple[tuple[str, Path], ...]:
    data_root = Path(__file__).resolve().parents[1] / "测试数据" / "saxs"
    static = next(data_root.rglob("8-000-s_0_00000_with_mask.edf"), None)
    temperature_frame = next(data_root.rglob("PA6-250-170-S_0_00000.edf"), None)
    strain_frame = next(data_root.rglob("8-000-s_0_00000_with_mask.edf"), None)
    return tuple(
        (mode, source)
        for mode, source in (
            ("saxs.static", static),
            ("saxs.temperature", temperature_frame.parent if temperature_frame else None),
            ("saxs.strain", strain_frame.parent if strain_frame else None),
        )
        if source is not None
    )


@pytest.mark.parametrize(
    "mode,source",
    _real_saxs_modes(),
    ids=lambda item: item if isinstance(item, str) else str(item),
)
def test_real_saxs_audit_is_consistent_across_parameter_figure_and_export_surfaces(
    tmp_path: Path,
    mode: str,
    source: Path,
) -> None:
    if not source.exists():
        pytest.skip(f"real SAXS fixture unavailable: {source}")

    engine = get_engine("saxs", config={"fig_format": "png"}, submodule_id=mode)
    result = engine.run_pipeline(str(source), str(tmp_path / "figures"))
    audit = result.parameters["scientific_acceptance_audit"]
    json.dumps(audit, allow_nan=False)

    manifest_root = Path(str(result.metadata["figure_manifest"])).parent
    documents = tuple(manifest_root.glob("figures/*/figure.pnfig.json"))
    assert documents
    for document_path in documents:
        document = json.loads(document_path.read_text(encoding="utf-8"))
        figure_audit = document["recipe"]["evidence"]["quality_provenance"].get(
            "scientific_acceptance_audit"
        )
        assert figure_audit == audit
        json.dumps(document, allow_nan=False)

    bundle = export_saxs_bundle(engine, str(tmp_path / "bundle"))
    assert bundle.status == "ok"
    bundle_root = Path(bundle.root)
    quality = json.loads((bundle_root / "quality_evidence.json").read_text(encoding="utf-8"))
    assert quality["scientific_acceptance_audit"] == audit
    manifest = json.loads((bundle_root / "bundle_manifest.json").read_text(encoding="utf-8"))
    assert manifest["files"]["quality_evidence"] == "quality_evidence.json"
    if mode == "saxs.temperature":
        assert result.validation_passed is False
