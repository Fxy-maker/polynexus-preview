# Cross-technique Results Workbench review hint

## Goal

Expose existing structured result review text in the customized Workbench for
DSC, WAXS, IR, NMR, and Joint, not only SAXS temperature/strain.

## Non-goals

- No scientific, evidence, severity, AI, publication, or Figure Pack changes.
- No hint for generic/legacy tables.

## Affected boundaries

- `polynexus/gui/main_window_output_mixin.py`
- `polynexus/gui/widgets/results_table_panel.py`
- focused MainWindow/ResultsTablePanel regressions

## Acceptance criteria

- [x] Non-SAXS structured profiles show existing summary/risk/next text in the
  Workbench review hint.
- [x] The profile's localized review action is used and remains re-translatable.
- [x] SAXS temperature/strain behavior and generic/unsupported clearing remain
  unchanged.
- [x] TDD RED is observed before production changes and GREEN is recorded after.
- [x] Task-scoped verifier, diff check, and explicit allowlist checkpoint pass.

## Verification result

- TDD RED: `2 failed, 19 passed`; the failures were the expected missing
  non-SAXS projection and shared action-key retranslation.
- TDD GREEN focused matrix: `68 passed` across MainWindow output, panel,
  results-table, and Workbench profile regressions.
- Task-scoped verifier passed: task/memory checks, Ruff, compile, quality
  `282`, preprocessing `106`, and whitespace checks all passed. The changed
  verifier scope also observed parallel SAXS evidence-binding files; those
  files are outside this task's allowlist and remain untouched.
- `git diff --check` passed as part of the verifier.
- Full/boundary verification is not claimed for this task.

## Checkpoint

The explicit allowlist checkpoint is created after the evidence above. Existing
scratch directories and parallel SAXS evidence-binding changes remain outside
the checkpoint.

## Implementation order

1. Add failing tests for non-SAXS projection and generic action retranslation.
2. Extend the panel's action-key recognition and MainWindow routing minimally.
3. Run focused/structured verification and checkpoint the explicit allowlist.

## Implementation plan

1. Write a DSC/Joint recorder regression that expects `set_review_hint()` with
   existing risk/next text and the profile review-action label.
2. Write a panel retranslation regression for the shared
   `RESULTS_WORKBENCH_REVIEW_ACTION` key.
3. Preserve the SAXS branch and allow any structured non-generic profile to use
   the profile title/action without deriving new scientific status.
4. Run the focused matrix, task verifier, diff check, and allowlist checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_workbench_review_hint'
python -m pytest tests/test_main_window_output_mixin.py tests/test_results_table_panel.py tests/test_results_table_service.py tests/test_results_workbench_profiles.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-results-workbench-cross-technique-review-hint.md --changed --types
git diff --check
```

## Known limitations

Real-data restarted-GUI visual review, scientific sign-off, and release policy
remain open in the full-software goal.

## Changed-file allowlist

- `polynexus/gui/main_window_output_mixin.py`
- `polynexus/gui/widgets/results_table_panel.py`
- `tests/test_main_window_output_mixin.py`
- `tests/test_results_table_panel.py`
- this task card
- the design spec and implementation plan created for this task
