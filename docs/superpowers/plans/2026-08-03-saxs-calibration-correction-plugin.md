# SAXS Detector Calibration Plugin Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fail-closed detector-correction plugin protocol, immutable provenance, and transactional integration while keeping production numerical correction disabled until equations and real calibration evidence are reviewed.

**Architecture:** The active EDF reader preloads explicit calibration frames, a pure core service validates the entire request, and an owner-controlled registry decides whether any backend may produce an effective image. The production registry is empty in this task; a test-only backend proves ordering and ownership without claiming physical validity.

**Tech Stack:** Python 3.12+, NumPy, dataclasses, Protocol, SHA-256, pytest, existing SAXS preprocess and quality contracts.

---

## Scientific stop gate

Do not implement production dark/flat/background/transmission/thickness,
polarization, solid-angle, or isotropic-harmonic equations in this task. The
repository has no reviewed calibration EDFs, and the approved formula details
are incomplete. A later scientific task must decide dark treatment of flat and
standard frames, flat normalization, background scaling, and pyFAI correction
ownership before registering a production backend.

## File map

- Create `polynexus/core/saxs_engine/saxs_detector_correction.py`: immutable in-memory request/result DTOs, compatibility validation, registry, transaction service.
- Modify `polynexus/core/saxs_engine/config.py`: disabled mode and reviewed policy ID only.
- Modify `polynexus/core/saxs_engine/io.py`: normalize explicit correction-ownership metadata without claiming validity.
- Modify `polynexus/core/saxs_engine/preprocess.py`: invoke the empty-by-default registry and use one effective image/mask for every integration path.
- Modify `polynexus/core/saxs_engine/saxs_quality_contracts.py`: detached corrected-detector evidence and ledger transport.
- Modify `polynexus/core/saxs_engine/__init__.py`: public contract exports.
- Create `tests/test_saxs_detector_corrections.py`: pure protocol, compatibility, identity, and transaction tests.
- Create `tests/test_saxs_detector_correction_integration.py`: preprocessing integration and ownership tests.
- Extend `tests/test_saxs_edf_metadata_quality.py`: header ownership normalization.
- Update the task card with exact evidence; add no calibration files.

### Task 1: Define immutable request, result, and registry contracts

- [ ] **Step 1: Add RED strict-contract tests**

```python
def test_disabled_request_is_identity_and_strict_json_safe() -> None:
    image = np.arange(16, dtype=float).reshape(4, 4)
    mask = np.zeros_like(image, dtype=bool)
    result = evaluate_detector_correction(
        image,
        mask,
        DetectorCorrectionRequest.disabled(sample_source_id="sample-1"),
    )
    np.testing.assert_array_equal(result.effective_image, image)
    np.testing.assert_array_equal(result.effective_mask, mask)
    assert result.applicable is False
    assert result.level == "Diagnostic"
    json.dumps(result.to_evidence_dict(), allow_nan=False)


def test_default_registry_has_no_production_backend() -> None:
    assert default_detector_correction_registry().policy_ids == ()
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_detector_corrections.py -q`

- [ ] **Step 3: Implement frozen public types**

```python
CorrectionMode = Literal["disabled", "candidate", "reviewed"]
CorrectionStatus = Literal["applied", "rejected", "unavailable", "not_requested", "candidate_only"]

@dataclass(frozen=True)
class DetectorCalibrationFrame:
    role: str
    source_id: str
    content_digest: str
    image: np.ndarray = field(repr=False, compare=False)
    metadata: Mapping[str, Any]

@dataclass(frozen=True)
class DetectorCorrectionRequest:
    mode: CorrectionMode
    sample_source_id: str
    policy_id: str | None
    review_record_digest: str | None
    frames: tuple[DetectorCalibrationFrame, ...]
    explicit_scalars: Mapping[str, float]
    geometry_digest: str | None

@dataclass(frozen=True)
class DetectorCorrectionResult:
    effective_image: np.ndarray = field(repr=False, compare=False)
    effective_mask: np.ndarray = field(repr=False, compare=False)
    correction_ledger: tuple[CorrectionLedgerEntry, ...]
    candidate_systematic_harmonic: Mapping[str, Any]
    level: str
    applicable: bool
    reason_codes: tuple[str, ...]
```

Factories copy arrays, set them read-only, validate digests, and keep arrays out
of `to_evidence_dict()`. Reuse Task 1 `CorrectionLedgerEntry`; do not define a
second incompatible ledger type.

- [ ] **Step 4: Add the owner-controlled registry**

```python
class DetectorCorrectionBackend(Protocol):
    policy_id: str
    operation_order: tuple[str, ...]

    def apply_validated(
        self,
        sample: np.ndarray,
        mask: np.ndarray,
        request: DetectorCorrectionRequest,
    ) -> tuple[np.ndarray, np.ndarray, tuple[CorrectionLedgerEntry, ...]]: ...


@dataclass(frozen=True)
class DetectorCorrectionRegistry:
    backends: Mapping[str, DetectorCorrectionBackend]

    @property
    def policy_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.backends))
```

`default_detector_correction_registry()` returns an empty mapping. There is no
environment variable, entry-point discovery, or config-only bypass.

- [ ] **Step 5: Run contract GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_detector_corrections.py -q`

### Task 2: Validate requests transactionally and fail closed

- [ ] **Step 1: Add RED compatibility tests**

Cover duplicate roles, shape mismatch, detector model/serial mismatch,
non-positive exposure, geometry digest mismatch, flat-field-already-applied,
backend-owned polarization/solid angle, nonfinite arrays, invalid flat pixels,
missing explicit transmission/thickness, stale review digest, and unknown
policy ID.

```python
@pytest.mark.parametrize("mutator, reason", incompatible_requests())
def test_incompatible_request_never_changes_authoritative_pixels(mutator, reason) -> None:
    image, mask, request = reviewed_fixture()
    rejected = evaluate_detector_correction(image, mask, mutator(request), registry=test_registry())
    np.testing.assert_array_equal(rejected.effective_image, image)
    np.testing.assert_array_equal(rejected.effective_mask, mask)
    assert rejected.applicable is False
    assert reason in rejected.reason_codes
    assert not any(item.status == "applied" for item in rejected.correction_ledger)
```

- [ ] **Step 2: Implement whole-request validation before backend dispatch**

Return `CorrectionValidation` containing `accepted`, normalized detached facts,
and reason codes. Validate every requested operation before calling a backend.
Never partially apply an accepted prefix. Legacy `background_file`,
`transmission=1.0`, or `thickness=1.0` defaults do not count as explicit
review evidence.

- [ ] **Step 3: Define mode behavior**

```python
if request.mode == "disabled":
    return identity_result("detector_correction_disabled")
if not validation.accepted:
    return identity_result(*validation.reason_codes)
if request.mode == "candidate":
    return identity_result("detector_correction_candidate_only", ledger=validation.ledger)
backend = registry.backends.get(request.policy_id or "")
if backend is None:
    return identity_result("detector_correction_backend_unavailable", ledger=validation.ledger)
return commit_backend_transaction(backend, image, mask, request)
```

Candidate mode may report compatibility but cannot return candidate pixels as
effective pixels. Backend exceptions, nonfinite output, shape changes, mutated
inputs, or incomplete ledgers roll back to identity.

- [ ] **Step 4: Prove negative values are preserved by the protocol**

The test backend returns a finite negative corrected pixel. Assert the
transaction does not clip it and the mask remains independent. Also record the
known downstream limitation: manual 1D integration currently excludes
non-positive intensity while chi-by-q retains finite negatives. Because no
production backend is active, do not change that scientific behavior here;
keep it as the activation stop gate.

- [ ] **Step 5: Run validation GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_detector_corrections.py -q`

### Task 3: Normalize EDF ownership metadata

- [ ] **Step 1: Add RED metadata tests**

```python
def test_edf_metadata_records_correction_claims_without_promoting_review() -> None:
    metadata = normalize_edf_detector_metadata({
        "FlatFieldStatus": "corrected",
        "PolarizationCorrection": "applied",
    })
    assert metadata["flat_field_status"] == "corrected"
    assert metadata["polarization_correction_status"] == "applied"
    assert metadata["calibration_reviewed"] is False
```

- [ ] **Step 2: Add fixed known-key normalization**

Normalize flat-field, dark, detector-background, polarization, solid-angle,
detector identity, exposure, threshold/cutoff, and geometry-owner header keys.
Unknown keys are excluded. Header completeness remains distinct from reviewed
calibration validity.

- [ ] **Step 3: Add a new review scope identifier**

Use `saxs.detector_calibration` for future review records. Do not extend the
meaning of existing `saxs.2d` reviews or accept them as calibration approval.
This task only validates a supplied review digest/scope; it does not add a GUI
review workflow.

- [ ] **Step 4: Run metadata GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_edf_metadata_quality.py -q`

### Task 4: Integrate the inactive plugin into preprocessing

- [ ] **Step 1: Add RED integration tests**

```python
def test_preprocess_default_correction_is_numerical_identity() -> None:
    baseline = preprocess_pipeline(image, copy.deepcopy(cfg), detector_header=header)
    plugin = preprocess_pipeline(
        image,
        copy.deepcopy(cfg),
        detector_header=header,
        detector_correction_request=DetectorCorrectionRequest.disabled("sample"),
    )
    np.testing.assert_array_equal(plugin.q, baseline.q)
    np.testing.assert_array_equal(plugin.I_raw, baseline.I_raw)
    assert plugin.detector_correction_evidence["applicable"] is False


def test_one_effective_image_and_mask_feed_all_integrations() -> None:
    result = preprocess_pipeline(
        image,
        cfg,
        detector_correction_request=reviewed_request(),
        detector_correction_registry=test_registry(),
    )
    assert result.integration_input_digest == result.sector_map_input_digest
```

- [ ] **Step 2: Add explicit optional preprocess arguments**

```python
def preprocess_pipeline(
    image: np.ndarray,
    cfg: SAXSConfig,
    *,
    detector_correction_request: DetectorCorrectionRequest | None = None,
    detector_correction_registry: DetectorCorrectionRegistry | None = None,
    **existing_kwargs: Any,
) -> PreprocessResult:
```

The default request is disabled and the default registry is empty. Resolve the
confirmed base mask first, evaluate correction once, and pass the result's
effective image/mask to full, directional, and chi-by-q integration paths.

- [ ] **Step 3: Add ownership conflict guards**

When a registered backend ledger says polarization, solid angle, or detector
background was applied, reject simultaneous legacy/pyFAI ownership. Do not
silently skip one owner. In this task the production registry is empty, so all
normal runs retain current behavior.

- [ ] **Step 4: Transport detached evidence**

Attach `detector_correction_evidence` to processed and detector quality
reports. Include status, policy ID, source IDs/digests, operation ledger,
applicability, and reasons. Exclude arrays, paths, arbitrary metadata, and
candidate pixels. Preserve the raw detector report separately.

- [ ] **Step 5: Run integration GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_detector_correction_integration.py tests/test_saxs_preprocess.py tests/test_saxs_2d_evidence_propagation.py -q`

### Task 5: Verify and checkpoint the inactive foundation

- [ ] **Step 1: Run required verification**

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_detector_corrections.py tests/test_saxs_detector_correction_integration.py tests/test_saxs_edf_metadata_quality.py -q
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
$env:PYTHONUTF8='1'
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-calibration-correction-plugin.md --changed --types
git diff --check
```

- [ ] **Step 2: Record open scientific activation gates**

Update the task card to state that software contracts passed but production
registry remains empty. Record the missing reviewed formulas, calibration EDF
roles, detector/geometry compatibility evidence, pyFAI ownership decision,
negative-support parity decision, and real-data review. Do not label the task
as real calibration validation.

- [ ] **Step 3: Review and checkpoint the exact allowlist**

```powershell
python scripts/auto_commit.py --message "feat(saxs): add inactive detector correction plugin" --files polynexus/core/saxs_engine/saxs_detector_correction.py polynexus/core/saxs_engine/config.py polynexus/core/saxs_engine/io.py polynexus/core/saxs_engine/preprocess.py polynexus/core/saxs_engine/saxs_quality_contracts.py polynexus/core/saxs_engine/__init__.py tests/test_saxs_detector_corrections.py tests/test_saxs_detector_correction_integration.py tests/test_saxs_edf_metadata_quality.py docs/agent/tasks/2026-08-03-saxs-calibration-correction-plugin.md
```

Do not register a production backend or push. Record the inactive-plugin and
unchanged-baseline evidence, then continue to Task 5 only when no documented
stop gate is triggered. Human scientific review remains required before merge.
