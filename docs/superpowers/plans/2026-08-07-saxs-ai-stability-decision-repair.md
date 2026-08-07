# SAXS AI Tuning and Stability Decision Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make SAXS AI recommendations actionable only when the real analysis mode, active perturbations, sequence continuity, orientation evidence, and scientific gates jointly support confirmation.

**Architecture:** Preserve the AI-then-stability workflow and current deterministic sampler. Repair causal symptom routing first, then make the stability bridge mode- and activity-aware, strengthen the core stability evidence contract, and finally project that evidence through the unchanged confirmation transaction and GUI.

**Tech Stack:** Python 3.12, NumPy, SciPy, PySide6, dataclasses, pytest, repository verification scripts.

---

## File map

- `polynexus/core/saxs_action_registry.py`: causal action-to-symptom ownership.
- `polynexus/core/saxs_symptom_detector.py`: structural condition-axis logic.
- `polynexus/orchestrator_state.py`: action-compatible candidate target binding.
- `polynexus/core/saxs_engine/config.py`: typed header-relative geometry offsets.
- `polynexus/core/saxs_engine/io.py`: apply offsets after header geometry.
- `polynexus/core/saxs_config_binding.py`: typed panel/application conversion
  for offset and tuple-valued perturbations.
- `polynexus/orchestrator_stability.py`: active mode/domains and SAXS metrics.
- `polynexus/core/preprocess_optimization/stability.py`: continuity, platform,
  excluded dimensions, and perturbation intervals.
- `polynexus/orchestrator_session.py`: real mode and non-applicable
  `keep_original` confirmation projection.
- `polynexus/gui/preprocess_decision_service.py`: SAXS stability evidence rows.
- `polynexus/gui/main_window_config_panel_mixin.py`: apply-capable controls for
  stability-selected geometry and mask settings.
- `tests/test_saxs_symptom_detector.py`: condition-axis regressions.
- `tests/test_saxs_action_registry.py`: causal registry regression.
- `tests/test_saxs_orchestrator_loop.py`: action target binding regression.
- `tests/test_saxs_stability_map.py`: mode/domain/continuity/platform regressions.
- `tests/test_saxs_scientific_correctness_repair.py`: geometry-offset regression.
- `tests/test_saxs_ai_confirmed_rerun_safety.py`: confirmation mode and
  keep-original safety regressions.
- `tests/test_preprocess_decision_service.py`: GUI evidence projection.

### Task 1: Repair condition-axis ownership and candidate symptom binding

**Files:**
- Modify: `polynexus/core/saxs_action_registry.py:59-77`
- Modify: `polynexus/core/saxs_symptom_detector.py:331-378`
- Modify: `polynexus/orchestrator_state.py:259-448`
- Test: `tests/test_saxs_action_registry.py`
- Test: `tests/test_saxs_symptom_detector.py`
- Test: `tests/test_saxs_orchestrator_loop.py`

- [ ] **Step 1: Write the failing complete-axis symptom regression**

Add:

```python
def test_complete_filename_axis_is_not_unstable_from_source_confidence_alone() -> None:
    symptoms = detect_saxs_symptoms(
        output_parameters={
            "batch_frames": 5,
            "condition_label": "Strain",
            "condition_missing_frames": 0,
            "condition_continuity_score": 1.0,
            "_batch_data": [
                {"strain_pct": value, "condition_value": value}
                for value in (0.0, 5.0, 60.0, 200.0, 400.0)
            ],
        },
        residual_pattern={"residual_type": "noise"},
        condition_evidence={
            "condition_label": "Strain",
            "condition_missing_frames": 0,
            "condition_confidence": 0.64,
            "condition_continuity_score": 1.0,
        },
    )
    assert "condition_axis_unstable" not in {item["name"] for item in symptoms}
```

- [ ] **Step 2: Write the failing causal action regression**

Change the existing condition recovery test to require:

```python
names = {item["name"] for item in actions}
assert "rerun_condition_recovery" in names
assert "adjust_q_crop" not in names
```

- [ ] **Step 3: Write the failing per-action target regression**

Build a SAXS orchestrator state with lead symptom
`condition_axis_unstable`, include `adjust_corr_window` for
`thickness_chain_unreliable`, call `_expand_technique_candidates()`, and assert:

```python
q_plans = [row for row in plans if row["action_name"] == "adjust_corr_window"]
assert q_plans
assert {row["target_symptom"] for row in q_plans} == {"thickness_chain_unreliable"}
```

- [ ] **Step 4: Run RED tests**

Run:

```powershell
python -m pytest -q tests/test_saxs_symptom_detector.py::test_complete_filename_axis_is_not_unstable_from_source_confidence_alone tests/test_saxs_action_registry.py::test_saxs_action_registry_matches_condition_recovery_actions tests/test_saxs_orchestrator_loop.py::test_saxs_candidate_plan_binds_action_compatible_symptom
```

Expected: all three fail for the currently observed reasons.

- [ ] **Step 5: Implement structural axis stability**

In `detect_saxs_symptoms()`, replace confidence-only instability with:

```python
axis_has_gaps = missing_frames > 0
axis_is_discontinuous = continuity is not None and continuity < 0.85
axis_confidence_unresolved = condition_confidence is not None and condition_confidence <= 0.0
condition_axis_unstable = has_series_axis and (
    axis_has_gaps or axis_is_discontinuous or axis_confidence_unresolved
)
```

Keep the confidence value in evidence; do not rewrite the recovered provenance.

- [ ] **Step 6: Implement causal registry ownership**

Remove `condition_axis_unstable` from `adjust_q_crop.target_symptoms`. Retain it
for `rerun_condition_recovery`; retain `mark_frame_outlier` only when separate
frame-local discontinuity evidence requests that action.

- [ ] **Step 7: Implement action-compatible target selection**

Add a private helper in `orchestrator_state.py`:

```python
def _target_for_action(
    lead: str,
    symptom_names: list[str],
    action_spec: dict[str, Any],
) -> str:
    supported = {
        str(item or "").strip()
        for item in action_spec.get("target_symptoms", [])
        if str(item or "").strip()
    }
    if lead in supported:
        return lead
    return next((name for name in symptom_names if name in supported), "")
```

Pass its result to `_candidate_plans_for_action()` instead of the global lead.

- [ ] **Step 8: Run GREEN tests and focused neighbors**

Run:

```powershell
python -m pytest -q tests/test_saxs_symptom_detector.py tests/test_saxs_action_registry.py tests/test_saxs_orchestrator_loop.py
```

Expected: pass.

### Task 2: Propagate the actual SAXS mode through stability and confirmation

**Files:**
- Modify: `polynexus/orchestrator_stability.py:96-159`
- Modify: `polynexus/orchestrator_session.py:682-728`
- Test: `tests/test_saxs_stability_map.py`
- Test: `tests/test_saxs_ai_confirmed_rerun_safety.py`

- [ ] **Step 1: Write failing mode regressions**

Parameterize `experiment_type` as `temperature` and `strain`, run a minimal
stability bridge with `assess_saxs_confirmed_rerun` monkeypatched to record its
mode, then assert:

```python
assert observed_modes == [experiment_type] * len(observed_modes)
assert observed_modes
```

Add a confirmation projection regression:

```python
report = {"submodule": "saxs.strain"}
_attach_stability_confirmation_contract(report, stability, mode="strain")
assert report["mode"] == "strain"
```

- [ ] **Step 2: Run RED tests**

Run the two new test node IDs. Expected: both report `static`.

- [ ] **Step 3: Implement strict mode normalization**

Add in `orchestrator_stability.py`:

```python
def _saxs_stability_mode(self: Any, config: Any) -> str:
    raw = str(getattr(config, "experiment_type", "") or self._public_submodule()).lower()
    if "strain" in raw:
        return "strain"
    if any(token in raw for token in ("temperature", "heating", "cooling", "isothermal")):
        return "temperature"
    if raw in {"static", "saxs.static"}:
        return "static"
    raise ValueError(f"unsupported_saxs_stability_mode:{raw or 'missing'}")
```

Resolve once before trial evaluation, pass it to
`assess_saxs_confirmed_rerun()`, and store it in the stability report.

- [ ] **Step 4: Project that mode through confirmation**

Extend `_attach_stability_confirmation_contract()` with an optional `mode`
argument, use `stability["mode"]` when present, and remove the hard-coded
`"static"` value.

- [ ] **Step 5: Run GREEN tests**

Run:

```powershell
python -m pytest -q tests/test_saxs_stability_map.py tests/test_saxs_ai_confirmed_rerun_safety.py
```

Expected: pass.

### Task 3: Exclude inactive perturbations and make geometry perturbations effective

**Files:**
- Modify: `polynexus/core/saxs_engine/config.py:180-235`
- Modify: `polynexus/core/saxs_engine/io.py:321-397`
- Modify: `polynexus/orchestrator_stability.py:12-51`
- Test: `tests/test_saxs_stability_map.py`
- Test: `tests/test_saxs_scientific_correctness_repair.py`
- Test: `tests/test_saxs_config_binding.py`
- Test: `tests/test_main_window_ai_tuning_mixin.py`

- [ ] **Step 1: Write failing active-domain tests**

Add tests that assert:

```python
by_name = {domain.name: domain for domain in _saxs_stability_domains(config, mode="strain")}
assert "bg_scale_value" not in by_name  # transmission mode
assert "beam_center_offset_x_px" in by_name
assert "beam_center_offset_y_px" in by_name
assert all(isinstance(value, tuple) for value in by_name["orientation_mask_dilation_px"].values)
```

Add a second test with manual background and a real background path and assert
`bg_scale_value` is present. Add a static 1D case and assert detector/orientation
dimensions are absent with explicit exclusion reasons.

- [ ] **Step 2: Write the failing header-relative geometry test**

Construct a config with `beam_center_offset_x_px=2.0` and
`beam_center_offset_y_px=-1.0`, call `extract_geometry_from_header()` with
header centers 100/200, and assert returned centers are 102/199.

- [ ] **Step 3: Run RED tests**

Run the new domain and geometry nodes. Expected: missing offset fields,
unconditional background domain, and scalar mask categories fail.

- [ ] **Step 4: Add typed offset fields**

Add to `SAXSConfig`:

```python
beam_center_offset_x_px: float = 0.0
beam_center_offset_y_px: float = 0.0
```

After resolving header/config centers in `extract_geometry_from_header()`, add
the finite offsets to the copied config. Keep `beam_center_x/y` as the effective
centers consumed by integration.

- [ ] **Step 5: Build an activity-aware domain result**

Introduce:

```python
@dataclass(frozen=True)
class SAXSStabilityDomains:
    domains: tuple[ParameterDomain, ...]
    excluded: dict[str, str]
```

Use absolute `[-2, 2]` pixel domains around the offset baseline. Include manual
background scale only when `bg_scale_method == "manual"` and
`background_file` is non-empty. Encode dilation categories as `((1,), (2,))`
so each candidate preserves the tuple contract. Exclude detector/orientation
dimensions when no detector/sector input is present.

- [ ] **Step 6: Enforce coupled windows before trial execution**

Add:

```python
def _valid_saxs_windows(config: dict[str, Any]) -> bool:
    return all(
        float(config[low]) < float(config[high])
        for low, high in (
            ("q_min", "q_max"),
            ("q_corr_min", "q_corr_max"),
            ("q_porod_min", "q_porod_max"),
        )
        if low in config and high in config
    )
```

Return a failed trial with `invalid_coupled_q_window` before creating an engine.

- [ ] **Step 7: Run GREEN tests**

Before the GREEN run, expose `beam_center_offset_x_px`,
`beam_center_offset_y_px`, and the mask-dilation radii in the SAXS calibration/
mask schemas. Add an explicit tuple converter in `saxs_config_binding.py`:

```python
def _as_positive_int_tuple(value: Any) -> tuple[int, ...]:
    raw = value if isinstance(value, (list, tuple)) else str(value).split(",")
    converted = tuple(sorted({int(item) for item in raw if int(item) > 0}))
    if not converted:
        raise ValueError("at least one positive dilation radius is required")
    return converted
```

Bind `orientation_mask_dilation_px` through this converter. Add GUI/binding
tests proving that `_apply_best_config()` followed by `_build_run_config()`
preserves the selected offsets and tuple exactly; this prevents a stability
candidate from passing the hash check while being silently ignored by the
rerun configuration.

Run:

```powershell
python -m pytest -q tests/test_saxs_stability_map.py tests/test_saxs_scientific_correctness_repair.py tests/test_saxs_config_binding.py tests/test_main_window_ai_tuning_mixin.py
```

Expected: pass.

### Task 4: Replace magnitude continuity with robust sequence jump evidence

**Files:**
- Modify: `polynexus/core/preprocess_optimization/stability.py:118-329`
- Test: `tests/test_saxs_stability_map.py`

- [ ] **Step 1: Write failing continuity tests**

Add:

```python
def test_large_smooth_strain_response_is_continuous() -> None:
    evidence = _continuity_for_sequence([10.0, 12.0, 15.0, 19.0, 24.0])
    assert evidence.status == "passed"

def test_isolated_sequence_jump_fails_continuity() -> None:
    evidence = _continuity_for_sequence([10.0, 11.0, 30.0, 31.0, 32.0])
    assert evidence.status == "failed"

def test_short_sequence_continuity_is_insufficient() -> None:
    evidence = _continuity_for_sequence([10.0, 12.0])
    assert evidence.status == "insufficient"
```

- [ ] **Step 2: Run RED tests**

Expected: the smooth sequence fails the current 5% rule and short evidence is
incorrectly treated as passed.

- [ ] **Step 3: Extend continuity status without losing `passed` compatibility**

Add `status: str` to `ContinuityEvidence`, retain `passed` as
`status == "passed"`, and serialize both. Implement a private robust detector:

```python
diff = np.diff(array)
center = float(np.median(diff))
mad = float(np.median(np.abs(diff - center)))
scale = max(1.4826 * mad, 0.05 * max(float(np.median(np.abs(diff))), 1e-12))
outlier = np.abs(diff - center) > 6.0 * scale
```

Require at least four finite frames for a definitive robust decision. Record
`continuity_jump:<metric>` only for isolated outlying increments.

- [ ] **Step 4: Calculate study continuity from plateau trials**

Move the study-level `_continuity_for_trials()` call after plateau membership is
known and evaluate `plateau_trials`. Do not allow rejected trials to poison the
selected platform. Treat `insufficient` as non-passing for automatic scientific
acceptance while preserving its distinct reason.

- [ ] **Step 5: Run GREEN tests and stability suite**

Run:

```powershell
python -m pytest -q tests/test_saxs_stability_map.py
```

Expected: pass.

### Task 5: Add strain orientation evidence and strengthen platform semantics

**Files:**
- Modify: `polynexus/orchestrator_stability.py:54-93`
- Modify: `polynexus/core/preprocess_optimization/stability.py:147-499`
- Test: `tests/test_saxs_stability_map.py`

- [ ] **Step 1: Write failing orientation extraction tests**

Create strain points with `f_herman`, `f_herman_raw`, and nested
`orientation_fit_evidence` containing axis/strength/significance values. Assert:

```python
values = _frame_values(engine, {})
assert values["f_herman"] == [0.10, 0.35, 0.60]
assert values["f_herman_raw"] == [0.12, 0.37, 0.62]
assert values["orientation_axis_deg"] == [2.0, 3.0, 4.0]
assert values["orientation_strength"] == [0.2, 0.4, 0.7]
```

Add a missing tensile-axis case and assert effective Herman is absent while raw
Herman and `orientation_tensile_axis_missing` remain diagnostic.

- [ ] **Step 2: Write failing platform spread regression**

Construct a two-dimensional request where all eligible trials vary only
`q_min`; assert `plateau.connected is False` and reason
`stable_plateau_dimension_spread_insufficient` is present.

- [ ] **Step 3: Run RED tests**

Expected: orientation keys are absent and the one-dimensional line is accepted
as a multi-dimensional platform.

- [ ] **Step 4: Extract orientation metrics with wrapped axes**

Extend `_frame_values()` with the four orientation series. Preserve only finite
values and calculate axis differences with 180-degree periodic wrapping in the
continuity consumer. Never synthesize effective Herman from raw Herman.

- [ ] **Step 5: Require evidence for active orientation dimensions**

Add `required_metrics` to `ParameterDomain`. For `chi_halfwidth` and mask
dilation, require at least one of `f_herman_raw`, `orientation_axis_deg`, or
`orientation_strength`. A trial missing every required metric is ineligible and
receives `active_dimension_evidence_missing:<name>`.

- [ ] **Step 6: Tighten platform connectivity and spread**

Reduce the default normalized neighbor radius to a dimension-aware value:

```python
radius = min(request.neighbor_radius, 0.35 + 0.05 / math.sqrt(len(request.domains)))
```

For multi-dimensional numeric studies require nonzero normalized spread in at
least two active dimensions. Store `active_dimensions` and
`spread_dimensions` in `PlateauSummary`.

- [ ] **Step 7: Rename the report interval contract**

Serialize trial-resampling output under `perturbation_intervals`. Keep a
read-only `bootstrap` compatibility alias for existing persisted reports, and
add `interval_semantics="parameter_perturbation"`.

- [ ] **Step 8: Run GREEN tests**

Run:

```powershell
python -m pytest -q tests/test_saxs_stability_map.py tests/test_saxs_strain_method_evidence.py tests/test_saxs_orientation_reliability.py
```

Expected: pass.

### Task 6: Make keep-original non-applicable and display SAXS evidence

**Files:**
- Modify: `polynexus/orchestrator_session.py:682-728`
- Modify: `polynexus/gui/preprocess_decision_service.py:19-98`
- Test: `tests/test_saxs_ai_confirmed_rerun_safety.py`
- Test: `tests/test_preprocess_decision_service.py`
- Test: `tests/test_preprocess_decision_dialog.py`

- [ ] **Step 1: Write failing keep-original safety test**

Project a stability report with a changed diagnostic selected config and
`decision="keep_original"`, then assert:

```python
assert report["selected_preprocess_config"] == {}
assert report["preprocess_candidates"] == []
assert report["preprocess_decision"]["decision"] == "keep_original"
```

- [ ] **Step 2: Write failing SAXS GUI evidence test**

Build a report with `stability_report` and assert:

```python
view = build_preprocess_ui_decision(report)
assert view.evidence_kind == "saxs_stability"
assert view.metric_rows["platform_points"] == 4
assert view.metric_rows["continuity_status"] == "passed"
assert "protected metrics available: 0" not in view.summary
```

- [ ] **Step 3: Run RED tests**

Expected: keep-original still exposes a selected subset and the view has only
generic preprocessing metrics.

- [ ] **Step 4: Fail closed at confirmation projection**

In `_attach_stability_confirmation_contract()`, expose candidate identity and
selected config only for `request_confirmation` or `auto_accept` with all hard
guards true. Preserve the diagnostic trial solely inside `stability_report`.

- [ ] **Step 5: Add SAXS-specific view projection**

Extend `PreprocessUIDecision` with `evidence_kind`. When `stability_report` is a
mapping, project platform point count/coverage, active/excluded dimensions,
continuity status/frame count, physical/quality gates, and orientation coverage
into `metric_rows`. Build the summary from those fields and decision reason
codes instead of the generic protected-metric count.

- [ ] **Step 6: Run GREEN tests and transaction regressions**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest -q tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_preprocess_decision_service.py tests/test_preprocess_decision_dialog.py tests/test_preprocess_transaction_service.py tests/test_main_window_ai_tuning_mixin.py
```

Expected: pass.

### Task 7: Verify the cumulative scientific slice and checkpoint it

**Files:**
- Modify: `docs/agent/tasks/2026-08-07-saxs-ai-stability-decision-repair.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run the cumulative focused matrix**

Run the exact focused command from the task card. Expected: pass with zero
failures.

- [ ] **Step 2: Run structured verification**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-07-saxs-ai-stability-decision-repair.md --changed --types
```

Expected: selected checks pass, including quality and preprocessing gates.

- [ ] **Step 3: Review the cumulative diff**

Run:

```powershell
git diff --check
git diff --stat HEAD~1..HEAD
git status --short --branch
```

Inspect all task-scoped production, test, and documentation changes. Preserve
unrelated workspace changes.

- [ ] **Step 4: Request independent code review**

Provide the reviewer the design, this plan, base SHA `2d4092ab`, current HEAD,
and cumulative diff. Repair every Critical and Important finding with a fresh
RED/GREEN regression before proceeding.

- [ ] **Step 5: Update durable evidence**

Record exact test counts, commands, known scientific limits, and review outcome
in the task card and memory. Do not claim Bayesian optimization or unattended
SAXS acceptance.

- [ ] **Step 6: Create the explicit-allowlist checkpoint**

Run `scripts/auto_commit.py` with only files changed by this task and message:

```text
fix(saxs): repair AI stability decision chain
```

Do not push, merge, deploy, or delete branches.
