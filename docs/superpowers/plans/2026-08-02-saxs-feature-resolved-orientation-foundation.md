# SAXS Feature-Resolved Orientation Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish support-aware, tensile-axis-referenced orientation evidence for the existing SAXS strain path without claiming that one q* represents all detector features.

**Architecture:** Preserve the current `I_2d`/q/chi sector payload as a compatibility surface, but attach explicit per-bin support, raw-detector provenance, and annulus-local quality. `saxs_anisotropy` continues to calculate the legacy auto-axis raw diagnostic; only a finite explicit tensile axis can produce the effective table Herman value. Core contracts own physical semantics and gates; `saxs_strain` transports them without adding GUI behavior.

**Tech Stack:** Python 3.14, NumPy, pyFAI `Integrate2dResult.count`, dataclasses, pytest, existing strict JSON contracts.

---

## File Structure

- Create: `tests/test_saxs_feature_orientation_foundation.py` - regression tests for axis semantics, sector occupancy, annulus support, and strain transport.
- Create: `docs/acceptance/2026-08-02-saxs-feature-resolved-orientation-foundation.md` - measured verification record and read-only 610 EDF evidence.
- Create: `docs/agent/memory/decisions/0006-saxs-tensile-axis-orientation-contract.md` - durable physical semantic decision after the implementation is verified.
- Modify: `polynexus/core/saxs_engine/config.py` - explicit tensile-axis configuration, distinct from the existing legacy detector-plane axis.
- Modify: `polynexus/core/saxs_engine/preprocess.py` - support-aware `SectorMapResult` and transport of raw detector provenance into `sector_data`.
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py` - serializable sector-map and annulus quality reports plus orientation evidence fields.
- Modify: `polynexus/core/saxs_engine/saxs_anisotropy.py` - support-aware annulus extraction, principal-scattering-axis evidence, and tensile-axis Herman gate.
- Modify: `polynexus/core/saxs_engine/saxs_strain.py` - transport raw detector/annulus evidence and stop applying unrelated diagnostic 1D reasons as 2D hard blockers.
- Modify: `tests/test_saxs_2d_detector_orientation_evidence.py` - migrate legacy auto-axis expectations into explicit tensile-axis and support-aware assertions.
- Modify: `tests/test_saxs_batch_parameters.py` - update canonical sector fixtures to include support and test table availability semantics.
- Modify: `docs/agent/tasks/2026-08-02-saxs-feature-resolved-orientation-foundation.md` - mark completed acceptance criteria and record exact verification/checkpoint evidence.

### Task 1: Define Serializable Physical and Quality Contracts

**Files:**
- Modify: `polynexus/core/saxs_engine/config.py:190-204`
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py:100-200,1719-1809`
- Create: `tests/test_saxs_feature_orientation_foundation.py`

- [ ] **Step 1: Write failing contract tests**

```python
import json
import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_quality_contracts import (
    QualityLevel,
    build_annulus_quality_report,
    build_sector_map_quality_report,
)


def test_support_reports_distinguish_empty_bins_from_intensity_values() -> None:
    intensity = np.array([[0.0, 3.0], [0.0, -2.0]])
    support = np.array([[0.0, 4.0], [0.0, 2.0]])
    sector = build_sector_map_quality_report(intensity, support)
    annulus = build_annulus_quality_report(
        support, np.array([0.40, 0.50]), q_target=0.50, q_width=0.01,
    )

    assert sector.empty_bin_count == 2
    assert sector.measured_nonpositive_bin_count == 1
    assert "sector_empty_bins_present" in sector.reason_codes
    assert "nonpositive_pixels" not in sector.reason_codes
    assert annulus.supported_angular_bin_count == 2
    json.dumps(sector.to_dict(), allow_nan=False)
    json.dumps(annulus.to_dict(), allow_nan=False)


def test_config_keeps_tensile_axis_separate_from_legacy_axis() -> None:
    cfg = SAXSConfig(orientation_axis_deg=37.0, tensile_axis_deg=90.0)

    assert cfg.orientation_axis_deg == 37.0
    assert cfg.tensile_axis_deg == 90.0
```

- [ ] **Step 2: Run the contract tests and confirm they fail because the support builders and `tensile_axis_deg` do not exist**

Run:

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_feature_orientation_foundation.py -q
```

Expected: import or attribute failures for `build_sector_map_quality_report`, `build_annulus_quality_report`, and `tensile_axis_deg`.

- [ ] **Step 3: Add the minimal immutable contracts and explicit configuration field**

Add a documented configuration field without changing `orientation_axis_deg` behavior in this task:

```python
# config.py
# Explicit detector-plane projection of the tensile axis.  None means this
# experiment has no verified tensile reference for a table-level Herman value.
tensile_axis_deg: Optional[float] = None
```

Add strict JSON-safe dataclasses and builders in `saxs_quality_contracts.py`:

```python
@dataclass(frozen=True)
class SectorMapQualityReport:
    shape: tuple[int, ...] = ()
    support_available: bool = False
    supported_bin_count: int = 0
    empty_bin_count: int = 0
    measured_nonpositive_bin_count: int = 0
    support_fraction: float | None = None
    reason_codes: tuple[str, ...] = ()
    level: QualityLevel = QualityLevel.UNUSABLE

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self)


@dataclass(frozen=True)
class AnnulusQualityReport:
    q_target_nm1: float | None = None
    q_width_nm1: float | None = None
    selected_q_bin_count: int = 0
    angular_bin_count: int = 0
    supported_angular_bin_count: int = 0
    support_fraction: float | None = None
    support_available: bool = False
    reason_codes: tuple[str, ...] = ()
    level: QualityLevel = QualityLevel.UNUSABLE

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self)
```

`build_sector_map_quality_report()` must count `support_count == 0` as empty
integration bins, and count nonpositive intensity only where support is
positive. `build_annulus_quality_report()` must use the same q-width expansion
as `extract_azimuthal_profile()` and compute angular support from
`np.any(support_count[:, q_mask] > 0, axis=1)`. Missing or shape-mismatched
support returns `support_available=False`, level `Diagnostic`, and
`sector_support_unavailable`; it must not manufacture a pixel count from
intensity.

Extend `build_orientation_evidence()` with optional
`sector_map_quality` and `annulus_quality` mappings. Add their detached
payloads under `physical_checks`; preserve its existing positional
`detector_quality` argument for all current callers.

- [ ] **Step 4: Run the contract tests and JSON-safety coverage**

Run:

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_feature_orientation_foundation.py tests/test_saxs_quality_contracts.py -q
```

Expected: PASS, including strict `json.dumps(..., allow_nan=False)`.

- [ ] **Step 5: Checkpoint the contract-only change when the index is clean**

Run:

```powershell
git diff --cached --name-only
python scripts/auto_commit.py --message "feat(saxs): define orientation support contracts" --files polynexus/core/saxs_engine/config.py polynexus/core/saxs_engine/saxs_quality_contracts.py tests/test_saxs_feature_orientation_foundation.py
```

Expected: the first command prints no unrelated staged file; the second creates
one commit containing only the explicit allowlist. If the index already has
another task, leave it unchanged and defer the checkpoint rather than mixing
work.

### Task 2: Preserve Pixel Support Through Both Sector Integration Backends

**Files:**
- Modify: `polynexus/core/saxs_engine/preprocess.py:339-393,706-729`
- Modify: `tests/test_saxs_preprocess.py:18-31`
- Modify: `tests/test_saxs_feature_orientation_foundation.py`

- [ ] **Step 1: Write failing NumPy and pyFAI support tests**

```python
from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.preprocess import integrate_chi_sectors


def test_numpy_sector_map_preserves_zero_support_separately_from_intensity() -> None:
    cfg = SAXSConfig(q_min=0.01, q_max=5.0, n_pt=8, n_chi_sectors=12)
    image = np.ones((32, 32), dtype=float)
    image[0, 0] = -1.5

    sector_map = integrate_chi_sectors(None, image, cfg)

    assert sector_map.intensity.shape == (12, 8)
    assert sector_map.support_count.shape == sector_map.intensity.shape
    assert np.array_equal(sector_map.empty_bin_mask, sector_map.support_count == 0)
    assert np.any(sector_map.empty_bin_mask)


def test_pyfai_sector_map_uses_result_count_and_fails_closed_without_it() -> None:
    class FakeAI:
        def integrate2d(self, *_args, **_kwargs):
            return SimpleNamespace(
                intensity=np.ones((4, 3)),
                radial=np.array([0.2, 0.3, 0.4]),
                azimuthal=np.array([-90.0, -30.0, 30.0, 90.0]),
                count=np.full((4, 3), 7.0),
            )

    result = integrate_chi_sectors(FakeAI(), np.ones((8, 8)), SAXSConfig(n_pt=3, n_chi_sectors=4))

    assert np.all(result.support_count == 7.0)
    assert result.integration_backend == "pyfai"
```

- [ ] **Step 2: Run the support tests and confirm tuple-only integration fails the new assertions**

Run:

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_feature_orientation_foundation.py::test_numpy_sector_map_preserves_zero_support_separately_from_intensity tests/test_saxs_feature_orientation_foundation.py::test_pyfai_sector_map_uses_result_count_and_fails_closed_without_it -q
```

Expected: attribute failures because `integrate_chi_sectors()` currently returns a three-item tuple.

- [ ] **Step 3: Introduce a compatibility-preserving sector result and populate it**

Define this dataclass near `integrate_chi_sectors()`:

```python
@dataclass(frozen=True)
class SectorMapResult:
    q: np.ndarray
    intensity: np.ndarray
    chi: np.ndarray
    support_count: np.ndarray | None
    integration_backend: str

    @property
    def empty_bin_mask(self) -> np.ndarray | None:
        return None if self.support_count is None else self.support_count <= 0

    def __iter__(self):
        yield self.q
        yield self.intensity
        yield self.chi
```

In the NumPy branch, return the calculated `pixel_count` as `support_count`.
In the pyFAI branch, read `res.count`, reorder it with the same chi ordering as
`I_2d`, and accept it only when it is finite, two-dimensional, and shape-equal
to intensity. Set `support_count=None` when pyFAI omits or malformedly shapes
the count array. Do not derive support from intensity values.

Keep existing unpacking source-compatible:

```python
sector_map = integrate_chi_sectors(ai, img, cfg, mask=detector_mask)
q_2d, I_2d, chi_rad = sector_map
sector_data.update({
    "I_2d": I_2d,
    "q_2d": q_2d,
    "chi_rad": chi_rad,
    "support_count": sector_map.support_count,
    "sector_empty_bin_mask": sector_map.empty_bin_mask,
    "sector_integration_backend": sector_map.integration_backend,
})
```

After `build_detector_quality_report(img, ...)` completes, add the raw report
to the same detached payload:

```python
sector_data["raw_detector_quality_report"] = detector_report.to_dict()
```

- [ ] **Step 4: Run integration and preprocessing regressions**

Run:

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_feature_orientation_foundation.py tests/test_saxs_preprocess.py tests/test_saxs_manual_mask_confirmed_rerun.py -q
```

Expected: PASS; the existing `I_2d`, `q_2d`, and `chi_rad` payload keys remain
present and new support keys are shape-aligned.

- [ ] **Step 5: Checkpoint the integration change when the index is clean**

Run:

```powershell
git diff --cached --name-only
python scripts/auto_commit.py --message "feat(saxs): retain sector integration support" --files polynexus/core/saxs_engine/preprocess.py tests/test_saxs_preprocess.py tests/test_saxs_feature_orientation_foundation.py
```

Expected: only the listed paths are committed. Preserve unrelated staged work
if the preflight shows any other path.

### Task 3: Make Anisotropy Evidence Annulus-Local and Tensile-Axis Referenced

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_anisotropy.py:24-160,709-897`
- Modify: `tests/test_saxs_2d_detector_orientation_evidence.py`
- Modify: `tests/test_saxs_feature_orientation_foundation.py`

- [ ] **Step 1: Write failing orientation semantic tests**

```python
import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_anisotropy import analyze_anisotropy
from polynexus.core.saxs_engine.saxs_quality_contracts import build_detector_quality_report


def test_effective_herman_requires_explicit_tensile_axis() -> None:
    I_2d, q, chi, q_1d, I_1d = _synthetic_azimuthal_input(37.0)
    support = np.ones_like(I_2d)
    raw = build_detector_quality_report(
        np.ones((16, 16)), source_kind="raw_detector", beam_center=(8.0, 8.0),
    )

    result = analyze_anisotropy(
        I_2d, q, chi, q_1d, I_1d,
        cfg=SAXSConfig(tensile_axis_deg=None),
        support_count=support,
        raw_detector_quality=raw,
    )

    assert np.isfinite(result.f_herman_raw)
    assert not np.isfinite(result.f_herman)
    assert result.orientation_evidence["fit_evidence"]["reference_axis_kind"] == "unknown"
    assert "tensile_axis_unknown" in result.orientation_evidence["reason_codes"]


def test_supported_annulus_uses_tensile_axis_and_does_not_inherit_empty_bins() -> None:
    I_2d, q, chi, q_1d, I_1d = _synthetic_azimuthal_input(37.0)
    support = np.ones_like(I_2d)
    support[:, :5] = 0.0
    raw = build_detector_quality_report(
        np.ones((16, 16)), source_kind="raw_detector", beam_center=(8.0, 8.0),
    )

    result = analyze_anisotropy(
        I_2d, q, chi, q_1d, I_1d,
        cfg=SAXSConfig(tensile_axis_deg=37.0),
        support_count=support,
        raw_detector_quality=raw,
    )

    assert result.f_herman > 0.3
    checks = result.orientation_evidence["physical_checks"]
    assert checks["annulus_quality_report"]["support_available"] is True
    assert "nonpositive_pixels" not in result.orientation_evidence["reason_codes"]
```

- [ ] **Step 2: Run the semantic tests and confirm the current auto-axis output violates the requested contract**

Run:

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_feature_orientation_foundation.py::test_effective_herman_requires_explicit_tensile_axis tests/test_saxs_feature_orientation_foundation.py::test_supported_annulus_uses_tensile_axis_and_does_not_inherit_empty_bins -q
```

Expected: the absent-axis case currently produces an effective value or lacks
the new evidence fields; the supported-annulus case lacks annulus evidence.

- [ ] **Step 3: Add optional support/raw inputs and explicit evidence fields**

Extend only the keyword side of the analyzer signature:

```python
def analyze_anisotropy(
    I_2d: np.ndarray,
    q: np.ndarray,
    chi: np.ndarray,
    q_1d: np.ndarray,
    I_1d: np.ndarray,
    cfg: Optional[SAXSConfig] = None,
    *,
    support_count: np.ndarray | None = None,
    raw_detector_quality: DetectorQualityReport | Mapping[str, Any] | None = None,
) -> AnisotropyResult:
```

Normalize the optional raw report through `DetectorQualityReport.from_dict()`.
Build sector-map and q*-annulus quality with the new builders. Do not call
`build_detector_quality_report(I_2d, source_kind="sector_map")` as a proxy for
raw detector quality.

Add result/evidence fields with the following stable meanings:

```python
principal_scattering_axis_deg: float = np.nan
tensile_axis_deg: float = np.nan
reference_axis_deg: float = np.nan
reference_axis_kind: str = "unknown"
orientation_vector_kind: str = "unknown"
herman_convention: str = "detector_plane_2d_v1"
isotropic_baseline: float = 0.25
```

Continue to calculate `f_herman_raw` against the legacy configured or automatic
principal axis and label it in evidence as `legacy_principal_axis`. When
`cfg.tensile_axis_deg` is finite, calculate the final Herman and P2/P4 against
that axis. When it is absent or nonfinite, leave `f_herman`, P2, and P4 as NaN,
record `tensile_axis_unknown`, and retain principal-axis diagnostics. Gate the
final value on usable annulus support and existing harmonic/coverage/axis-drift
checks. A raw detector report blocks all orientation only at `Unusable`; a
diagnostic raw report remains visible evidence rather than an automatic annulus
veto.

Update `_attach_orientation_evidence()` to include feature kind `q_star_candidate`,
selected q range, axis semantics, convention, baseline, sector-map report, and
annulus report. Keep legacy keys and strict JSON serialization.

- [ ] **Step 4: Run anisotropy tests and migrate old configured-axis assertions**

Run:

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_feature_orientation_foundation.py tests/test_saxs_2d_detector_orientation_evidence.py -q
```

Expected: PASS. Update existing tests that require an effective Herman value to
provide both a support matrix and `SAXSConfig(tensile_axis_deg=...)`; leave
auto-axis tests asserting only principal-scattering diagnostics and raw values.

- [ ] **Step 5: Checkpoint the anisotropy change when the index is clean**

Run:

```powershell
git diff --cached --name-only
python scripts/auto_commit.py --message "feat(saxs): require tensile axis for Herman output" --files polynexus/core/saxs_engine/saxs_anisotropy.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_feature_orientation_foundation.py
```

Expected: exactly the stated paths are committed, without staged parallel work.

### Task 4: Transport the New Evidence Through In-Situ Strain Results

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_strain.py:364-523,771-805`
- Modify: `tests/test_saxs_batch_parameters.py:780-870`
- Modify: `tests/test_saxs_2d_evidence_propagation.py:161-200`
- Modify: `tests/test_saxs_feature_orientation_foundation.py`

- [ ] **Step 1: Write failing strain transport tests**

```python
def test_strain_table_needs_tensile_axis_but_preserves_principal_axis_evidence() -> None:
    q = np.linspace(0.10, 1.00, 120)
    intensity = 0.1 + np.exp(-((q - 0.45) / 0.025) ** 2)
    chi = np.linspace(-np.pi, np.pi, 36, endpoint=False)
    sector_data = {
        "I_2d": np.outer(1.0 + 3.0 * np.cos(chi) ** 2, intensity),
        "q_2d": q,
        "chi_rad": chi,
        "I_full": intensity,
        "support_count": np.ones((chi.size, q.size)),
        "raw_detector_quality_report": {
            "source_kind": "raw_detector", "shape": [8, 8], "pixel_count": 64,
            "finite_pixel_count": 64, "valid_pixel_count": 64,
            "coverage_fraction": 1.0, "beam_center_available": True,
            "beam_center": [4.0, 4.0], "level": "Trend",
        },
    }

    result = analyze_strain_series(
        [0.0], [q], [intensity], sector_data_list=[sector_data],
        cfg=SAXSConfig(smooth_method="none", tensile_axis_deg=None),
    )

    point = result.strain_points[0]
    assert not np.isfinite(point.f_herman)
    assert np.isfinite(point.f_herman_raw)
    assert "tensile_axis_unknown" in point.orientation_evidence["reason_codes"]


def test_low_q_diagnostic_does_not_block_supported_tensile_annulus(monkeypatch) -> None:
    from polynexus.core.saxs_engine import saxs_strain
    from polynexus.core.saxs_engine.core import LongPeriodResult, SAXSResult, StructureParams

    q = np.linspace(0.10, 1.00, 120)
    intensity = 0.1 + np.exp(-((q - 0.45) / 0.025) ** 2)
    chi = np.linspace(-np.pi, np.pi, 36, endpoint=False)
    sector_data = {
        "I_2d": np.outer(1.0 + 3.0 * np.cos(chi) ** 2, intensity),
        "q_2d": q,
        "chi_rad": chi,
        "I_full": intensity,
        "support_count": np.ones((chi.size, q.size)),
    }

    def fake_analyze_single(*_args, **_kwargs):
        return SAXSResult(
            long_period=LongPeriodResult(L_best=14.0, L_confidence=0.8),
            structure=StructureParams(L=14.0, lc=3.0, la=11.0, phi_c=0.25),
            data_quality_report={
                "level": "Diagnostic",
                "low_q_truncated": True,
                "reason_codes": ["intensity_nonpositive"],
            },
        )

    monkeypatch.setattr(saxs_strain, "analyze_single", fake_analyze_single)
    result = analyze_strain_series(
        [0.0], [q], [intensity], sector_data_list=[sector_data],
        cfg=SAXSConfig(smooth_method="none", tensile_axis_deg=0.0),
    )

    point = result.strain_points[0]
    assert np.isfinite(point.f_herman)
    assert "orientation_low_q_truncated" not in point.orientation_evidence["reason_codes"]
```

- [ ] **Step 2: Run the transport tests and confirm existing global 1D blockers fail the supported-annulus case**

Run:

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_feature_orientation_foundation.py tests/test_saxs_batch_parameters.py tests/test_saxs_2d_evidence_propagation.py -q
```

Expected: the new missing-axis assertion fails until transport is added; the
current low-q test demonstrates the old global-blocker behavior.

- [ ] **Step 3: Pass support and raw detector evidence unchanged through the strain adapter**

In `herman_from_sector_data()`, extract the new fields and pass them to the
keyword-only analyzer parameters:

```python
support_count = sector_data.get("support_count")
raw_detector_quality = sector_data.get("raw_detector_quality_report")
orientation = analyze_anisotropy(
    I_2d, q_2d, chi_rad, q_1d, I_1d, cfg=cfg,
    support_count=support_count,
    raw_detector_quality=raw_detector_quality,
)
```

Replace `_orientation_quality_blockers()` with an annulus-safe rule: only a
1D report at level `Unusable` returns `orientation_input_quality_unusable`.
Do not include `low_q_truncated`, `invalid_pairs_dropped`,
`intensity_nonpositive`, or q defects as global 2D blockers. Their 1D evidence
remains attached to the frame as a distinct quality domain.

Return principal-axis, tensile-axis, reference-axis, sector-map, and annulus
evidence in the existing result mapping. Existing dataframe/table projection
continues to render nonfinite `f_herman` as unavailable and does not display
`f_herman_raw` as the final value.

- [ ] **Step 4: Run strain, table, and evidence-propagation tests**

Run:

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_feature_orientation_foundation.py tests/test_saxs_batch_parameters.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_strain_sector_fail_closed.py -q
```

Expected: PASS. Update the former test that asserted
`orientation_low_q_truncated` so it instead verifies that the 1D reason stays
in frame quality evidence while a supported tensile annulus is not blocked.

- [ ] **Step 5: Checkpoint the strain transport change when the index is clean**

Run:

```powershell
git diff --cached --name-only
python scripts/auto_commit.py --message "fix(saxs): separate annulus and 1d orientation quality" --files polynexus/core/saxs_engine/saxs_strain.py tests/test_saxs_batch_parameters.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_feature_orientation_foundation.py
```

Expected: the commit includes only the stated core and test files.

### Task 5: Run Read-Only Real-EDF Acceptance and Record the Physical Boundary

**Files:**
- Create: `docs/acceptance/2026-08-02-saxs-feature-resolved-orientation-foundation.md`
- Create: `docs/agent/memory/decisions/0006-saxs-tensile-axis-orientation-contract.md`
- Modify: `docs/agent/tasks/2026-08-02-saxs-feature-resolved-orientation-foundation.md`
- Modify: `docs/superpowers/specs/2026-08-02-saxs-feature-resolved-orientation-foundation-design.md`

- [ ] **Step 1: Add a read-only 610 EDF acceptance test before recording results**

```python
from pathlib import Path

import numpy as np
import pytest

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.io import read_image
from polynexus.core.saxs_engine.preprocess import preprocess_pipeline


@pytest.mark.real_data
def test_610_edf_sector_support_is_not_raw_detector_nonpositive_defect() -> None:
    root = Path(r"C:\Users\Fan Xuyi\Desktop\edf\610")
    files = sorted(root.glob("610-*-S_0_00000.edf"))
    if len(files) != 4:
        pytest.skip("610 EDF acceptance dataset is unavailable")

    cfg = SAXSConfig(experiment_type="strain", smooth_method="none")
    for path in files:
        image, header = read_image(str(path))
        result = preprocess_pipeline(image, cfg, detector_header=header)
        sector = result["sector_data"]
        raw = result["detector_quality_report"]

        assert sector["support_count"].shape == sector["I_2d"].shape
        assert np.array_equal(
            sector["sector_empty_bin_mask"], sector["support_count"] <= 0,
        )
        assert raw["source_kind"] == "raw_detector"
        assert np.count_nonzero(sector["sector_empty_bin_mask"]) > raw[
            "nonpositive_pixel_count"
        ]
```

The test reads source data without writing beside it. It proves only: four files
load, raw detector reports are separate, support arrays are shape-aligned, and
sector-map empty bins are not counted as raw detector nonpositive pixels. It
must not assert a desired Herman magnitude for 5%, 60%, or 200%.

- [ ] **Step 2: Run the real acceptance test and focused regression matrix**

Run:

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_feature_orientation_foundation.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_batch_parameters.py tests/test_saxs_preprocess.py -q
```

Expected: PASS or explicit skip only when the external `610` directory is
absent. Record the observed frame count, support result, raw-detector result,
and skip status in the acceptance note.

- [ ] **Step 3: Update durable scientific records with verified facts only**

Write the acceptance note with the exact commands and outcomes. Write Decision
0006 with these stable statements:

```markdown
## Decision

Table-level SAXS Herman values are referenced to an explicit tensile axis.
Image-derived principal scattering axes are diagnostic evidence and cannot
substitute for tensile-axis metadata.

## Consequences

Missing tensile-axis metadata yields an unavailable table value, not zero.
Sector-map empty bins are integration-support facts, not raw detector defects.
```

Update the task card checkboxes and append observed verification results. Update
the design status from `Awaiting written-spec review` to `Implemented and
verified` only after all commands below pass.

- [ ] **Step 4: Run the complete SAXS matrix and structured verifier**

Run:

```powershell
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-08-02-saxs-feature-resolved-orientation-foundation.md --changed --types
git diff --check
```

Expected: all selected tests pass, the verifier exits `0`, and whitespace check
reports no error. Preserve existing unrelated worktree changes when a verifier
selects them; record any resulting limitation rather than changing their files.

- [ ] **Step 5: Review the cumulative allowlist and create the final task checkpoint**

Run:

```powershell
git diff --name-only
git diff --cached --name-only
python scripts/auto_commit.py --message "feat(saxs): establish support-aware tensile orientation" --files polynexus/core/saxs_engine/config.py polynexus/core/saxs_engine/preprocess.py polynexus/core/saxs_engine/saxs_quality_contracts.py polynexus/core/saxs_engine/saxs_anisotropy.py polynexus/core/saxs_engine/saxs_strain.py tests/test_saxs_feature_orientation_foundation.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_batch_parameters.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_preprocess.py docs/superpowers/specs/2026-08-02-saxs-feature-resolved-orientation-foundation-design.md docs/superpowers/plans/2026-08-02-saxs-feature-resolved-orientation-foundation.md docs/agent/tasks/2026-08-02-saxs-feature-resolved-orientation-foundation.md docs/acceptance/2026-08-02-saxs-feature-resolved-orientation-foundation.md docs/agent/memory/decisions/0006-saxs-tensile-axis-orientation-contract.md
```

Expected: the diff contains only the listed first-milestone files and the
staging preflight is empty. If a parallel task is staged, do not unstage or
commit around it; preserve it and report the checkpoint blocker.

## Plan Self-Review

- Spec coverage: Task 1 defines axis, convention, and quality domains; Task 2
  retains occupancy; Task 3 applies annulus-local analysis and tensile-axis
  output; Task 4 transports the result through strain; Task 5 proves and records
  the real-data boundary.
- Completion scan: no unresolved marker is present in executable code steps.
- Type consistency: `support_count` is a shape-aligned `np.ndarray | None` from
  `SectorMapResult`, sector payload, analyzer input, annulus builder, and strain
  transport. `tensile_axis_deg` is the only configuration source for final
  `f_herman`; `orientation_axis_deg` remains legacy principal-axis input.
- Scope: continuous q-band discovery, feature classification, structural-vector
  conversion, GUI layout, export projection, and AI advice remain separate
  future tasks.
