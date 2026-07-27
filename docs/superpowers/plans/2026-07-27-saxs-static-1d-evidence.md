# SAXS Static 1D Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or superpowers:subagent-driven-development) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transport existing static SAXS 1D evidence through single-frame and
unconditioned batch parameters, Workbench, History, and Export without changing
scientific calculations or condition-axis semantics.

**Architecture:** Keep evidence construction in the SAXS core and add one pure
batch-helper boundary for copying frame evidence and aggregating existing
metric mappings. `SAXSEngine` owns transport selection, the GUI consumes only
the resulting parameters payload, and Export builds a static quality snapshot
from the same result DTOs. Static batch scope is explicit metadata so existing
`Trend` quality levels cannot be presented as temperature/strain trends.

**Tech Stack:** Python, dataclasses/mappings, NumPy, Pytest, existing SAXS
quality contracts, Results Workbench presentation services, JSON export.

---

## File map

- Modify `polynexus/core/saxs_batch_helpers.py`: add immutable copying of the
  three existing frame evidence fields and a static-batch summary helper.
- Modify `polynexus/core/saxs.py`: transport evidence for static single and
  static batch parameters, preserving all legacy numeric fields.
- Modify `polynexus/gui/saxs_results_table_service.py`: format scoped static
  batch review text through existing `risk_text`/`next_text` channels.
- Modify `polynexus/core/saxs_export_bundle.py`: include aligned static batch
  frame evidence and its existing summary in `quality_evidence.json`.
- Modify `tests/test_saxs_batch_parameters.py`: engine transport and alignment
  regressions.
- Modify `tests/test_saxs_workbench_series_evidence.py`: static batch Workbench,
  Diagnostics, and History regressions.
- Modify `tests/test_saxs_export_bundle.py`: static single/batch provenance
  regressions.
- Create `docs/superpowers/specs/2026-07-27-saxs-static-1d-evidence-design.md`:
  approved design boundary.
- Create `docs/agent/tasks/2026-07-27-saxs-static-1d-evidence.md`: task card and
  acceptance evidence.
- Create this plan under `docs/superpowers/plans/`.
- Update `docs/agent/memory/current-state.md` and `active-work.md` only after
  verification, recording final evidence and limitations.

### Task 1: Add the pure static evidence helpers

**Files:**

- Modify: `polynexus/core/saxs_batch_helpers.py`
- Test: `tests/test_saxs_batch_parameters.py`

- [ ] **Step 1: Write the failing tests**

Add tests that construct `SAXSResult`-like objects with distinct nested
`data_quality_report`, `guinier_evidence`, and `metric_evidence` mappings and
assert:

```python
from polynexus.core.saxs_batch_helpers import (
    build_static_batch_metric_evidence,
    copy_saxs_quality_evidence,
)

def test_copy_saxs_quality_evidence_copies_only_present_contract_fields():
    source = SimpleNamespace(
        data_quality_report={"level": "Diagnostic"},
        guinier_evidence={"metric": {"level": "Trend"}},
        metric_evidence={"porod": {"level": "Trend"}},
        quality_flag="WARN",
    )
    copied = copy_saxs_quality_evidence(source)

    assert copied == {
        "data_quality_report": {"level": "Diagnostic"},
        "guinier_evidence": {"metric": {"level": "Trend"}},
        "metric_evidence": {"porod": {"level": "Trend"}},
    }
    assert copied["metric_evidence"] is not source.metric_evidence

def test_build_static_batch_metric_evidence_keeps_missing_frame_counts():
    analyses = [
        SimpleNamespace(metric_evidence={"porod": {"level": "Trend"}}),
        None,
        SimpleNamespace(metric_evidence={"porod": {"level": "Diagnostic"}}),
    ]

    summary = build_static_batch_metric_evidence(analyses)

    assert summary["porod"]["frame_count"] == 3
    assert summary["porod"]["evidence_frame_count"] == 2
    assert summary["porod"]["missing_frame_count"] == 1
    assert summary["porod"]["level"] == "Diagnostic"
    assert "series_metric_missing_frames" in summary["porod"]["reason_codes"]
    assert summary["porod"]["source_ref"] == "saxs_static_batch.metric_evidence"
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```powershell
pytest tests/test_saxs_batch_parameters.py -k "copy_saxs_quality_evidence or static_batch_metric_evidence" -q
```

Expected: collection succeeds and both tests fail because the two helpers do
not yet exist.

- [ ] **Step 3: Implement the smallest helper boundary**

Implement `copy_saxs_quality_evidence(value)` to deep-copy only the three
existing evidence attributes when they are not `None`. Implement
`build_static_batch_metric_evidence(analyses)` by extracting each aligned
`metric_evidence` mapping, retaining `None` for missing results, and passing
those mappings to `build_series_metric_evidence(...,
source_ref="saxs_static_batch.metric_evidence")`. Do not alter evidence levels
or calculate any physical quantity.

- [ ] **Step 4: Run the focused tests and confirm GREEN**

Run the same Pytest command. Expected: both tests pass and no existing batch
helper tests regress.

### Task 2: Transport static single and batch evidence

**Files:**

- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/core/saxs_batch_helpers.py`
- Test: `tests/test_saxs_batch_parameters.py`

- [ ] **Step 1: Write failing engine transport tests**

Add tests for `SAXSEngine.get_parameters()` that assert a cached static
`SAXSResult` exposes exact deep-copied evidence alongside `L_nm`, `lc_nm`, and
other legacy numbers. Add a multi-file test with three aligned results
(`usable`, `None`, `diagnostic`) and assert each `_batch_data` row has only its
own evidence, the missing row has no evidence key, and the top-level payload
contains:

```python
assert params["metric_evidence_scope"] == "static_batch"
assert params["metric_evidence"]["porod"]["missing_frame_count"] == 1
assert params["metric_evidence"]["porod"]["level"] == "Diagnostic"
```

- [ ] **Step 2: Run the new tests and confirm RED**

Run:

```powershell
pytest tests/test_saxs_batch_parameters.py -k "static_single or static_batch" -q
```

Expected: the new assertions fail because static parameters currently contain
only legacy structural values and rows do not carry evidence.

- [ ] **Step 3: Implement transport**

In the static single `get_parameters()` branches, merge the result of
`copy_saxs_quality_evidence(self._analysis)` into the legacy parameter dict.
In the static batch path, copy evidence from the aligned `_batch_results[i]`
into each row before `_apply_batch_params_to_results()` changes only existing
parameter layers. When constructing the batch payload, add the summary from
`build_static_batch_metric_evidence()` and
`metric_evidence_scope="static_batch"`. Keep the helper additive so
temperature/strain callers retain their current series payloads.

- [ ] **Step 4: Run focused engine regressions**

Run:

```powershell
pytest tests/test_saxs_batch_parameters.py -q
```

Expected: all tests pass, including failed-frame alignment and existing raw /
calibrated parameter compatibility.

### Task 3: Make scoped evidence visible in Workbench and History

**Files:**

- Modify: `polynexus/gui/saxs_results_table_service.py`
- Test: `tests/test_saxs_workbench_series_evidence.py`

- [ ] **Step 1: Write failing presentation tests**

Add a static payload test with `metric_evidence_scope="static_batch"` and a
downgraded Porod summary. Assert `risk_text + next_text` contains “batch” and
the coverage/reason code, but does not contain “temperature trend” or “strain
trend”. Assert the Diagnostics section serializes the nested
`metric_evidence`. Add a persistence round-trip assertion using the existing
`persist_analysis_run()` path with a static submodule.

- [ ] **Step 2: Run tests and confirm RED**

Run:

```powershell
pytest tests/test_saxs_results_table_service.py tests/test_saxs_workbench_series_evidence.py -k "static_batch or persistence" -q
```

Expected: the payload remains visible in Diagnostics, but the new scoped batch
wording assertion fails.

- [ ] **Step 3: Implement scoped formatting**

Update the existing review formatter to read `metric_evidence_scope` from the
immutable copied payload. For `static_batch`, prefix the review detail with
“Batch quality” (and its translated equivalent) and keep all existing metric
level/count/reason formatting. Leave temperature/strain behavior byte-for-byte
compatible. Do not inspect engine objects or recompute evidence in the GUI.

- [ ] **Step 4: Run focused presentation and persistence tests**

Run the two commands from this task's verification matrix for the focused
presentation files. Expected: all existing series review and History tests plus
the new static tests pass.

### Task 4: Extend static Export provenance

**Files:**

- Modify: `polynexus/core/saxs_export_bundle.py`
- Test: `tests/test_saxs_export_bundle.py`

- [ ] **Step 1: Write failing Export tests**

Add a single-frame assertion that existing `payload["static"]["metric_evidence"]`
is unchanged. Add a three-result static batch fixture and assert:

```python
static = payload["static"]
assert static["metric_evidence_scope"] == "static_batch"
assert static["metric_evidence"]["porod"]["missing_frame_count"] == 1
assert [frame["frame_index"] for frame in static["frames"]] == [0, 2]
assert static["frames"][0]["metric_evidence"]["porod"]["level"] == "Trend"
```

The failed frame must not acquire a copied evidence object.

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```powershell
pytest tests/test_saxs_export_bundle.py -k "static" -q
```

Expected: the single-frame compatibility test passes and the new batch test
fails because static Export currently inspects only the first analysis.

- [ ] **Step 3: Implement the static quality snapshot**

Add a static-specific snapshot helper that preserves the existing single-frame
shape and, for multiple `_batch_results`, emits aligned `frames` entries only
when a result has quality evidence. Put the existing conservative batch
summary and `metric_evidence_scope` at the static level. Pass the snapshot
through `_jsonable()` exactly once at the existing Export boundary.

- [ ] **Step 4: Run Export tests and inspect strict JSON**

Run:

```powershell
pytest tests/test_saxs_export_bundle.py -q
```

Expected: all Export tests pass and generated JSON contains no `NaN` or
`Infinity` tokens.

### Task 5: Full verification and checkpoint

**Files:**

- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: implementation/test files from Tasks 1–4

- [ ] **Step 1: Run the focused SAXS matrix**

Run:

```powershell
$taskTempRoot = 'C:\Temp\PolyNexus_saxs_static_1d_evidence'
$env:PYTEST_ADDOPTS = "-o addopts= --basetemp=$taskTempRoot"
pytest tests/test_saxs_batch_parameters.py tests/test_saxs_results_table_service.py tests/test_saxs_workbench_series_evidence.py tests/test_saxs_export_bundle.py -q
```

Expected: zero failures.

- [ ] **Step 2: Run the complete SAXS and repository checks**

Run:

```powershell
pytest tests/test_saxs_*.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-static-1d-evidence.md --changed --types
git diff --check
```

Expected: the SAXS matrix, task verifier, and whitespace check exit successfully.
Any pre-existing GUI lint blocker is recorded rather than modified.

- [ ] **Step 3: Update durable memory with exact evidence**

Record the changed contract, verification counts, checkpoint hash, and any
remaining scientific-review limitation in `current-state.md` and
`active-work.md`. Do not copy raw logs or temporary paths into memory.

- [ ] **Step 4: Create the atomic checkpoint**

After verification, derive the exact changed-file allowlist and run:

```powershell
python scripts/auto_commit.py `
  --message "feat(saxs): close static 1d evidence transport" `
  --files docs/superpowers/specs/2026-07-27-saxs-static-1d-evidence-design.md `
          docs/superpowers/plans/2026-07-27-saxs-static-1d-evidence.md `
          docs/agent/tasks/2026-07-27-saxs-static-1d-evidence.md `
          polynexus/core/saxs_batch_helpers.py `
          polynexus/core/saxs.py `
          polynexus/gui/saxs_results_table_service.py `
          polynexus/core/saxs_export_bundle.py `
          tests/test_saxs_batch_parameters.py `
          tests/test_saxs_results_table_service.py `
          tests/test_saxs_workbench_series_evidence.py `
          tests/test_saxs_export_bundle.py `
          docs/agent/memory/current-state.md `
          docs/agent/memory/active-work.md
```

Expected: one local checkpoint commit is created; no push, merge, deploy, or
unrelated pre-existing file is included.

## Self-review

- The spec's single-frame, batch, Workbench, History, Export, failure, and
  verification requirements each map to Tasks 1–5.
- No implementation step introduces a new physical cutoff or calls an AI
  model.
- `metric_evidence_scope` is written by the core transport and read only by
  the presentation/export boundaries; temperature/strain series payloads keep
  their existing keys and behavior.
- Missing/failed frames are represented by absent evidence mappings and counted
  by the existing conservative aggregator; no frame is imputed.
