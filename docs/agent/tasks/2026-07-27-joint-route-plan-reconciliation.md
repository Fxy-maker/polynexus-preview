# Joint Route Plan Reconciliation

Status: automated lifecycle route reconciled; scientific review remains open
Date: 2026-07-27

## Goal

Reconcile the full-software development plan with the current Joint
`joint.compare` implementation and evidence, without promoting unresolved
cross-technique scientific conflicts.

## Scope

- `polynexus/core/joint/coordinator.py`
- `polynexus/gui/main_window_workers.py`
- Joint Workbench, FigureDefinition, Manifest, export, and History evidence
- The Phase 7 route status in
  `docs/superpowers/plans/2026-07-25-full-software-development.md`

## Non-goals

- No new consistency tolerance, scientific threshold, or conflict resolution.
- No silent correction of DSC/WAXS/SAXS/IR/NMR disagreements.
- No real-data scientific approval, restarted-GUI visual approval, push,
  merge, or deployment.

## Affected boundaries

- JointCoordinator publication and JointHubWorker handoff to the shared
  FigureDefinition/Manifest lifecycle.
- Results Workbench profile, Gallery/Editor, export provenance, and History
  restore consumers.
- Route documentation and durable project memory only; production code is
  unchanged by this reconciliation.

## Acceptance criteria

- [x] `joint.compare` calls the shared coordinator publication entrypoint.
- [x] Joint FigureDefinition IDs and publication roles are covered by tests.
- [x] Manifest, Editor, export, History, and custom Workbench restoration are
  covered by the current lifecycle regression.
- [x] The full plan no longer claims this automated route is missing.
- [ ] Cross-technique scientific consistency/conflict semantics are reviewed by
  a domain expert.
- [ ] Real-data and restarted-GUI release review are complete.

## Implementation plan

1. Inspect the Joint coordinator, GUI worker, profile, and lifecycle tests.
2. Run the focused provider/coordinator/lifecycle/Workbench matrix using an
   external basetemp.
3. Update only the stale Phase 7 route wording and durable evidence records.
4. Run the task-scoped verifier and create one explicit-allowlist checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_joint_current_audit'
python -m pytest -q tests/test_joint_figure_provider.py tests/test_joint_lifecycle_closure.py tests/test_joint_coordinator.py tests/test_ir_nmr_joint_workbench_profiles.py
python scripts/verify.py --task docs/agent/tasks/2026-07-27-joint-route-plan-reconciliation.md --changed --types
```

Focused result: `14 passed` with exit code `0`. The final task-scoped verifier
passed task/memory checks, Ruff, compile/type baseline, quality `283 passed`,
preprocessing `106 passed`, and whitespace with exit code `0`, using external
basetemp `C:\Temp\PolyNexus_joint_route_verify`.

## Known limitations

Automated route closure does not establish that cross-technique scientific
comparisons are valid. Conflict provenance, real data, live GUI interaction,
and final release approval remain open.
