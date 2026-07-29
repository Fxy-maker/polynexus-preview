# Scientific Review Promotion Gates Acceptance

Date: 2026-07-29
Task: `docs/agent/tasks/2026-07-29-scientific-review-promotion-gates.md`
Status: implementation verified; human scientific release approval remains open

## What changed

- The shared scientific-review module now restores serialized immutable review
  records and emits one JSON-safe promotion snapshot. Missing, invalid,
  non-finite, non-accepted, scope-mismatched, and source-mismatched records
  fail closed.
- IR mapping keeps supplied coordinates, ROI spectra, and invalid-pixel masks
  unchanged. Without an accepted matching `ir.mapping` record, map and ROI
  figures are diagnostic; with one, the map is Main and ROI spectra are SI.
  Invalid-pixel diagnostics are always diagnostic. The same snapshot is in
  evidence, figure recipes, and `AnalysisResult.metadata`.
- NMR solid-C carries source identity and optional review provenance through
  analysis evidence and FigureDefinitions. An unreviewed real solid-C run is
  diagnostic-only; an accepted matching record promotes only the spectrum to
  Main, supporting figures to SI, and leaves deconvolution diagnostic.
  Liquid/solid-H behavior is unchanged.
- Joint rows accept an explicit review payload, require accepted source-matched
  records for every selected batch, and persist the aggregate decision in the
  hub report and every figure recipe. Source values, conflicts, and run
  provenance are not overwritten.

## Verification evidence

- Focused IR/shared/NMR/Joint matrix:
  `python -m pytest -q tests/test_scientific_review.py tests/test_ir_mapping.py tests/test_ir_figure_provider.py tests/test_ir_lifecycle_closure.py tests/test_nmr_figure_provider.py tests/test_nmr_joint_provenance_matrix.py tests/test_joint_figure_provider.py tests/test_joint_lifecycle_closure.py`
  → `46 passed in 30.47s`, exit code 0.
- Real NMR solid-C lifecycle:
  `python -m pytest -q tests/test_nmr_lifecycle_closure.py -k solid_c -vv`
  → `1 passed, 3 deselected in 116.02s`, exit code 0. The test asserts the
  persisted decision reason is `review_missing` and no Gallery entry is Main.
- Task-scoped verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-29-scientific-review-promotion-gates.md --changed --types`
  → task/memory checks passed; Ruff and compile passed; quality gate
  `287 passed`; preprocessing gate `106 passed`; whitespace passed; exit 0.
- Boundary-only verifier:
  `python scripts/verify.py --changed --types --boundary`
  → task/memory checks, Ruff, compile, quality `287 passed`, preprocessing
  `106 passed`, whitespace, and boundary audit passed; exit 0.
- Full/boundary verifier:
  `python scripts/verify.py --changed --types --full --boundary`
  → tool timeout after `364028 ms`, exit 124, with no complete pytest summary.
  This is recorded as a verification limitation, not a pass.

## Files in the atomic checkpoint

The checkpoint is limited to the explicit allowlist in the task card, including
the shared review/core changes, focused regressions, this task/plan/acceptance,
and the active-work memory entry. Current-state, GUI processes, test-storage
directories, `.superpowers/`, real datasets, and unrelated parallel changes
remain untouched.

## Open release gates

- Real reviewer-owned records for IR coordinate/ROI semantics, NMR solid-C
  assignment/Xc policy, Joint conflict precedence, and final release approval
  have not been supplied; no production promotion is claimed.
- All-mode real/Golden visual review, restarted-GUI walkthroughs, and complete
  AI-off/failure/fallback acceptance remain open.
- Full repository verification needs a bounded rerun or a separately captured
  complete pytest summary; the timeout above cannot certify it.
