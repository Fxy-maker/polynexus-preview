---
task_id: 2026-07-29-results-review-prefix-deduplication
kind: gui-quality
status: completed
---

# Results Review prefix deduplication

## Goal

Ensure the shared Results Review panel formats risk and next-step labels once
even when a persisted or technique-specific fallback already contains the
localized label prefix.

## Non-goals

- Do not change evidence text, risk severity, scientific interpretation, or
  publication roles.
- Do not modify technique-specific Results Review producers outside the shared
  panel boundary.
- Do not change Joint identity or conflict semantics.

## Affected boundaries

- `polynexus/gui/results_review_service.py`: shared panel text composition.
- `tests/test_results_review_service.py`: English/Chinese and window-fallback
  regressions.
- Durable task/spec/plan records only; no generated outputs or datasets.

## Acceptance criteria

- [x] Repeated English or Chinese risk prefixes are removed before shared
  formatting.
- [x] Repeated English or Chinese next-step prefixes are removed before shared
  formatting.
- [x] Unprefixed text and the evidence payload after the prefix are preserved.
- [x] Existing direct panel composition, window persistence, focused quality,
  and changed-file verification pass.

## Implementation plan

1. Add RED regressions for repeated English/Chinese prefixes and formatted
   window fallbacks.
2. Normalize only leading localized panel decoration in the shared Results
   Review service, then apply the existing formatter once.
3. Run the focused matrix and structured verifier, review the diff, update
   durable evidence, and create one explicit allowlist checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_results_review_service.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-results-review-prefix-deduplication.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/gui/results_review_service.py`
- `tests/test_results_review_service.py`
- `docs/agent/tasks/2026-07-29-results-review-prefix-deduplication.md`
- `docs/superpowers/specs/2026-07-29-results-review-prefix-deduplication-design.md`
- `docs/superpowers/plans/2026-07-29-results-review-prefix-deduplication.md`
- `docs/agent/memory/active-work.md`

## Verification evidence

- TDD RED: 3 expected failures for repeated direct/window prefixes.
- Focused GREEN: 6 passed; complete Results Review service: 28 passed;
  Results/MainWindow slice: 35 passed; persistence review subset: 67 passed.
- Structured verifier exited `0`: Ruff, compile, type baseline, quality `287`,
  preprocessing `106`, memory/task checks, and whitespace all passed.
- `git diff --check` passed.

## Checkpoint boundary

The existing uncommitted `docs/agent/memory/current-state.md` change belongs to
the earlier test-storage task and is intentionally excluded from this atomic
checkpoint.

## Known limitations

This is a display-boundary cleanup. It does not close the open restarted-GUI,
scientific review, or final release-approval gates.
