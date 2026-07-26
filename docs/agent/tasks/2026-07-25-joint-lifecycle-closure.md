---
task_id: 2026-07-25-joint-lifecycle-closure
kind: scientific-cross-module
status: completed
---

# Joint lifecycle closure

## Goal

Prove the Joint path from hub publication through Gallery, Editor revisions,
export provenance, and History restore using one stable figure run.

## Non-goals

- Do not change Joint comparison formulas, tolerances, or conflict severity.
- Do not promote diagnostic, low-confidence, or assignment-limited evidence.
- Do not infer scientific meaning for missing instrument provenance.
- Do not claim real-data, restarted-GUI, or human scientific release review.

## Affected boundaries

- `polynexus/core/joint/` publication contracts.
- Shared Figure Manifest/Gallery/Editor/export/history consumers.
- `tests/test_joint_lifecycle_closure.py` and acceptance/memory records.

## Implementation plan

1. Run the focused lifecycle regression against the existing Joint publisher,
   Gallery, Editor, export, and History contracts.
2. Run the Joint component/provenance matrix and the cross-technique AI safety
   matrix with an external pytest basetemp.
3. Run the task-scoped verifier, record exact outcomes, and create one
   allowlisted checkpoint commit.

## Acceptance criteria

- [x] Joint publishes crystallinity/main, multiscale/SI, and coverage/diagnostic
  entries under one run ID.
- [x] The main figure reaches working revision 2 and published revision 2.
- [x] Export retains `metadata/runs/<run_id>/` and the active-run pointer.
- [x] History restore rehydrates the Joint report, custom Workbench, and all
  three active Gallery entries.
- [x] The focused regression passes without changing production code.
- [x] Remaining release-only gates are recorded as open.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_joint_lifecycle'
python -m pytest tests/test_joint_lifecycle_closure.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-25-joint-lifecycle-closure.md --changed --types
```

## Known limitations

This is an automated contract closure. Real Joint inputs, restarted-GUI visual
inspection, AI-off/failure/fallback release evidence, and human scientific
sign-off remain cross-software release gates.
