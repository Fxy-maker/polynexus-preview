# Scientific Review Promotion Gates: IR Mapping, NMR Solid-C, and Joint

## Goal

Carry the approved reviewer-owned scientific confirmation contract through the
three remaining promotion boundaries without changing numeric analysis:

- IR mapping consumes coordinates and explicit ROIs as supplied, keeps invalid
  pixels masked, and promotes map/ROI figures only after accepted source-matched
  `ir.mapping` review.
- NMR solid-C keeps all figures diagnostic until an accepted source-matched
  `nmr.solid_c` assignment/Xc review; after acceptance only the spectrum is
  Main, supporting figures are SI, and deconvolution remains diagnostic.
- Joint keeps source values and conflicts intact, and promotes its crystallinity
  Main and multiscale SI figures only after every selected batch row has an
  accepted source-matched `joint` review.

## Non-goals

- No vendor reader, coordinate inference, interpolation, peak reassignment,
  formula/threshold change, conflict overwrite, GUI-only scientific branch, or
  final release approval.
- No deletion, migration, push, merge, deployment, or modification of real
  regression datasets.

## Affected boundaries

- Shared review record restoration and JSON-safe decision snapshots.
- IR mapping `AnalysisResult` evidence/metadata and FigureDefinition recipes.
- NMR solid-C result metadata, evidence, and FigureDefinition roles.
- Joint batch-row review input, report, FigureDefinition roles, and recipes.
- Focused provider/lifecycle/provenance regressions and durable acceptance notes.

## Acceptance criteria

- [x] Missing, malformed, non-finite, conditional/rejected/stale, or
   source-mismatched records fail closed and remain diagnostic.
- [x] Accepted records require the correct scope, source reference, reviewer,
   timestamp, policy version, and required scope-specific decisions.
- [x] Promotion decisions are identical in evidence and figure recipes and are
   JSON-safe; raw values, coordinates, masks, and source-run provenance remain
   unchanged.
- [x] IR mapping accepted fixtures promote `map=Main`, `ROI=SI`, invalid-pixels
   diagnostic; NMR solid-C accepted fixtures promote only the spectrum to Main;
   Joint accepted fixtures promote crystallinity Main and multiscale SI.
- [x] Real NMR solid-C lifecycle confirms the absence of a reviewer record keeps
   the published run diagnostic-only; liquid/solid-H lifecycle behavior stays
   green.
- [x] No claim is made that final scientific release approval is complete: the
   actual reviewer records and all-mode visual/restarted-GUI/AI-fallback gates
   remain follow-up work.

## Verification commands

```powershell
python -m pytest -q tests/test_scientific_review.py tests/test_ir_mapping.py tests/test_ir_figure_provider.py tests/test_ir_lifecycle_closure.py tests/test_nmr_figure_provider.py tests/test_nmr_joint_provenance_matrix.py tests/test_joint_figure_provider.py tests/test_joint_lifecycle_closure.py
python -m pytest -q tests/test_nmr_lifecycle_closure.py -k solid_c -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-29-scientific-review-promotion-gates.md --changed --types
python scripts/verify.py --changed --types --full --boundary
```

Report exact exit codes and summaries. The full/boundary command must not be
called passed if it times out without a pytest summary.

## Explicit checkpoint allowlist

- `polynexus/core/__init__.py`
- `polynexus/core/scientific_review.py`
- `polynexus/core/ir.py`
- `polynexus/core/ir_engine/ir_mapping.py`
- `polynexus/core/nmr.py`
- `polynexus/core/nmr_engine/figure_provider.py`
- `polynexus/core/joint/dataset.py`
- `polynexus/core/joint/figure_provider.py`
- `tests/test_scientific_review.py`
- `tests/test_ir_mapping.py`
- `tests/test_ir_lifecycle_closure.py`
- `tests/test_nmr_figure_provider.py`
- `tests/test_nmr_lifecycle_closure.py`
- `tests/test_nmr_joint_provenance_matrix.py`
- `tests/test_joint_figure_provider.py`
- `tests/test_joint_lifecycle_closure.py`
- `docs/agent/memory/active-work.md`
- `docs/agent/tasks/2026-07-29-ir-mapping-scientific-review-gate.md`
- `docs/superpowers/plans/2026-07-29-ir-mapping-scientific-review-gate.md`
- `docs/agent/tasks/2026-07-29-scientific-review-promotion-gates.md`
- `docs/superpowers/plans/2026-07-29-scientific-review-promotion-gates.md`
- `docs/acceptance/2026-07-29-scientific-review-promotion-gates.md`

## Pre-existing workspace changes

Keep `docs/agent/memory/current-state.md`, `docs/agent/memory/active-work.md`,
running GUI processes, historical pytest/storage directories, `.superpowers/`,
and all unrelated user/parallel-agent changes outside this checkpoint.

## Implementation plan

1. Extend the shared review contract with payload restoration, JSON-safe
   decision snapshots, and fail-closed non-finite validation.
2. Gate IR mapping roles and persist the decision in mapping evidence, recipes,
   and `AnalysisResult` metadata without modifying map arrays or masks.
3. Gate NMR solid-C roles and evidence while preserving liquid/solid-H behavior;
   verify accepted synthetic and unreviewed real solid-C paths.
4. Gate Joint roles for every selected batch row and persist the aggregate
   decision in hub reports and all FigureDefinition recipes.
5. Run focused tests, the real solid-C lifecycle, task-scoped verification,
   hygiene/boundary checks, and create an explicit allowlist checkpoint.

## Verification

Run the commands in the preceding section. The required structured gate is:

    python scripts/verify.py --task docs/agent/tasks/2026-07-29-scientific-review-promotion-gates.md --changed --types

Do not call full/boundary verification passed if it times out without a pytest
summary.

## Verification evidence

- Focused IR/shared/NMR/Joint matrix: `46 passed in 30.47s`, exit 0.
- Real NMR solid-C lifecycle: `1 passed, 3 deselected in 116.02s`, exit 0;
  `review_missing` and diagnostic-only roles were asserted.
- Task-scoped verifier: task/memory checks, Ruff, compile, quality `287
  passed`, preprocessing `106 passed`, whitespace all passed, exit 0.
- Boundary-only verifier: same checks plus boundary audit passed, exit 0.
- Full/boundary verifier: exit 124 after 364028 ms with no complete pytest
  summary; classified as timeout, not pass.

## Completion state

The implementation and bounded verification are complete. The task does not
authorize or claim human scientific release approval; the open gates are listed
in `docs/acceptance/2026-07-29-scientific-review-promotion-gates.md`.
