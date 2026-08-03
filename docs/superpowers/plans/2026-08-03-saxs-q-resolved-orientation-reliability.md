# SAXS q-Resolved Orientation Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add append-only q-resolved orientation, neutral q-band, stability, correction-ledger, and sensitivity evidence to SAXS core.

**Architecture:** A new focused module consumes existing support-aware chi-by-q maps and emits immutable strict-JSON-safe evidence. Existing scalar anisotropy remains backward compatible; preprocess supplies bounded variant integrations, and strain transports detached records without new GUI behavior.

**Tech Stack:** Python 3.12+, NumPy, SciPy, dataclasses, pytest, existing SAXS quality contracts.

---

## File map

- Create `polynexus/core/saxs_engine/saxs_orientation_reliability.py`: DTOs, M2, q bands, bootstrap, ledger, sensitivity summaries.
- Modify `polynexus/core/saxs_engine/config.py`: bounded diagnostic settings only.
- Modify `polynexus/core/saxs_engine/preprocess.py`: immutable integration variant hook.
- Modify `polynexus/core/saxs_engine/saxs_anisotropy.py`: append q-resolved evidence.
- Modify `polynexus/core/saxs_engine/saxs_quality_contracts.py`: detached serialization only if required.
- Modify `polynexus/core/saxs_engine/saxs_strain.py`: frame transport.
- Modify `polynexus/core/saxs_engine/__init__.py`: public exports.
- Create `tests/test_saxs_q_resolved_orientation_reliability.py`: synthetic contracts.
- Create `tests/test_saxs_real_q_resolved_orientation.py`: read-only real replay.

### Task 1: Lock the q-bin contract with RED tests

- [ ] **Step 1: Write the isotropic and known-harmonic tests**

```python
def test_q_resolved_m2_preserves_detector_plane_baseline() -> None:
    chi = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    q = np.array([0.20, 0.30, 0.40])
    intensity = np.ones((chi.size, q.size))
    support = np.ones_like(intensity)

    evidence = build_q_resolved_orientation(intensity, q, chi, support_count=support)

    assert all(point.f_principal_raw == pytest.approx(0.25, abs=1e-12) for point in evidence.q_bins)
    assert evidence.convention == "detector_plane_2d_v1"
    assert evidence.isotropic_baseline == 0.25


def test_q_resolved_m2_recovers_known_axis_and_strength() -> None:
    chi = np.linspace(-np.pi, np.pi, 180, endpoint=False)
    q = np.array([0.25, 0.30, 0.35])
    axis = np.deg2rad(35.0)
    intensity = 10.0 * (1.0 + 0.4 * np.cos(2.0 * (chi[:, None] - axis)))
    intensity = np.repeat(intensity, q.size, axis=1)

    evidence = build_q_resolved_orientation(
        intensity, q, chi, support_count=np.ones_like(intensity)
    )

    point = evidence.q_bins[1]
    assert point.anisotropy_strength == pytest.approx(0.2, abs=0.01)
    assert axial_distance_deg(point.principal_axis_deg, 35.0) < 1.0
    assert point.f_principal_raw == pytest.approx(0.40, abs=0.01)
```

Also add `test_sector_map_backends_share_detector_image_clockwise_convention`
using synthetic intensity at +column, +row, -column, and -row. Assert NumPy and
pyFAI integrations map those directions to 0, 90, 0, and 90 degrees modulo
180. Normalize backend output once in preprocessing if required and record the
raw backend convention in provenance.

- [ ] **Step 2: Run RED**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_q_resolved_orientation_reliability.py -q`

Expected: collection failure because `saxs_orientation_reliability` does not exist.

- [ ] **Step 3: Add immutable DTO skeletons and strict serialization**

```python
@dataclass(frozen=True)
class QOrientationBin:
    q_bin_id: str
    q_nm1: float
    q_bin_width_nm1: float | None
    harmonic_numerator_real: float | None
    harmonic_numerator_imag: float | None
    intensity_denominator: float | None
    m2_real: float | None
    m2_imag: float | None
    anisotropy_strength: float | None
    principal_axis_deg: float | None
    f_principal_raw: float | None
    f_reference: float | None
    reference_axis_deg: float | None
    reference_axis_kind: str
    effective_angular_bins: float
    angular_coverage: float
    support_fraction: float | None
    harmonic_significance: float | None
    stability_interval: Mapping[str, Any]
    level: str
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return strict_json_dataclass(self)
```

Also define immutable `CorrectionLedgerEntry`, `OrientationQBandCandidate`,
`OrientationSensitivitySummary`, and `QResolvedOrientationEvidence` with the
field names in the spec. `OrientationQBandCandidate` must expose ordered
`supported_q_bin_ids`; each sensitivity observation must expose a stable
`variant_id`, candidate ID, ordered q-bin IDs, q range, orientation summaries,
eligibility, and reasons. `QResolvedOrientationEvidence` must expose a
`reliability_policy_digest` derived from normalized gate settings.

- [ ] **Step 4: Implement the minimal M2 calculation**

```python
def _second_harmonic(chi: np.ndarray, weights: np.ndarray) -> complex | None:
    valid = np.isfinite(chi) & np.isfinite(weights) & (weights > 0)
    denominator = float(np.sum(weights[valid]))
    if np.count_nonzero(valid) < 5 or denominator <= 0:
        return None
    return complex(np.sum(weights[valid] * np.exp(2j * chi[valid])) / denominator)


def _herman_from_m2(m2: complex, reference_axis_deg: float | None) -> tuple[float, float | None]:
    principal = float(0.25 + 0.75 * abs(m2))
    if reference_axis_deg is None:
        return principal, None
    phase = np.exp(-2j * np.deg2rad(reference_axis_deg))
    return principal, float(np.clip(0.25 + 0.75 * np.real(m2 * phase), -0.5, 1.0))
```

Store the finite numerator real/imaginary parts and positive denominator used
for each result before normalization. Derive `q_bin_id` from canonical lower
and upper q bounds, not list position or process hash.

- [ ] **Step 5: Run focused GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_q_resolved_orientation_reliability.py -q`

Expected: the initial isotropic and known-harmonic tests pass.

### Task 2: Add support gates and neutral q-band candidates

- [ ] **Step 1: Add RED tests for multiple bands and unsupported bins**

```python
def test_candidates_keep_multiple_separated_q_bands() -> None:
    evidence = build_q_resolved_orientation(*two_band_fixture())
    assert [(item.q_min_nm1, item.q_max_nm1) for item in evidence.q_band_candidates] == [
        pytest.approx((0.20, 0.30)),
        pytest.approx((0.60, 0.75)),
    ]
    assert {item.feature_kind for item in evidence.q_band_candidates} == {"q_band"}


def test_zero_support_is_unavailable_not_zero_intensity() -> None:
    intensity, q, chi, support = isotropic_fixture()
    support[:, 2] = 0
    evidence = build_q_resolved_orientation(intensity, q, chi, support_count=support)
    assert evidence.q_bins[2].level == "Unusable"
    assert "annulus_no_supported_angular_bins" in evidence.q_bins[2].reason_codes
```

- [ ] **Step 2: Run RED and confirm candidate assertions fail**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_q_resolved_orientation_reliability.py -q`

- [ ] **Step 3: Implement per-q support summaries using existing config gates**

Reuse `orientation_auto_min_strength`, `orientation_auto_min_significance`,
`orientation_min_coverage`, `orientation_min_effective_bins`, and
`orientation_max_axis_drift_deg`. Do not add a publication cutoff.

- [ ] **Step 4: Implement contiguous candidate extraction**

```python
def _candidate_runs(points: Sequence[QOrientationBin]) -> tuple[tuple[int, ...], ...]:
    eligible = [point.level == "Trend" for point in points]
    runs: list[list[int]] = []
    for index, ok in enumerate(eligible):
        if ok:
            if not runs or index != runs[-1][-1] + 1:
                runs.append([])
            runs[-1].append(index)
    return tuple(tuple(run) for run in runs if len(run) >= 3)
```

Bridge one supported one-bin gap only in a separate tested helper. Aggregate
M2 from unsmoothed source intensity and support, never candidate smoothing.

- [ ] **Step 5: Run focused GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_q_resolved_orientation_reliability.py -q`

### Task 3: Add deterministic resampling stability

- [ ] **Step 1: Add RED tests for repeatability and failure preservation**

```python
def test_bootstrap_is_deterministic_and_does_not_mutate_inputs() -> None:
    intensity, q, chi, support = anisotropic_fixture()
    before = intensity.copy()
    first = build_q_resolved_orientation(intensity, q, chi, support_count=support, source_id="frame-0")
    second = build_q_resolved_orientation(intensity, q, chi, support_count=support, source_id="frame-0")
    assert first.to_dict() == second.to_dict()
    np.testing.assert_array_equal(intensity, before)


def test_bootstrap_failure_keeps_raw_value_diagnostic() -> None:
    evidence = build_q_resolved_orientation(*sparse_angular_fixture())
    point = next(item for item in evidence.q_bins if item.f_principal_raw is not None)
    assert point.level == "Diagnostic"
    assert "orientation_resampling_unavailable" in point.reason_codes
```

- [ ] **Step 2: Implement circular moving-block bootstrap**

Use 256 replicates; block length is `max(3, ceil(5 degrees / chi_step))`.
Derive a stable seed from `source_id`, q bounds, and convention using SHA-256.
Store only percentile summaries, not replicate arrays.

- [ ] **Step 3: Label intervals as stability intervals**

The serialized key is `stability_interval`; never emit `confidence_interval`
or uncertainty units unsupported by the data.

- [ ] **Step 4: Run focused GREEN and strict JSON check**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_q_resolved_orientation_reliability.py -q`

### Task 4: Add correction ledger and bounded sensitivity variants

- [ ] **Step 1: Add RED tests for candidate-only behavior**

```python
def test_candidate_center_and_mask_variants_never_replace_baseline() -> None:
    image, cfg, mask = detector_fixture()
    baseline_cfg = copy.deepcopy(cfg)
    baseline_mask = mask.copy()

    result = evaluate_orientation_sensitivity(image, cfg, confirmed_mask=mask)

    assert result.baseline_variant_id == "baseline"
    assert all(item.status == "candidate_only" for item in result.correction_ledger if item.operation.endswith("variant"))
    assert cfg == baseline_cfg
    np.testing.assert_array_equal(mask, baseline_mask)


def test_variants_keep_identity_and_common_support_inputs() -> None:
    evidence = build_q_resolved_orientation(*anisotropic_fixture())
    assert evidence.reliability_policy_digest
    assert all(point.q_bin_id for point in evidence.q_bins)
    assert all(point.intensity_denominator is not None for point in evidence.q_bins)
    assert all(item.variant_id for item in evidence.sensitivity_summary.observations)
```

- [ ] **Step 2: Add bounded settings to `SAXSConfig`**

```python
orientation_reliability_enabled: bool = True
orientation_bootstrap_replicates: int = 256
orientation_center_offsets_px: tuple[float, ...] = (-1.0, 0.0, 1.0)
orientation_mask_dilation_px: tuple[int, ...] = (1, 2)
orientation_q_width_scales: tuple[float, ...] = (0.75, 1.0, 1.25)
orientation_chi_bin_scales: tuple[float, ...] = (0.5, 1.0, 2.0)
```

Validate and normalize these values in core; malformed settings fail closed to
diagnostic defaults and record reasons.

- [ ] **Step 3: Add a preprocess integration callback**

The sensitivity service receives an explicit callback that returns a detached
`SectorMapResult` for `(image, cfg_variant, mask_variant)`. Do not copy EDF I/O
into the reliability module.

- [ ] **Step 4: Implement artifact-sensitive semantics**

Set `artifact_sensitive` only when a bounded variant changes an existing
eligibility decision, removes the matched q band, changes frame-local q-band
identity, or violates the existing axis-drift gate. Always retain continuous
variant ranges and per-variant candidate observations.

- [ ] **Step 5: Run focused GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_q_resolved_orientation_reliability.py tests/test_saxs_preprocess.py -q`

### Task 5: Attach evidence and replay real EDFs

- [ ] **Step 1: Add RED propagation tests**

Assert `AnisotropyResult`, `StrainPoint`, and `StrainSeriesResult` expose a
detached `q_resolved_orientation_evidence` field without changing legacy
`f_herman` or `f_herman_raw`.

- [ ] **Step 2: Attach evidence in `analyze_anisotropy()`**

Build q-resolved evidence from the canonical sector map and support count.
Keep scalar q-star analysis unchanged. Never derive a final scalar from a
different q band in this task.

- [ ] **Step 3: Copy detached evidence through strain transport**

Use existing quality-copy patterns. Rebuild no report from processed intensity
and do not apply radial 1D blockers to unrelated q bands.

- [ ] **Step 4: Add read-only real-data test**

The test locates zero and five-percent EDFs, writes only to pytest `tmp_path`,
and records candidate q overlap plus sensitivity ranges. It must skip with an
explicit reason if fixtures are unavailable and must not assert monotonicity.

- [ ] **Step 5: Run required verification**

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_q_resolved_orientation_reliability.py tests/test_saxs_feature_orientation_foundation.py tests/test_saxs_2d_detector_orientation_evidence.py -q
python -m pytest -p no:cacheprovider tests/test_saxs_real_q_resolved_orientation.py -q
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-q-resolved-orientation-reliability.md --changed --types
git diff --check
```

- [ ] **Step 6: Review and checkpoint the exact allowlist**

Update this task card with exact results. Review the cumulative diff, then run:

```powershell
python scripts/auto_commit.py --message "feat(saxs): add q-resolved orientation reliability" --files polynexus/core/saxs_engine/saxs_orientation_reliability.py polynexus/core/saxs_engine/config.py polynexus/core/saxs_engine/preprocess.py polynexus/core/saxs_engine/saxs_anisotropy.py polynexus/core/saxs_engine/saxs_quality_contracts.py polynexus/core/saxs_engine/saxs_strain.py polynexus/core/saxs_engine/__init__.py tests/test_saxs_q_resolved_orientation_reliability.py tests/test_saxs_real_q_resolved_orientation.py docs/agent/tasks/2026-08-03-saxs-q-resolved-orientation-reliability.md
```

Do not push. Review the cumulative diff and real-data evidence, record the
contract check in the task card, and continue to Task 2 only when no documented
scientific stop gate is triggered. Human scientific review remains required
before merge.
