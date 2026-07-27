# SAXS candidate replay and calibration audit implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add JSON-safe, mode-aware SAXS candidate replay provenance and verify that existing calibration gates prevent unsafe promotion.

**Architecture:** A pure `PreprocessReplayAudit` DTO will normalize hashes,
evidence, decision, mode context, and application flags. The shared
preprocessing orchestrator will create one row per SAXS trial and attach the
rows to the report and engine as candidate-only audit data. SAXS export will
copy the rows read-only; the existing physical evidence and decision engine
remain authoritative. Calibration changes are limited to contract coverage if
the existing loader already supplies the required blockers.

**Tech Stack:** Python dataclasses, existing preprocessing contracts and
`stable_config_hash`, JSON-safe normalization, pytest, repository verifier.

---

### Task 1: Add the replay audit DTO

**Files:**
- Create: `polynexus/core/preprocess_optimization/replay.py`
- Modify: `polynexus/core/preprocess_optimization/__init__.py`
- Test: `tests/test_preprocess_replay_contract.py`

- [ ] **Step 1: Write the failing contract tests**

Add tests for one successful and one failed replay:

```python
def test_replay_audit_is_json_safe_and_hashes_configs() -> None:
    audit = build_preprocess_replay_audit(
        candidate=_candidate(),
        source_config={"savgol_window": 7},
        effective_config={"savgol_window": 9},
        mode="temperature",
        source_context={"condition_values": [20.0, float("nan")]},
        evidence=_evidence(),
        decision=_decision(),
        trial_engine_created=True,
        error="",
    )

    payload = audit.to_dict()
    json.dumps(payload, allow_nan=False)
    assert payload["original_config_hash"] == stable_config_hash({"savgol_window": 7})
    assert payload["effective_config_hash"] == stable_config_hash({"savgol_window": 9})
    assert payload["mode"] == "temperature"
    assert payload["original_preserved"] is True
    assert payload["apply_performed"] is False
    assert payload["source_context"]["condition_values"][1] is None


def test_failed_replay_has_no_effective_hash_and_cannot_apply() -> None:
    audit = build_preprocess_replay_audit(
        candidate=_candidate(),
        source_config={"savgol_window": 7},
        effective_config=None,
        mode="strain",
        source_context={},
        evidence=_evidence(run_status="failed"),
        decision=_decision(decision="keep_original"),
        trial_engine_created=False,
        error="candidate_timeout",
    )

    assert audit.effective_config_hash is None
    assert audit.apply_allowed is False
    assert audit.apply_performed is False
    assert audit.error == "candidate_timeout"
```

Run:

```powershell
python -m pytest tests/test_preprocess_replay_contract.py -q
```

Expected: FAIL because the replay module and builder do not exist.

- [ ] **Step 2: Implement the minimum DTO and normalizer**

Implement `PreprocessReplayAudit` with these fields:

```python
schema_version: str
candidate_id: str
technique: str
mode: str
generation_reason: str
source_context: dict[str, Any]
original_config_hash: str
effective_config_hash: str | None
run_status: str
trial_engine_created: bool
error: str
evidence: dict[str, Any]
decision: dict[str, Any]
original_preserved: bool = True
apply_allowed: bool = False
apply_performed: bool = False
```

`build_preprocess_replay_audit` must hash only the supplied configuration
snapshots, convert non-finite numbers to `None` recursively, copy evidence and
decision dictionaries, force `apply_performed=False` for replay creation, and
serialize with `json.dumps(..., allow_nan=False)`. It must not include raw q/I
arrays or a raw data path.

Export the DTO and builder from `preprocess_optimization.__init__`.

- [ ] **Step 3: Run the contract tests**

Run the command from Step 1. Expected: both tests pass and no production
algorithm output changes.

- [ ] **Step 4: Commit the atomic DTO slice**

```powershell
python scripts/auto_commit.py --message "feat(preprocess): add replay audit contract" --files polynexus/core/preprocess_optimization/replay.py polynexus/core/preprocess_optimization/__init__.py tests/test_preprocess_replay_contract.py
```

### Task 2: Attach replay rows to the SAXS orchestrator

**Files:**
- Modify: `polynexus/orchestrator_preprocess.py`
- Modify: `polynexus/core/saxs_engine/saxs_ai_rescue.py` only if the final
  decision wrapper needs a replay-safe mode field.
- Test: `tests/test_saxs_ai_orchestrator_handoff.py`
- Test: `tests/test_orchestrator_preprocess.py`

- [ ] **Step 1: Write failing integration assertions**

Extend the valid SAXS handoff test to assert:

```python
replay = report["saxs_ai_rescue_replay"]
assert replay
assert all(item["technique"] == "SAXS" for item in replay)
assert all(item["original_preserved"] is True for item in replay)
assert all(item["apply_performed"] is False for item in replay)
assert all("original_config_hash" in item for item in replay)
assert orchestrator._engine.saxs_ai_rescue_replay == replay
json.dumps(replay, allow_nan=False)
```

Run the focused handoff tests and confirm the new field is absent/fails before
implementation.

- [ ] **Step 2: Add trial metadata without changing trial behavior**

In `_execute_preprocess_candidate`, retain the current return keys and add:

```python
"original_config_hash": stable_config_hash(base_config),
"effective_config_hash": (
    stable_config_hash(self._config_to_dict(effective_config_object))
    if effective_config_object is not None else None
),
"trial_engine_created": trial_engine is not None,
```

For hash mismatch, change, or timeout paths, return the same metadata with a
`None` effective hash when no effective configuration exists.

- [ ] **Step 3: Build one replay row per SAXS trial**

In `_run_preprocess_intent`, collect rows after final candidate selection so
the selected candidate uses the final margin-aware SAXS decision and all other
candidates retain their own existing trial decision. Derive `mode` from the
engine's existing `cfg.experiment_type` and temperature/strain result fields;
do not infer a mode from an LLM string. Copy only bounded workspace condition
context (`condition_context`, `condition_values`, `sample`, and `batch`) into
`source_context`. Attach the resulting list to:

```python
report["saxs_ai_rescue_replay"] = replay_rows
engine.saxs_ai_rescue_replay = replay_rows
```

The replay builder must receive the existing `PreprocessEvidence` and decision
dict. It must not call a second SAXS analyzer, add a second score, or commit a
candidate. Invalid intents and no-candidate reports must use an empty replay
list and preserve their existing fail-closed reason.

- [ ] **Step 4: Run focused orchestration tests**

```powershell
python -m pytest tests/test_saxs_ai_orchestrator_handoff.py tests/test_orchestrator_preprocess.py -q
```

Expected: all existing tests plus the new replay assertions pass; default
shadow remains `keep_original` and the control configuration is unchanged.

- [ ] **Step 5: Commit the orchestrator slice**

```powershell
python scripts/auto_commit.py --message "feat(saxs): record candidate replay provenance" --files polynexus/orchestrator_preprocess.py polynexus/core/saxs_engine/saxs_ai_rescue.py tests/test_saxs_ai_orchestrator_handoff.py tests/test_orchestrator_preprocess.py
```

### Task 3: Preserve replay provenance through SAXS export

**Files:**
- Modify: `polynexus/core/saxs_export_bundle.py`
- Test: `tests/test_saxs_ai_orchestrator_handoff.py`
- Test: `tests/test_saxs_export_bundle.py`

- [ ] **Step 1: Write the failing export assertion**

After a valid shadow handoff, assert:

```python
quality = _quality_evidence_payload(orchestrator._engine, "temperature")
assert quality["ai_rescue"]["replay"] == report["saxs_ai_rescue_replay"]
```

Run the focused export tests and confirm the new key is missing.

- [ ] **Step 2: Add read-only export lookup**

Read `saxs_ai_rescue_replay` from the engine first and then its result, exactly
like the existing plan/decision lookup. Add it under `ai_rescue["replay"]`
only when present. Pass it through the existing `_jsonable` function; do not
recompute or promote any evidence during export.

- [ ] **Step 3: Run export and provenance tests**

```powershell
python -m pytest tests/test_saxs_ai_orchestrator_handoff.py tests/test_saxs_export_bundle.py -q
```

Expected: existing quality evidence and manifest behavior remain unchanged,
with replay rows added as an audit-only field.

- [ ] **Step 4: Commit the export slice**

```powershell
python scripts/auto_commit.py --message "feat(saxs): export replay audit provenance" --files polynexus/core/saxs_export_bundle.py tests/test_saxs_ai_orchestrator_handoff.py tests/test_saxs_export_bundle.py tests/test_saxs_export_provenance.py
```

### Task 4: Cover all SAXS modes and calibration blockers

**Files:**
- Modify: `tests/test_saxs_ai_orchestrator_handoff.py`
- Modify: `tests/test_orchestrator_preprocess.py`
- Modify: `tests/test_preprocess_calibration.py`
- Modify: `polynexus/core/preprocess_optimization/calibration.py` only if a
  failing test demonstrates a missing blocker.

- [ ] **Step 1: Add mode-specific fake-engine tests**

Run the same candidate replay path with `experiment_type="static"`,
`"temperature"`, and `"strain"`. Assert the audit mode matches the engine
context, failed trials contain the real error, missing mode evidence remains
missing, and every path keeps the original control configuration.

- [ ] **Step 2: Add SAXS calibration blocker tests**

Use `get_preprocess_policy("SAXS")` to prove:

```python
empty = calibrate_cases([], policy=policy)
assert empty.promotion_allowed is False
assert "no_calibration_cases" in empty.blockers

low_coverage = calibrate_cases([case(evidence_coverage=0.5)], policy=policy)
assert "insufficient_evidence_coverage" in low_coverage.blockers

disagreement = calibrate_cases([case(expert_accept=True, selected=False)], policy=policy)
assert "insufficient_expert_agreement" in disagreement.blockers
```

Also retain the existing report hash, technique, schema, policy, generator,
and core-version loader tests. Do not loosen them to make a case pass.

- [ ] **Step 3: Run mode and calibration tests**

```powershell
python -m pytest tests/test_saxs_ai_orchestrator_handoff.py tests/test_orchestrator_preprocess.py tests/test_preprocess_calibration.py -q
```

Expected: all mode paths remain candidate-only and all unsafe calibration
profiles remain blocked.

- [ ] **Step 4: Commit the mode/calibration slice**

```powershell
python scripts/auto_commit.py --message "test(saxs): cover replay modes and calibration gates" --files tests/test_saxs_ai_orchestrator_handoff.py tests/test_orchestrator_preprocess.py tests/test_preprocess_calibration.py polynexus/core/preprocess_optimization/calibration.py
```

### Task 5: Verify and record the checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-27-saxs-candidate-replay-calibration.md`
- Modify: `docs/acceptance/2026-07-27-saxs-real-workbench-acceptance.md` only for
  verified new evidence.
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [ ] **Step 1: Run the focused SAXS matrix**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_candidate_replay'
python -m pytest tests/test_preprocess_replay_contract.py tests/test_saxs_ai_rescue_bridge.py tests/test_saxs_ai_orchestrator_handoff.py tests/test_orchestrator_preprocess.py tests/test_preprocess_calibration.py tests/test_saxs_export_bundle.py -q
```

- [ ] **Step 2: Run the structured verifier**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-candidate-replay-calibration.md --changed --types
```

Record the exact test counts and warnings; do not call a timeout a pass.

- [ ] **Step 3: Run full/boundary verification**

```powershell
python scripts/verify.py --changed --types --full --boundary
```

Use an external basetemp and preserve any pre-existing untracked diagnostics.

- [ ] **Step 4: Update durable records and checkpoint**

Mark only verified acceptance checkboxes, record known limitations (including
the remaining human GUI/scientific gate), run `git diff --check`, then call:

```powershell
python scripts/auto_commit.py --message "feat(saxs): audit candidate replay and calibration gates" --files polynexus/core/preprocess_optimization/replay.py polynexus/core/preprocess_optimization/__init__.py polynexus/orchestrator_preprocess.py polynexus/core/saxs_export_bundle.py tests/test_preprocess_replay_contract.py tests/test_saxs_ai_orchestrator_handoff.py tests/test_orchestrator_preprocess.py tests/test_preprocess_calibration.py tests/test_saxs_export_bundle.py docs/agent/tasks/2026-07-27-saxs-candidate-replay-calibration.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

## Plan self-review

- Spec coverage: replay fields, mode handling, decision safety, calibration
  blockers, export provenance, testing, and human acceptance boundaries are
  covered by Tasks 1–5.
- Placeholder scan: no implementation step depends on an unspecified helper;
  each new helper, field, test target, and command is named.
- Type consistency: the replay builder consumes the existing
  `PreprocessCandidate`, `PreprocessEvidence`, and decision dictionaries; the
  orchestrator keeps its current trial return keys and adds metadata only.
- Scope: no raw data, SAXS algorithm, publication threshold, provider call, or
  tiered-auto policy is changed by this plan.
