# Results Evidence Wrap Readability

## Goal

Keep long Results Workbench evidence text inside the available viewport by
preserving Qt height-for-width layout after the shared evidence label is made
 horizontally shrinkable.

## Non-goals

- Do not change evidence content, scientific interpretation, or release state.
- Do not change IR coordinates, NMR assignment readiness, Xc gating, or Joint
  conflict policy.
- Do not edit real datasets, generated native screenshots, or parallel SAXS
  work.

## Affected boundaries

- Production: `polynexus/gui/widgets/wrapped_evidence_label.py` and the
  Results Workbench label setup in `polynexus/gui/main_window_results_mixin.py`.
- Regression: one focused Qt test for the shared label's constrained-width
  behavior.
- Documentation: the linked design, plan, and acceptance record.

## Implementation plan

1. Add a focused Qt regression for the Results shrink policy and confirm the
   current behavior fails.
2. Preserve `heightForWidth` in `WrappedEvidenceLabel` while retaining the
   caller's horizontal and vertical size policies.
3. Run focused GUI tests, task verification, and diff checks.
4. Record exact outcomes and create a checkpoint with the explicit allowlist.

## Acceptance criteria

- [x] A long evidence string is visually wrap-capable under a constrained
      width.
- [x] `WrappedEvidenceLabel.text()` returns the exact source string.
- [x] The label keeps horizontal shrink behavior without losing
   `heightForWidth`.
- [x] Focused tests, task verification, diff checks, and the explicit
      checkpoint pass without including pre-existing or unrelated paths.

## Verification

```powershell
python -m pytest -q tests/test_wrapped_evidence_label.py
python scripts/verify.py --task docs/agent/tasks/2026-07-31-results-evidence-wrap-readability.md --changed --types
git diff --check
```

## Known limitation

The offscreen focused test passed and a native Windows route recheck passed for
both NMR solid-H and solid-C. The native capture was written outside the
repository to `D:\PolyNexus_native_restarted_gui_audit_wrap_recheck_20260731`.
The native screenshot still contains a deliberately long evidence sentence;
it wraps into continuation rows rather than changing the scientific text.
