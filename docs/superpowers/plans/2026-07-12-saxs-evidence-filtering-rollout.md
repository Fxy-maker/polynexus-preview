# SAXS Evidence Filtering Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add evidence-backed temperature and strain publication filtering to the current-main SAXS provider without importing the integration branch's provider rewrite.

**Architecture:** Reuse the committed `SAXSFrameView`, `FigureEligibilityDecision`, and `publication_role` contracts. The current provider keeps its existing figure IDs, source columns, labels, and scientific values; temperature filters summary sources to eligible main frames, while strain annotates current frame/waterfall definitions and conservatively downgrades mixed evidence. Temperature and strain are separate commits with separate focused tests.

**Tech Stack:** Python 3.12, NumPy, pytest, immutable `FigureDefinition` contracts, shared FigurePipeline publisher.

---

## File map and boundaries

| File | Responsibility in this plan |
|---|---|
| `polynexus/core/saxs_engine/figure_provider.py` | Add evidence-aware temperature source selection, conservative series roles, and evidence recipe metadata while preserving current builders. |
| `tests/test_saxs_temperature_evidence_filtering.py` | Temperature RED/GREEN tests for source omission, emitted final values, roles, and reasons. |
| `tests/test_saxs_strain_evidence_filtering.py` | Strain RED/GREEN tests for frame roles, waterfall downgrade, ordering, and reasons. |
| `docs/acceptance/2026-07-12-mainline-integration-reconciliation-inventory.md` | Record focused evidence and the limits of this partial SAXS migration. |

Do not modify `polynexus/core/saxs_engine/saxs_temperature.py`, `saxs_strain.py`, GUI files, `D:\PolyNexus`, user-local scripts, or PR #9.

## Shared rules for both slices

- Use only `frame_views_from_engine()` and emitted result fields; never call `analyze_single`, `analyze_temperature_series`, or `analyze_strain_series` from the provider.
- Frame indices in evidence recipes are zero-based source indices, matching `SAXSFrameView.index`; existing figure IDs remain one-based display IDs.
- A frame is main only when `classify_frame_eligibility()` returns `highest_role == "main"`.
- `diagnostic` outranks `si`, and `si` outranks `main` when a series contains mixed roles for the purpose of a series definition. Therefore a mixed series is never mislabeled as main.
- When no evidence frames are available, preserve legacy behavior and leave definitions at their default `publication_role="si"`; do not infer main eligibility.
- Omitted source values must be omitted by index selection, never replaced with `nan`, raw fallback values, or newly calculated values.

### Task 1: Temperature evidence plan and main-source filtering

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_provider.py:build_saxs_figure_definitions`, `build_saxs_temperature_definitions`, `_build_temperature_waterfall`, `_build_temperature_summary_definitions`, `_build_temperature_parameters`, `_build_temperature_heatmap`
- Create: `tests/test_saxs_temperature_evidence_filtering.py`

- [x] **Step 1: Add the temperature fixture and a failing rejected-middle-frame test**

Create the fixture directly in the new test file so it does not depend on production constructors:

```python
from types import SimpleNamespace
import numpy as np

from polynexus.core.saxs_engine.figure_provider import build_saxs_figure_definitions


def _temperature_engine_with_evidence(rejected_index=2):
    conditions = [30.0, 45.0, 60.0, 75.0, 90.0]
    q_list = [np.asarray([0.1, 0.2, 0.3])] * len(conditions)
    intensity_list = [np.asarray([10.0, 5.0, 2.0])] * len(conditions)
    params = []
    analyses = []
    for index, condition in enumerate(conditions):
        evidence = {
            "paper_figure_candidate": index != rejected_index,
            "lc_reliability_status": "usable" if index != rejected_index else "low_confidence",
            "Q_star_valid": index != rejected_index,
            "L_nm": 12.125 + index * 0.225,
            "lc_nm": 3.225 + index * 0.125,
            "lc_effective_array": 3.225 + index * 0.125,
            "Q_star": 102.5 + index * 1.75,
            "Xc": 0.265 + index * 0.0125,
            "file": f"frame_{index}.dat",
        }
        params.append(evidence)
        analyses.append(
            SimpleNamespace(
                label=f"frame-{index}",
                condition_value=condition,
                q=q_list[index],
                I=intensity_list[index],
                final_parameters=dict(evidence),
                structure=SimpleNamespace(L=90.0 + index, lc=40.0 + index),
            )
        )
    result = SimpleNamespace(
        temperatures=np.asarray(conditions),
        L_array=np.asarray([item["L_nm"] for item in params]),
        lc_array=np.asarray([item["lc_nm"] for item in params]),
        lc_effective_array=np.asarray([item["lc_nm"] for item in params]),
        Q_star_array=np.asarray([item["Q_star"] for item in params]),
        Xc_array=np.asarray([item["Xc"] for item in params]),
    )
    return SimpleNamespace(
        _temperature_result=result,
        _strain_result=None,
        _condition_type="temperature",
        cfg=SimpleNamespace(experiment_type="temperature"),
        _q_list=q_list,
        _I_list=intensity_list,
        _batch_results=analyses,
        _batch_params=params,
        _conditions=conditions,
        _file_list=[item["file"] for item in params],
    )


def _definition(definitions, figure_id):
    return next(item for item in definitions if item.figure_id == figure_id)
```

Put final values in `_batch_params` that intentionally disagree with raw `analysis.structure` values. Mark frames 0, 1, 3, and 4 with `paper_figure_candidate=True`, `lc_reliability_status="usable"`, and `Q_star_valid=True`; mark frame 2 with `paper_figure_candidate=False`, `lc_reliability_status="low_confidence"`, and `Q_star_valid=False`. Build definitions through the current provider entry point and assert the temperature parameters source excludes condition 60 while retaining the emitted final values for conditions 30, 45, 75, and 90.

```python
def test_temperature_main_sources_omit_rejected_middle_frame():
    engine = _temperature_engine_with_evidence(rejected_index=2)

    definitions = build_saxs_figure_definitions(engine)
    parameters = _definition(definitions, "saxs.series.temperature.parameters")
    source = parameters.data_sources[0]

    assert source.values["temperature_C"] == (30.0, 45.0, 75.0, 90.0)
    assert source.values["L_nm"] == (12.125, 12.35, 12.8, 13.025)
    assert parameters.publication_role == "main"
```

- [x] **Step 2: Run the new test and verify the failure is the missing filter**

Run:

```powershell
python -m pytest tests/test_saxs_temperature_evidence_filtering.py::test_temperature_main_sources_omit_rejected_middle_frame -q
```

Expected result before implementation: FAIL because the current parameters source contains all five temperatures, including 60.0. If collection fails, fix only the fixture/import error and rerun until the assertion fails for the missing filtering behavior.

- [x] **Step 3: Import the shared evidence types and add an evidence plan helper**

Add these imports to the provider before the helper:

```python
from polynexus.core.figures.contracts import FigureEligibilityDecision
from .figure_common import SAXSFrameView
```

Then add a private helper near `_apply_publication_roles` that consumes already-built frame views and returns a plain immutable-by-convention payload:

```python
def _evidence_plan(
    evidence_frames: Sequence[SAXSFrameView],
    frame_count: int,
) -> tuple[dict[int, FigureEligibilityDecision], tuple[int, ...], dict[int, str]]:
    decisions = {
        frame.index: classify_frame_eligibility(frame)
        for frame in evidence_frames
        if 0 <= frame.index < frame_count
    }
    main_indices = tuple(
        index for index in range(frame_count)
        if decisions.get(index, FigureEligibilityDecision("si", ("evidence_missing",))).highest_role == "main"
    )
    reasons = {
        index: "|".join(decision.reasons)
        for index, decision in decisions.items()
        if decision.highest_role != "main"
    }
    return decisions, main_indices, reasons
```

Use the existing `FigureEligibilityDecision` import rather than defining a second role type. Keep the helper local to the provider because this plan does not create a generic multi-technique filtering framework.

- [x] **Step 4: Pass evidence frames into the temperature builder**

In `build_saxs_figure_definitions`, compute `evidence_frames = frame_views_from_engine(engine_state)` once. Pass it to `build_saxs_temperature_definitions` using an optional keyword argument so existing direct callers remain valid:

```python
definitions = build_saxs_temperature_definitions(
    temperature_result,
    tuple(getattr(engine_state, "_q_list", ())),
    tuple(getattr(engine_state, "_I_list", ())),
    evidence_frames=evidence_frames,
)
```

Change the temperature builder signature to `evidence_frames: Sequence[SAXSFrameView] = ()`. Do not change the positional arguments used by existing tests.

- [x] **Step 5: Filter only the main temperature summary sources**

In `build_saxs_temperature_definitions`, after cleaning all frames:

1. Build the evidence plan for `len(cleaned_frames)`.
2. Select `selected_indices = main_indices or tuple(range(frame_count))`; this preserves a SI/diagnostic pack when no frame qualifies for main.
3. Pass `selected_indices` to `_build_temperature_parameters` and `_build_temperature_heatmap`.
4. Keep the waterfall source complete for evidence visibility, but set its role to `si` when any frame is not main.
5. Add one recipe object to every temperature series definition:

```python
"evidence": {
    "included_frame_indices": list(selected_indices),
    "omitted_frame_indices": [index for index in range(frame_count) if index not in selected_indices],
    "omission_reasons": reasons,
}
```

Update `_build_temperature_parameters` and `_build_temperature_heatmap` to slice all aligned arrays by `included_indices` before constructing `values`. The arrays must be sliced together; do not use independent finite-value filtering that could change frame alignment.

- [x] **Step 6: Preserve explicit temperature series roles during final annotation**

Update `_apply_publication_roles` so an explicit non-default role already set by a builder is retained for series definitions. For definitions without an explicit role, use conservative aggregation:

```python
def _aggregate_publication_role(roles):
    roles = tuple(roles)
    if roles and all(role == "main" for role in roles):
        return "main"
    if "si" in roles or not roles:
        return "si"
    return "diagnostic"
```

Per-frame definitions still use the exact frame decision. This prevents a mixed main/diagnostic temperature waterfall from being labeled main.

- [x] **Step 7: Run temperature focused tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_saxs_temperature_evidence_filtering.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_publication_cutover.py tests/test_saxs_mode_evidence_contract.py -q
```

Expected result: all tests pass; existing temperature figure IDs, validation, and publish metadata remain unchanged. Add tests in the new file for missing evidence -> `si`, explicit error -> `diagnostic`, and recipe omission reasons.

- [x] **Step 8: Run shared regressions and commit the temperature slice**

Run:

```powershell
python -m pytest tests/test_figure_contracts.py tests/test_figure_pipeline.py tests/test_figure_production.py tests/test_run_figure_manifest.py tests/test_figure_render_plan_core.py tests/test_figure_assets.py tests/test_figure_publication_audit.py tests/test_figure_recovery_pipeline.py tests/test_manifest_editor_shared_plan.py -q
python -m compileall -q polynexus/core/figures polynexus/core/saxs_engine
git diff --check
```

Expected result: focused/shared tests pass, compileall exits 0, and diff-check emits no output. Commit only the temperature provider and temperature test:

```powershell
git add polynexus/core/saxs_engine/figure_provider.py tests/test_saxs_temperature_evidence_filtering.py
git diff --cached --check
git commit -m "feat(saxs): filter temperature publication evidence"
```

### Task 2: Strain evidence roles and conservative waterfall filtering

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_provider.py:_build_scattering_frame`, `_build_series_waterfall`, `build_saxs_figure_definitions`
- Create: `tests/test_saxs_strain_evidence_filtering.py`

- [x] **Step 1: Add a failing strain mixed-evidence test**

Create the strain fixture directly in the new test file with conditions `[0.0, 25.0, 50.0]`, aligned q/intensity arrays, and emitted evidence where frames 0 and 2 are main and frame 1 is diagnostic:

```python
from types import SimpleNamespace
import numpy as np

from polynexus.core.saxs_engine.figure_provider import build_saxs_figure_definitions


def _strain_engine_with_evidence():
    conditions = [0.0, 25.0, 50.0]
    q_list = [np.asarray([0.1, 0.2, 0.3])] * len(conditions)
    intensity_list = [np.asarray([10.0, 5.0, 2.0])] * len(conditions)
    params = [
        {"paper_figure_candidate": True, "quality_flag": "OK", "file": "frame_0.dat"},
        {"paper_figure_candidate": False, "quality_flag": "ERROR:qstar", "file": "frame_1.dat"},
        {"paper_figure_candidate": True, "quality_flag": "OK", "file": "frame_2.dat"},
    ]
    analyses = [
        SimpleNamespace(
            label=f"frame-{index}",
            condition_value=condition,
            q=q_list[index],
            I=intensity_list[index],
            final_parameters=dict(params[index]),
        )
        for index, condition in enumerate(conditions)
    ]
    return SimpleNamespace(
        _temperature_result=None,
        _strain_result=SimpleNamespace(strains=np.asarray(conditions)),
        _condition_type="strain",
        cfg=SimpleNamespace(experiment_type="strain"),
        _q_list=q_list,
        _I_list=intensity_list,
        _conditions=conditions,
        _batch_results=analyses,
        _batch_params=params,
        _file_list=[item["file"] for item in params],
    )
```

Build current strain definitions and assert:

```python
def test_strain_mixed_evidence_downgrades_waterfall_and_preserves_order():
    definitions = build_saxs_figure_definitions(_strain_engine_with_evidence())

    frames = [item for item in definitions if item.scope == "frame"]
    waterfall = next(item for item in definitions if item.figure_id == "saxs.series.strain.waterfall")

    assert [item.publication_role for item in frames] == ["main", "diagnostic", "main"]
    assert [obj["name"] for obj in waterfall.objects] == ["0% strain", "25% strain", "50% strain"]
    assert waterfall.publication_role == "si"
    assert waterfall.recipe["evidence"]["omission_reasons"][1] == "analysis_rejected_paper_figure"
```

- [x] **Step 2: Run the strain test and verify the failure**

Run:

```powershell
python -m pytest tests/test_saxs_strain_evidence_filtering.py::test_strain_mixed_evidence_downgrades_waterfall_and_preserves_order -q
```

Expected result before implementation: FAIL because the current waterfall has no evidence recipe and is incorrectly assigned the aggregate main role.

- [x] **Step 3: Add evidence metadata to current strain definitions**

Reuse the evidence plan computed in `build_saxs_figure_definitions`. Pass a compact recipe payload into `_build_scattering_frame` and `_build_series_waterfall`:

```python
"evidence": {
    "included_frame_indices": list(range(frame_count)),
    "omitted_frame_indices": [],
    "omission_reasons": {
        index: "|".join(decision.reasons)
        for index, decision in decisions.items()
        if decision.highest_role != "main"
    },
}
```

Keep all current strain waterfall objects and their order. The non-main frames remain visible as SI/diagnostic evidence; no new algorithm or panel is introduced.

- [x] **Step 4: Make series role aggregation conservative and preserve per-frame roles**

Use the `_aggregate_publication_role` implementation from Task 1. Apply the exact decision to each numbered frame definition and the conservative aggregate to the waterfall. Do not filter q/intensity arrays for strain in this slice because the current strain provider has no separate summary source; mixed main/diagnostic evidence is diagnostic, while mixed main/SI evidence is SI.

- [x] **Step 5: Run strain and SAXS regressions**

Run:

```powershell
python -m pytest tests/test_saxs_strain_evidence_filtering.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_publication_cutover.py tests/test_saxs_mode_evidence_contract.py -q
```

Expected result: all tests pass; existing strain labels, waterfall ordering, and publication cutover metadata remain stable.

- [x] **Step 6: Run shared regressions and commit the strain slice**

Run:

```powershell
python -m pytest tests/test_figure_contracts.py tests/test_figure_pipeline.py tests/test_figure_production.py tests/test_run_figure_manifest.py tests/test_figure_render_plan_core.py tests/test_figure_assets.py tests/test_figure_publication_audit.py tests/test_figure_recovery_pipeline.py tests/test_manifest_editor_shared_plan.py -q
python -m compileall -q polynexus/core/figures polynexus/core/saxs_engine
git diff --check
```

Expected result: all focused/shared tests pass with clean compile and diff checks. Commit only the strain test and provider changes:

```powershell
git add polynexus/core/saxs_engine/figure_provider.py tests/test_saxs_strain_evidence_filtering.py
git diff --cached --check
git commit -m "feat(saxs): annotate strain publication evidence"
```

### Task 3: Acceptance evidence and handoff

**Files:**
- Modify: `docs/acceptance/2026-07-12-mainline-integration-reconciliation-inventory.md`
- Read-only verification: the two committed provider slices and their tests

- [x] **Step 1: Record both slice commits and exact test evidence**

Append a SAXS rollout section listing the two commit hashes, the temperature and strain focused commands, the shared regression command, and the fact that `scripts/verify.py` remains unavailable in clean `origin/main` because it is not part of that baseline.

- [x] **Step 2: Run final local verification for this rollout**

Run:

```powershell
python -m pytest tests/test_saxs_temperature_evidence_filtering.py tests/test_saxs_strain_evidence_filtering.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_publication_cutover.py tests/test_saxs_mode_evidence_contract.py -q
python -m pytest tests/test_figure_contracts.py tests/test_figure_pipeline.py tests/test_figure_production.py tests/test_run_figure_manifest.py tests/test_figure_render_plan_core.py tests/test_figure_assets.py tests/test_figure_publication_audit.py tests/test_figure_recovery_pipeline.py tests/test_manifest_editor_shared_plan.py -q
python -m compileall -q polynexus/core/figures polynexus/core/saxs_engine
git diff --check HEAD~2 HEAD
git status --short --branch
```

Expected result: both pytest groups pass, compileall exits 0, diff-check emits no output, and the worktree is clean.

- [x] **Step 3: Commit only the acceptance evidence**

```powershell
git add docs/acceptance/2026-07-12-mainline-integration-reconciliation-inventory.md
git diff --cached --check
git commit -m "docs: record SAXS evidence filtering rollout"
```

Do not push, create a PR, close PR #9, merge main, or sync `D:\PolyNexus` in this plan.

## Plan self-review

- Spec coverage: evidence snapshot boundary is already committed; this plan covers temperature filtering, strain role propagation, failure behavior, stable IDs/source fields, independent commits, rollback boundaries, tests, and acceptance evidence. Representative selection and full provider parity remain explicitly deferred.
- Placeholder scan: no unfinished markers or unspecified implementation steps are present; each code change names the file, function, expected test, and command.
- Type consistency: the plan uses existing `SAXSFrameView`, `FigureEligibilityDecision`, `FigureDefinition.publication_role`, `build_saxs_figure_definitions`, and current temperature/strain builder names.
