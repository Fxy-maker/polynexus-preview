# SAXS AI Confirmation UI Acceptance Design

## Goal

Create repository evidence that a SAXS `request_confirmation` report is
presented by the real review dialog and, after the user activates its enabled
confirmation control, enters the existing guarded preprocessing transaction.

## Scope

The slice covers the GUI boundary only:

1. The existing `SideTuningReportDialog` renders a SAXS confirmation report
   with an enabled Apply control and exposes the selected configuration.
2. The existing `MainWindowAITuningMixin._on_ai_tune_finished` route consumes
   that dialog result and calls the SAXS confirmation transaction entry point.
3. The existing transaction service remains the authority for identity checks,
   rerun timing, physical/quality gates, persistence, and rollback.

No new decision, threshold, rescue action, interpolation, frame repair,
publication role, or GUI-specific scientific algorithm is introduced.

## Verification boundary

The regression uses an offscreen real `MainWindow` and the real
`SideTuningReportDialog`. The modal event loop is replaced only by a test
callback that clicks the dialog's actual enabled Apply button, so the test
does not replace the UI decision with a direct mixin call. The downstream
transaction start is observed at its existing public helper boundary; its
post-rerun gate and rollback behavior remain covered by the focused SAXS
transaction tests.

## Acceptance

- A SAXS confirmation report enables the real dialog Apply button.
- Activating that button through `_on_ai_tune_finished` starts exactly one
  pending SAXS transaction and invokes the existing apply/rerun callbacks.
- A rejected dialog does not start a transaction or apply configuration.
- No GUI test asserts scientific acceptance independently of the existing SAXS
  evidence and quality gates.
- The task records that restarted-GUI visual inspection and human scientific
  review remain open release gates.
