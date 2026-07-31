# Results Evidence Wrap Readability Acceptance

## Scope

This record covers only the shared Results evidence-label layout regression.

## Evidence

- Root cause: direct `QSizePolicy.Ignored/Preferred` reset QLabel's
  `heightForWidth` flag even though the rendered text retained zero-width
  break opportunities.
- Production fix: `WrappedEvidenceLabel.setSizePolicy()` preserves the caller's
  policy values and restores `heightForWidth=True`.
- TDD RED was `1 failed`; focused GREEN and the Results/Workbench matrix were
  `52 passed in 2.72s`.
- Ruff and compile passed. Structured verifier passed with quality `297` and
  preprocessing `106`, task/memory, type-baseline, and whitespace checks.
- Native Windows NMR route recheck returned `2 passed, 15 deselected in
  71.69s`, exit code `0`, with captures under
  `D:\PolyNexus_native_restarted_gui_audit_wrap_recheck_20260731`.
- The MainWindow geometry probe reported a constrained evidence-label width of
  `1248 px`, `heightForWidth=True`, and no workspace horizontal overflow.

## Acceptance checklist

- [x] Long evidence text wraps at constrained width.
- [x] `text()` preserves the original source string.
- [x] Focused regression passes.
- [x] Results/Workbench regression tests pass.
- [x] Structured verifier and diff boundary pass.
- [x] Checkpoint uses the explicit allowlist in the task card and plan.

## Remaining release limitations

IR mapping remains diagnostic-only without vendor-native mapping project data;
NMR solid-C remains assignment-limited with uncalibrated/default axis evidence;
Joint remains blocked pending scientific reviewer conflict interpretation; the
overall release disposition remains conditional pending owner approval.
