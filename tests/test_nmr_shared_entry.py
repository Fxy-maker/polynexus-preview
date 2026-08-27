from __future__ import annotations

from polynexus.core.canonical_experiments import default_converter_registry
from polynexus.core.compute.service import ComputeRunService


class _EmptyResult:
    parameters: dict = {}
    figures: dict = {}
    metadata: dict = {}


class _FakeEngine:
    def __init__(self) -> None:
        self.result = _EmptyResult()
        self.calls: list[tuple[str, str, dict]] = []

    def run_pipeline(self, path: str, output_dir: str, **options):
        self.calls.append((path, output_dir, options))
        return self.result


def test_registry_converts_nmr_ppm_table_to_material_neutral_template(tmp_path) -> None:
    source = tmp_path / "spectrum.csv"
    source.write_text("ppm,intensity\n10,0.2\n5,0.8\n", encoding="utf-8")

    outcome = default_converter_registry().convert_path(
        source, technique="nmr", source_artifact_id="nmr-source"
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "nmr.spectrum.v1"
    assert outcome.template.measurements[0].units["x"] == "ppm"
    assert outcome.template.measurements[0].family == "spectrum_1d"


def test_registry_keeps_opaque_nmr_fid_and_vendor_directories_replayable(tmp_path) -> None:
    fid = tmp_path / "fid"
    fid.write_bytes(b"opaque-fid")
    vendor_dir = tmp_path / "nmr-vendor"
    vendor_dir.mkdir()
    (vendor_dir / "ser").write_bytes(b"opaque-ser")

    registry = default_converter_registry()
    fid_outcome = registry.convert_path(fid, technique="nmr", source_artifact_id="fid-source")
    dir_outcome = registry.convert_path(
        vendor_dir, technique="nmr", source_artifact_id="dir-source"
    )

    assert fid_outcome.status == "ready"
    assert fid_outcome.template is not None
    assert fid_outcome.template.template_id == "nmr.spectrum.v1"
    assert dir_outcome.status == "ready"
    assert dir_outcome.template is not None
    assert dir_outcome.template.template_id == "nmr.spectrum.v1"
    assert dir_outcome.template.measurements == ()


def test_compute_run_attaches_nmr_template_before_provider(tmp_path) -> None:
    source = tmp_path / "spectrum.csv"
    source.write_text("ppm,intensity\n10,0.2\n5,0.8\n", encoding="utf-8")
    engine = _FakeEngine()

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="nmr", path=source, output_dir=tmp_path / "out", engine=engine
    )

    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.template_id == "nmr.spectrum.v1"
    assert len(run.capability_items) == 2
    assert engine.calls == [(str(source.resolve()), str((tmp_path / "out").resolve()), {})]


def test_compute_run_passes_explicit_project_material_to_nmr_as_a_hint(tmp_path) -> None:
    from polynexus.core.nmr_engine.config import NMRConfig

    source = tmp_path / "spectrum.csv"
    source.write_text("ppm,intensity\n10,0.2\n5,0.8\n", encoding="utf-8")
    engine = _FakeEngine()
    engine._cfg = NMRConfig(polymer_name="")

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="nmr",
        path=source,
        output_dir=tmp_path / "out",
        engine=engine,
        project_context={"schema": "project-context.v1", "material": {"name": "custom-polymer"}},
    )

    assert run.status == "completed"
    assert engine._cfg.polymer_name == "custom-polymer"


def test_no_material_context_does_not_fabricate_nmr_polymer_assignment() -> None:
    from polynexus.core.nmr_engine.config import NMRConfig
    from polynexus.core.nmr_engine.core import analyze_spectrum
    from polynexus.core.nmr_engine.io import NMRSpectrum

    ppm = [float(value) for value in range(220, -21, -1)]
    intensity = [0.01] * len(ppm)
    for center, height in ((174, 1.0), (43, 0.8), (30, 0.5)):
        intensity[220 - center] = height
    spectrum = NMRSpectrum(
        ppm=ppm,
        intensity=intensity,
        nucleus="13C",
        metadata={"sample_state": "solid"},
    )
    result = analyze_spectrum(spectrum, NMRConfig(polymer_name=""))

    assert result.peaks
    assert all(not peak.get("polymer") for peak in result.peaks)
    assert result.Xc_method in {"", "requires_crystalline_amorphous_assignment"}
