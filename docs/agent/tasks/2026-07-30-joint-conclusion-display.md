---
task_id: 2026-07-30-joint-conclusion-display
kind: gui-scientific-provenance
status: completed
date: 2026-07-30
title: Show the fail-closed Joint conclusion in Results review
---

# Joint conclusion display

## Goal

Make the reviewer-owned Joint conclusion visible in the Results review panel
when the report already provides it, so a review-record status cannot be
mistaken for a Joint scientific conclusion.

## Non-goals

- Do not change Joint classification, formulas, thresholds, or severity.
- Do not merge `scientific_review` status with `joint_conclusion`.
- Do not choose technique conflict precedence or promote a result.
- Do not touch SAXS code, tests, real datasets, or test-storage directories.

## Affected boundaries

- `polynexus/gui/results_review_service.py`: format the existing JSON-safe
  `joint_conclusion` in the Joint panel text.
- `polynexus/gui/i18n.py`: add English and Chinese labels.
- `tests/test_results_review_service.py`: preserve the blocked-conclusion
  display contract.

## Implementation plan

1. Add a regression fixture containing the existing fail-closed Joint
   conclusion in the Results review context.
2. Format the conclusion beside the existing Joint summary and hints using
   localized labels.
3. Run the non-SAXS Joint/Results review matrix and the structured verifier.
4. Create one explicit changed-file allowlist checkpoint.

## Acceptance criteria

- [x] A context with `class=blocked`, `allowed=false`, and
  `reason=conflict_error` visibly includes all three values in Joint review
  text.
- [x] Existing Joint summary, reminder, and compare-hint text remains present.
- [x] Scientific review provenance remains separate from the displayed
  conclusion.
- [x] Focused Results review tests pass and the changed-file verifier is green.

## Known boundary

The panel only displays the conclusion already produced by the Joint core
report. It does not create assignments, resolve conflicts, or authorize
publication.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_joint_hub_dataset.py tests/test_joint_figure_provider.py tests/test_joint_lifecycle_closure.py tests/test_nmr_joint_provenance_matrix.py tests/test_results_review_service.py
python scripts/verify.py --task docs/agent/tasks/2026-07-30-joint-conclusion-display.md --changed --types
git diff --check
```

## Native route evidence

- Windows Qt Joint route: `1 passed, 16 deselected in 9.22s`, exit 0, with
  `QT_QPA_PLATFORM=windows`.
- Capture root:
  `D:\PolyNexus_native_joint_conclusion_display_20260730`.
- Results, Gallery, History, and Editor captures were generated; Editor
  package export fallback also passed.
- Visual inspection confirmed the Results review text exposes the blocked
  Joint conclusion while the separate scientific review record remains
  visible as provenance.

## Explicit changed-file allowlist

- `polynexus/gui/results_review_service.py`
- `polynexus/gui/i18n.py`
- `tests/test_results_review_service.py`
- this task card
- `docs/acceptance/2026-07-30-joint-conclusion-display.md`
