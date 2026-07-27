---
task_id: 2026-07-28-joint-evidence-weighted-conflicts
kind: scientific-cross-module
status: completed
---

# Joint evidence-weighted conflict severity

## Goal

Ensure a Joint Tm/Gibson-Thompson conflict is surfaced as review evidence
instead of a hard error when one of its source runs is already diagnostic-only
or otherwise below the existing evidence-weight threshold.

## Non-goals

- Do not change the Tm/Gibson-Thompson formula, tolerance, or numeric values.
- Do not suppress conflicts or silently correct source results.
- Do not change the existing phi-c severity policy or Joint publication roles.
- Do not infer missing instrument provenance or scientific assignment meaning.

## Affected boundaries

- `polynexus/core/joint/validation.py`: carry source evidence weight into the
  existing Tm severity decision.
- `polynexus/core/joint/dataset.py`: pass the minimum DSC/SAXS evidence weight
  into the validation call.
- `tests/test_joint_hub_dataset.py`: regression for diagnostic-only SAXS Tm
  conflict severity and provenance details.

## Design

The existing phi-c path already uses the minimum participating evidence weight:
weights below `0.5` downgrade a numeric conflict from `ERROR` to `WARN` while
preserving `passed=False` and the original numeric details. Apply that same
policy to `Tm_GT` only. A fully evidenced conflict remains an `ERROR`; a
diagnostic-only or assignment-limited source remains a visible `WARN`.

## Implementation plan

1. Add a failing dataset regression for a diagnostic-only SAXS Tm conflict.
2. Add an optional evidence-weight argument to the existing Tm validator and
   pass the minimum DSC/SAXS weight from the Joint dataset boundary.
3. Run the focused Joint matrix, task verifier, and changed/type verifier.
4. Record the scientific review boundary and create an allowlisted checkpoint.

## Acceptance criteria

- [x] Low-evidence Tm conflicts remain visible with `passed=False` and severity
  `WARN`, including the effective evidence weight in details.
- [x] Fully evidenced Tm conflicts retain severity `ERROR`.
- [x] Existing Joint numeric values, phi-c behavior, provenance, and lifecycle
  tests remain green.
- [x] Task-scoped verification and diff checks pass.
- [ ] Human scientific review remains explicitly required before release.

## Verification

```powershell
python -m pytest -q tests/test_joint_hub_dataset.py tests/test_joint_figure_provider.py tests/test_joint_coordinator.py tests/test_joint_lifecycle_closure.py tests/test_nmr_joint_provenance_matrix.py
python scripts/verify.py --task docs/agent/tasks/2026-07-28-joint-evidence-weighted-conflicts.md --changed --types
```

Observed focused matrix: `23 passed in 13.11s`, exit code `0`. The task-scoped
verifier also exited `0` with quality `283` and preprocessing `106`.

## Known limitations

This task only propagates an existing evidence-weight policy. It does not
resolve the still-open IR/NMR calibration semantics, real Joint inputs,
restarted-GUI visual review, or final scientific release decision.
