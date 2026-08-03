# SAXS Orientation Feature Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track mutually unique q-band features across strain and publish conservative same-feature delta evidence.

**Architecture:** A pure core tracker consumes detached Task 1 frame evidence plus existing condition/source-index facts. It creates immutable track and sequence DTOs, then strain/core transports the complete detached multi-track evidence without choosing a primary feature.

**Tech Stack:** Python 3.12+, dataclasses, NumPy, pytest, existing SAXS sequence quality contracts.

---

## File map

- Create `polynexus/core/saxs_engine/saxs_orientation_tracking.py`: compatibility, track construction, delta, sequence DTO.
- Modify `polynexus/core/saxs_engine/saxs_strain.py`: invoke tracker and attach evidence.
- Modify `polynexus/core/saxs_engine/saxs_quality_contracts.py`: detached series evidence if existing generic builder is insufficient.
- Modify `polynexus/core/saxs_engine/__init__.py`: exports.
- Modify `polynexus/core/saxs.py`: append-only parameter and frame transport.
- Modify `polynexus/core/saxs_batch_helpers.py`: deep-copy sequence and frame evidence.
- Create `tests/test_saxs_orientation_feature_tracking.py`: pure core TDD.
- Create `tests/test_saxs_orientation_tracking_transport.py`: engine transport.
- Create `tests/test_saxs_real_orientation_tracking.py`: read-only real series.

### Task 1: Define immutable tracking contracts

- [ ] **Step 1: Write RED DTO and JSON tests**

```python
def test_orientation_track_is_immutable_and_strict_json_safe() -> None:
    observation = OrientationFeatureObservation(
        frame_source_index=0,
        condition_value=0.0,
        candidate_id="frame-000-band-001",
        q_range_nm1=(0.20, 0.30),
        common_q_bin_ids=("q-0200-0233", "q-0233-0266", "q-0266-0300"),
        q_center_nm1=0.25,
        f_principal_raw=0.40,
        f_reference=None,
        delta_f_from_zero=None,
        delta_stability_interval={},
        reliability_status="diagnostic",
        reason_codes=("tensile_axis_unknown",),
    )
    track = OrientationFeatureTrack(
        track_id="orientation-track-001",
        feature_kind="q_band",
        convention="detector_plane_2d_v1",
        reference_axis_kind="unknown",
        reference_axis_deg=None,
        reliability_policy_digest="policy-sha256",
        observations=(observation,),
        reliability_status="diagnostic",
        reason_codes=("tensile_axis_unknown",),
    )
    json.dumps(track.to_dict(), allow_nan=False)
    with pytest.raises(FrozenInstanceError):
        track.track_id = "changed"  # type: ignore[misc]
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_orientation_feature_tracking.py -q`

- [ ] **Step 3: Implement DTOs and stable IDs**

Use frozen dataclasses. Track IDs derive from ordered source indices and
candidate IDs through a deterministic SHA-256 suffix; do not use process hash
or UUID randomness.

- [ ] **Step 4: Run focused GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_orientation_feature_tracking.py -q`

### Task 2: Implement mutual-unique compatibility

- [ ] **Step 1: Add unique, crossing, and ambiguous RED tests**

```python
def test_mutually_unique_overlapping_bands_keep_one_track() -> None:
    sequence = track_orientation_features(
        [frame(0, 0.0, band("a", 0.20, 0.30)), frame(1, 5.0, band("b", 0.22, 0.31))]
    )
    assert len(sequence.tracks) == 1
    assert tuple(item.candidate_id for item in sequence.tracks[0].observations) == ("a", "b")


def test_ambiguous_fork_splits_instead_of_selecting_lowest_cost() -> None:
    sequence = track_orientation_features(
        [
            frame(0, 0.0, band("a", 0.20, 0.35)),
            frame(1, 5.0, band("b", 0.20, 0.28), band("c", 0.29, 0.35)),
        ]
    )
    assert sequence.ambiguous_match_count == 1
    assert "feature_match_ambiguous" in sequence.reason_codes
    assert all(
        tuple(item.candidate_id for item in track.observations) != ("a", "b")
        for track in sequence.tracks
    )
```

- [ ] **Step 2: Implement compatibility predicates**

```python
def compatible(
    left_frame: QResolvedOrientationEvidence,
    left: OrientationQBandCandidate,
    right_frame: QResolvedOrientationEvidence,
    right: OrientationQBandCandidate,
    *,
    max_axis_drift_deg: float,
) -> bool:
    if left_frame.convention != right_frame.convention or left_frame.reference_axis_kind != right_frame.reference_axis_kind:
        return False
    if left_frame.reference_axis_deg != right_frame.reference_axis_deg:
        return False
    if left_frame.reliability_policy_digest != right_frame.reliability_policy_digest:
        return False
    if len(ordered_common_q_bins(left, right)) < 3:
        return False
    if not (right.q_min_nm1 <= left.q_center_nm1 <= right.q_max_nm1):
        return False
    if not (left.q_min_nm1 <= right.q_center_nm1 <= left.q_max_nm1):
        return False
    return axes_compatible(left.principal_axis_deg, right.principal_axis_deg, max_axis_drift_deg)
```

Build all adjacent-frame edges, retain only edges where each endpoint has
exactly one compatible neighbor, and split every other branch.

- [ ] **Step 3: Add one-gap tests and implementation**

Bridge exactly one missing frame only when candidates on both sides are mutual-
unique. Preserve missing source index in sequence evidence. Two or more missing
frames always split.

- [ ] **Step 4: Run focused GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_orientation_feature_tracking.py -q`

### Task 3: Add zero-reference and delta semantics

- [ ] **Step 1: Add RED tests for unique, missing, and duplicate zero**

```python
@pytest.mark.parametrize("conditions", [(5.0, 60.0), (0.0, 0.0, 5.0)])
def test_delta_is_unavailable_without_a_unique_zero_reference(conditions) -> None:
    sequence = track_orientation_features(sequence_for_conditions(conditions))
    assert sequence.zero_reference_source_index is None
    assert all(
        all(item.delta_f_from_zero is None for item in track.observations)
        for track in sequence.tracks
    )
    assert any(code in sequence.reason_codes for code in ("zero_reference_missing", "zero_reference_ambiguous"))
```

- [ ] **Step 2: Implement same-track delta only**

Require a unique condition value numerically equal to zero, identical
convention/reference kind and degree, identical policy digest, finite applicable
reference Herman for final delta, usable local evidence, and exact common q-bin
identity. Reaggregate each frame from Task 1 harmonic numerators and intensity
denominators over the ordered q-bin intersection before subtraction. If any
additive term is absent, emit `delta_common_support_unavailable`.

```python
def aggregate_common_m2(
    left: QResolvedOrientationEvidence,
    right: QResolvedOrientationEvidence,
    q_bin_ids: Sequence[str],
) -> tuple[complex, complex] | None:
    outputs: list[complex] = []
    for frame in (left, right):
        by_id = {item.q_bin_id: item for item in frame.q_bins}
        selected = [by_id.get(q_bin_id) for q_bin_id in q_bin_ids]
        if any(item is None or item.intensity_denominator is None for item in selected):
            return None
        denominator = sum(float(item.intensity_denominator) for item in selected)
        if denominator <= 0:
            return None
        numerator = sum(
            complex(float(item.harmonic_numerator_real), float(item.harmonic_numerator_imag))
            for item in selected
        )
        outputs.append(numerator / denominator)
    return outputs[0], outputs[1]
```

- [ ] **Step 3: Implement conservative interval arithmetic**

```python
def delta_interval(frame_interval: Mapping[str, float], zero_interval: Mapping[str, float]) -> dict[str, float] | None:
    required = ("lower", "upper")
    if not all(key in frame_interval and key in zero_interval for key in required):
        return None
    return {
        "lower": float(frame_interval["lower"] - zero_interval["upper"]),
        "upper": float(frame_interval["upper"] - zero_interval["lower"]),
        "kind": "conservative_stability_bound",
    }
```

Use candidate stability bounds only when both candidates' ordered
`supported_q_bin_ids` exactly equal the common q-bin set. Otherwise leave the
bound unavailable with `delta_stability_common_support_unavailable`; do not
describe subtraction of marginal intervals as a paired bootstrap.

- [ ] **Step 4: Prove no monotonicity rule exists**

Add a test where five-percent delta is negative and all reliability states are
preserved without warning or coercion solely because of the sign.

- [ ] **Step 5: Run focused GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_orientation_feature_tracking.py -q`

### Task 4: Add suspected-systematic diagnostics

- [ ] **Step 1: Add RED persistence tests**

Create one sequence with a broad, detector-axis-stable component in every
valid frame and one with a q-local evolving component. Assert only the first
gets `systematic_harmonic_suspected` and neither is subtracted.

- [ ] **Step 2: Implement metrics before classification**

Emit valid-frame persistence, common-q coverage, axial spread, and strength
coefficient of variation. Mark suspected only when persistence is 1.0, common-q
coverage is at least 0.5, and axial spread stays within the existing axis-drift
gate. This is a diagnostic label, never a correction or promotion.

- [ ] **Step 3: Run focused GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_orientation_feature_tracking.py -q`

### Task 5: Attach and transport sequence evidence

- [ ] **Step 1: Add RED strain transport tests**

Assert `StrainSeriesResult.orientation_tracking_evidence` and emitted SAXS
parameters contain the complete detached multi-track DTO, while each original
frame's Task 1 DTO is unchanged. Also assert invalid, duplicate, or missing
source-index mappings fail tracking closed instead of substituting list order.

- [ ] **Step 2: Invoke tracker after frame evidence is complete**

Call tracking at the end of `analyze_strain_series()` after condition/source
alignment and frame orientation evidence. Catch structural failures into an
explicit unavailable sequence DTO; do not swallow individual matching reasons.
Extend the function with an explicit `frame_source_indices` argument supplied
by the existing caller's source-index mapping; never synthesize it from list
position.

- [ ] **Step 3: Flatten approved summaries in `polynexus/core/saxs.py`**

Transport `orientation_tracking_evidence` as one detached strict-JSON-safe DTO
plus per-frame observation lists. Do not flatten a singular track ID or q range,
because no primary feature is scientifically authorized. Do not expose raw
arrays or replace `f_Herman`/`f_Herman_raw`.

- [ ] **Step 4: Add read-only real-series acceptance**

Assert the test reports whether zero/five-percent share a track, all ambiguous
or split reasons, and any delta interval. Do not assert the expected sign or
monotonicity.

- [ ] **Step 5: Run required verification**

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_orientation_feature_tracking.py tests/test_saxs_orientation_tracking_transport.py -q
python -m pytest -p no:cacheprovider tests/test_saxs_real_orientation_tracking.py -q
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-orientation-feature-tracking.md --changed --types
git diff --check
```

- [ ] **Step 6: Review and checkpoint the exact allowlist**

```powershell
python scripts/auto_commit.py --message "feat(saxs): track orientation features across strain" --files polynexus/core/saxs_engine/saxs_orientation_tracking.py polynexus/core/saxs_engine/saxs_strain.py polynexus/core/saxs_engine/saxs_quality_contracts.py polynexus/core/saxs_engine/__init__.py polynexus/core/saxs.py polynexus/core/saxs_batch_helpers.py tests/test_saxs_orientation_feature_tracking.py tests/test_saxs_orientation_tracking_transport.py tests/test_saxs_real_orientation_tracking.py docs/agent/tasks/2026-08-03-saxs-orientation-feature-tracking.md
```

Do not push. Review the tracking DTO and real-series evidence, record the
contract check in the task card, and continue to Task 3 only when no documented
scientific stop gate is triggered. Human scientific review remains required
before merge.
