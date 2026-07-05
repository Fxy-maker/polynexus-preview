# SAXS `lc` Physical Constraints Implementation Checklist

## Purpose

This checklist translates the planning document into a minimal, low-risk implementation path.

Reference:

- [saxs_lc_physical_constraints_plan.md](D:/PolyNexus/docs/saxs_lc_physical_constraints_plan.md)

## Implementation Boundary

First implementation covers:

- SAXS temperature-series pipeline only
- deterministic physical status fields only
- no AI override of core physical status
- minimal GUI exposure for status and reasons
- targeted tests before broader UI polish

Not included in v1:

- strain pipeline refactor
- static single-frame behavior redesign
- polymer-specific hard-coded threshold packs
- full extraction-algorithm rewrite

## Deliverable 1: Deterministic Status Fields

### Target files

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs.py`

### Tasks

- Add sequence-level melting-window classification output.
- Add frame-level `lc` reliability classification output.
- Add frame-level downgrade reason field.
- Preserve existing raw values and raw snapshots.
- Do not silently rewrite raw `lc` into another value.

### Suggested fields

- `melting_window_status`
- `melting_window_reason`
- `lc_reliability_status`
- `lc_reliability_reason`

### Suggested enums

- `melting_window_status`
  - `outside_window`
  - `near_onset`
  - `within_window`
  - `post_end`
  - `undetermined`

- `lc_reliability_status`
  - `usable`
  - `low_confidence`
  - `diagnostic_only`

## Deliverable 2: Melting-Window Coupling

### Target files

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs.py`

### Tasks

- Convert sequence `Tm_onset`, `Tm_peak`, `Tm_end` into frame-level window labels.
- Use current-sequence evidence as the primary basis.
- Keep `T_melt_expected` as an optional soft hint only.
- Ensure "near melting window" and "`lc` unreliable" are independent judgments.

### Rules to implement

- If `Tm_onset` and `Tm_end` are both valid:
  - frames below onset -> `outside_window`
  - onset-adjacent frames -> `near_onset`
  - between onset and end -> `within_window`
  - above end -> `post_end`
- If melting evidence is weak or unavailable:
  - use `undetermined`
  - do not force a melting interpretation from temperature alone
- Prefer sustained Bragg-peak loss over single-frame dips when deriving `Tm_onset` / `Tm_peak`.

## Deliverable 3: `lc` Downgrade Logic

### Target files

- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs.py`

### Tasks

- Define downgrade triggers from existing evidence.
- Map trigger combinations to `usable`, `low_confidence`, `diagnostic_only`.
- Keep reasons structured and stable for export and AI review.

### Initial trigger candidates

- single-method-only solution with implausibly thin thickness
- severe tangent / IDF / gamma-min disagreement
- minority phase fraction too small
- abnormal `Q_invariant`
- abrupt frame continuity break inside temperature sequence
- frame lies within melting window and structural evidence is weak
- pre-melting sequence collapse in `lc` / minority fraction even when the melting window is not proven yet

### Minimum reason keys

- `method_conflict`
- `minority_fraction_too_low`
- `q_invariant_anomaly`
- `sequence_continuity_break`
- `sequence_continuity_weakened`
- `sequence_crystallinity_drop`
- `sequence_crystallinity_softening`
- `peak_tracking_lost`
- `peak_tracking_weakened`
- `within_melting_window`
- `melting_window_undetermined`
- `single_method_fragile`

## Deliverable 4: Output Surface

### Target files

- `polynexus/core/saxs.py`
- `polynexus/gui/main_window.py`

### Tasks

- Include status and reason fields in batch export rows.
- Surface the new fields in result detail panels or summary text.
- Ensure users can distinguish raw numeric values from reliability state.
- Keep calibration status and reliability status separate.

### Must-show information

- current `lc` numeric value
- whether it is raw or calibrated
- whether it is usable / low-confidence / diagnostic-only
- why it was downgraded

## Deliverable 5: AI Review Linkage

### Target files

- `polynexus/core/analysis_evidence.py`
- `polynexus/gui/main_window.py`

### Tasks

- Feed new status fields into evidence and review summaries.
- Let AI explain:
  - near-melting evidence
  - extraction instability
  - next review steps
- Keep AI on the interpretation layer only.

### Required guardrail

- AI must not promote `diagnostic_only` to accepted physical truth.

## Deliverable 6: Tests

### Suggested test files

- `tests/test_saxs_temperature.py`
- `tests/test_saxs_batch_parameters.py`
- `tests/test_analysis_evidence.py`
- `tests/test_main_window_persistence.py`

### Test cases

- PA6-like high-temperature frame with weak structure -> downgraded from normal `lc`
- frame outside melting window but structurally unstable -> unreliable, not auto-melt
- frame within melting window -> melting-window status set correctly
- no reference crystallinity -> raw retained, no hidden calibration
- export rows include new status and reason fields
- GUI persistence and summary text preserve the new fields

## Recommended Execution Order

1. Add new deterministic fields in `saxs_temperature.py`.
2. Thread the fields through `saxs.py` batch rows and summaries.
3. Add `lc` downgrade logic in `core.py` and final row labeling in `saxs.py`.
4. Add tests for classification and export behavior.
5. Expose the fields in GUI summaries.
6. Hook the fields into AI/evidence review text.

## Definition of Done for V1

- Temperature-series SAXS results can label each frame with melting-window status and `lc` reliability status.
- PA6 high-temperature weak frames are no longer silently treated as normal valid `lc`.
- Results can explicitly say "not enough evidence for reliable `lc`" without claiming melting.
- No hidden crystallinity default is reintroduced.
- New behavior is covered by focused regression tests.
