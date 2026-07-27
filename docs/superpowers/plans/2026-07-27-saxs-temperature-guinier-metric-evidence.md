# SAXS temperature Guinier metric evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the existing temperature-frame Guinier metric to the common SAXS series evidence contract and verify its propagation.

**Architecture:** Keep `guinier_sequence_evidence` as the Rg-specific sequence contract. Build a read-only per-frame mapping from each point's existing nested `guinier_evidence["metric"]`, then pass it through the existing `build_series_metric_evidence` builder alongside the other method metrics. Existing parameter, Workbench, History, and Export paths consume the resulting summary without new scientific interpretation.

**Tech Stack:** Python dataclasses/mappings, NumPy, pytest, existing SAXS quality contracts, repository verifier.

---

### Task 1: Add RED regression coverage for the common Guinier series summary

**Files:**
- Modify: `D:\PolyNexus\tests\test_saxs_temperature_guinier_evidence.py`
- Modify: `D:\PolyNexus\tests\test_saxs_mode_evidence_propagation.py`

- [x] **Step 1: Write the failing assertions**

Extend the existing successful temperature-series test with:

```python
assert result.metric_evidence["guinier"]["metric_name"] == "Rg"
assert result.metric_evidence["guinier"]["frame_count"] == 3
assert result.metric_evidence["guinier"]["evidence_frame_count"] == 3
assert result.metric_evidence["guinier"]["level"] == "Trend"
```

Extend the injected-failure test with:

```python
assert result.metric_evidence["guinier"]["missing_frame_count"] == 1
assert result.metric_evidence["guinier"]["evidence_frame_count"] == 2
assert result.metric_evidence["guinier"]["level"] == "Diagnostic"
```

Add an assertion to the mode propagation fixture that a temperature frame's
existing `metric_evidence` remains unchanged and that its separate
`guinier_evidence` still contains the nested `metric` payload.

- [x] **Step 2: Run the focused tests to observe RED**

Run:

```powershell
python -m pytest tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_mode_evidence_propagation.py -q
```

Expected: the new `metric_evidence["guinier"]` assertions fail because the
temperature summary currently includes only Porod, Kratky, invariant, and
lamellar entries.

### Task 2: Derive and aggregate the existing frame Guinier metric

**Files:**
- Modify: `D:\PolyNexus\polynexus\core\saxs_engine\saxs_temperature.py`
- Test: `D:\PolyNexus\tests\test_saxs_temperature_guinier_evidence.py`

- [x] **Step 1: Add a read-only extraction helper**

Near the temperature-series analysis helpers, add a private function with this
behavior:

```python
def _guinier_metric_frame_payload(point):
    evidence = getattr(point, "guinier_evidence", None)
    if not isinstance(evidence, dict):
        return {}
    metric = evidence.get("metric")
    return {"guinier": dict(metric)} if isinstance(metric, dict) else {}
```

The helper must not mutate `point.guinier_evidence` and must return an empty
mapping for missing or malformed nested evidence.

- [x] **Step 2: Include the extracted metric in the existing series builder**

Immediately before the existing `build_series_metric_evidence` call, create
one derived mapping per temperature point by copying each point's existing
`metric_evidence` mapping and adding the extracted `guinier` entry only when
present. Then call the existing builder with `metric_names=("guinier", "porod", "kratky", "invariant", "lamellar")`.

Do not alter `point.metric_evidence`; the derived list is only an input to the
summary builder. Keep the existing sequence builder call unchanged.

- [x] **Step 3: Run the temperature evidence tests GREEN**

Run:

```powershell
python -m pytest tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_mode_evidence_propagation.py -q
```

Expected: all tests pass and the failure frame contributes one missing Guinier
metric without receiving copied evidence.

### Task 3: Verify transport and consumer preservation

**Files:**
- Test: `D:\PolyNexus\tests\test_saxs_workbench_series_evidence.py`
- Modify: `D:\PolyNexus\polynexus\gui\saxs_results_table_service.py`
- Test: `D:\PolyNexus\tests\test_saxs_export_bundle.py`

- [x] **Step 1: Add propagation assertions**

Use an existing temperature result fixture and assert the parameter payload
contains `metric_evidence["guinier"]`, while `guinier_sequence_evidence`
remains present in the quality export payload. Assert figure IDs and roles are
unchanged by reusing the existing temperature profile contract test. The
Workbench formatter labels the common `guinier` key as `Rg` while preserving
all contract levels and counts.

- [x] **Step 2: Run the consumer slice**

Run:

```powershell
python -m pytest tests/test_saxs_workbench_series_evidence.py tests/test_saxs_export_bundle.py tests/test_saxs_workbench_figure_contracts.py tests/test_results_workbench_profiles.py -q
```

Expected: all existing and new assertions pass; no publication role changes.

### Task 4: Run repository verification and record the checkpoint

**Files:**
- Modify: `D:\PolyNexus\docs\agent\tasks\2026-07-27-saxs-temperature-guinier-metric-evidence.md`
- Modify: `D:\PolyNexus\docs\agent\memory\active-work.md`
- Modify: `D:\PolyNexus\docs\agent\memory\current-state.md`
- Modify: this plan

- [x] **Step 1: Run the required verifier and whitespace check**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-temperature-guinier-metric-evidence.md --changed --types
git diff --check
```

Record exact results. A pre-existing finding in an unrelated modified GUI
file must remain explicitly outside this task's allowlist.

- [x] **Step 2: Run the focused SAXS matrix**

Run the focused consumer slice from Task 3 plus the temperature/strain quality
tests. Do not report a full repository pass unless the full command completes.

- [x] **Step 3: Create one atomic local checkpoint**

After verification, run:

```powershell
python scripts/auto_commit.py --message "feat(saxs): add temperature guinier series evidence" --files polynexus/core/saxs_engine/saxs_temperature.py polynexus/gui/saxs_results_table_service.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_mode_evidence_propagation.py tests/test_saxs_workbench_series_evidence.py tests/test_saxs_export_bundle.py docs/agent/tasks/2026-07-27-saxs-temperature-guinier-metric-evidence.md docs/superpowers/specs/2026-07-27-saxs-temperature-guinier-metric-evidence-design.md docs/superpowers/plans/2026-07-27-saxs-temperature-guinier-metric-evidence.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

Do not stage or alter unrelated pre-existing workspace files.

## Plan self-review

- The spec's common-summary and detailed-sequence contracts are both covered.
- Code changes are confined to existing temperature aggregation, Workbench
  label presentation, and focused regression/docs files.
- Missing, malformed, diagnostic, and complete frame behavior is explicitly
  covered.
- No scientific threshold, GUI decision, rescue execution, or publication role
  is introduced.
