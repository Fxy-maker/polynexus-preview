from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from polynexus.core.engine import get_engine
from polynexus.core.saxs_export_bundle import export_saxs_bundle


def _real_saxs_modes() -> tuple[tuple[str, Path], ...]:
    repository_root = Path(__file__).resolve().parents[1]
    data_root = next(
        (candidate / "saxs")
        for candidate in repository_root.iterdir()
        if candidate.is_dir() and (candidate / "saxs").is_dir()
    )
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


def _assert_projection_subset(projected: Any, authoritative: Any, *, path: str) -> None:
    assert isinstance(projected, Mapping), path
    assert isinstance(authoritative, Mapping), path
    for key, value in projected.items():
        assert key in authoritative, f"{path}.{key} missing from authoritative evidence"
        expected = authoritative[key]
        if isinstance(value, Mapping):
            _assert_projection_subset(value, expected, path=f"{path}.{key}")
        else:
            assert value == expected, f"{path}.{key} changed in Figure projection"


@pytest.mark.parametrize(
    "mode,source",
    _real_saxs_modes(),
    ids=lambda item: item if isinstance(item, str) else str(item),
)
def test_real_saxs_method_evidence_is_preserved_across_parameter_figure_and_export(
    tmp_path: Path,
    mode: str,
    source: Path,
) -> None:
    if not source.exists():
        pytest.skip(f"real SAXS fixture unavailable: {source}")

    engine = get_engine("saxs", config={"fig_format": "png"}, submodule_id=mode)
    result = engine.run_pipeline(str(source), str(tmp_path / "figures"))
    authoritative = result.parameters.get("metric_evidence")
    assert isinstance(authoritative, Mapping)
    json.dumps(authoritative, allow_nan=False)

    mode_name = mode.rsplit(".", 1)[-1]
    bundle = export_saxs_bundle(engine, str(tmp_path / "bundle"))
    assert bundle.status == "ok"
    quality = json.loads(
        (Path(bundle.root) / "quality_evidence.json").read_text(encoding="utf-8")
    )
    mode_quality = quality[mode_name]
    exported = mode_quality["metric_evidence"]
    assert exported == authoritative
    json.dumps(quality, allow_nan=False)

    frame_authoritative = {
        int(frame["frame_index"]): frame["metric_evidence"]
        for frame in mode_quality.get("frames", [])
        if isinstance(frame, Mapping) and isinstance(frame.get("metric_evidence"), Mapping)
    }

    manifest_path = Path(str(result.metadata["figure_manifest"]))
    documents = tuple(manifest_path.parent.glob("figures/*/figure.pnfig.json"))
    assert documents
    seen_projection = False
    for document_path in documents:
        document = json.loads(document_path.read_text(encoding="utf-8"))
        provenance = document["recipe"]["evidence"]["quality_provenance"]
        series_metric = provenance.get("series_record", {}).get("metric_evidence")
        if isinstance(series_metric, Mapping) and series_metric:
            _assert_projection_subset(series_metric, authoritative, path="series.metric_evidence")
            seen_projection = True
        for frame in provenance.get("frame_records", []):
            frame_metric = frame.get("metric_evidence")
            if isinstance(frame_metric, Mapping) and frame_metric:
                if mode_name == "static":
                    frame_source = authoritative
                else:
                    frame_source = frame_authoritative.get(int(frame["frame_index"]))
                _assert_projection_subset(
                    frame_metric,
                    frame_source,
                    path="frame.metric_evidence",
                )
                seen_projection = True
        json.dumps(document, allow_nan=False)
    assert seen_projection
