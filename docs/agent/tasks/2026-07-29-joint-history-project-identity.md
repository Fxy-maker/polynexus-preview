---
task_id: 2026-07-29-joint-history-project-identity
kind: gui-persistence
status: completed
---

# Joint history project identity

## Goal

Restore the persisted/report sample identity into the Joint Workbench project
badge so a restored Joint run does not appear as `No project` while its
diagnostic report is visible.

## Non-goals

- Do not change Joint calculations, thresholds, conflict severities, evidence,
  publication roles, or source-run provenance.
- Do not add raw-file ingestion or a new persistence schema.
- Do not infer a scientific sample identity when the report has no sample rows;
  retain the existing default label in that case.

## Affected boundaries

- `polynexus/gui/main_window_history_mixin.py`: history restore display context.
- `tests/test_joint_lifecycle_closure.py`: Joint publish/export/history route.
- Task plan, acceptance audit, and durable memory records.

## Implementation plan

1. Add a failing assertion for the existing restored `PA6-A` Joint lifecycle
   fixture.
2. Implement display-only identity resolution at the history restore boundary:
   explicit persisted label first, one report sample second, translated Joint
   workspace label for multiple samples, default label for no rows.
3. Run focused Joint/history regressions, the task verifier, and diff checks.
4. Record exact evidence and create one allowlisted local checkpoint.

## Acceptance criteria

- [x] The existing Joint lifecycle test fails before the production change with
  the restored label `No project`.
- [x] A single-row Joint restore shows the row sample name in the project badge.
- [x] A multi-row Joint restore uses the translated Joint workspace label.
- [x] An empty Joint report keeps the default `No project` label.
- [x] Existing Joint report values, validations, run IDs, manifests, and export
  provenance remain unchanged.
- [x] Focused tests, task verifier, whitespace check, and allowlist checkpoint
  pass.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_joint_history_identity_red_20260729'
python -m pytest -q tests/test_joint_lifecycle_closure.py -vv
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_joint_history_identity_verify_20260729'
python scripts/verify.py --task docs/agent/tasks/2026-07-29-joint-history-project-identity.md --changed --types
git diff --check
```

## Documentation checkpoint allowlist

- `docs/agent/tasks/2026-07-29-joint-history-project-identity.md`
- `docs/acceptance/2026-07-29-joint-history-project-identity.md`
- `docs/agent/memory/active-work.md`

The production/test implementation was previously checkpointed in commit
`6d3b760`; this follow-up checkpoint contains only the durable acceptance
records listed above.

## Known limitations

This fixes the visible restore identity only. It does not resolve the separate
scientific Joint conflict review or the final restarted-GUI release decision.

Implementation evidence: the Joint identity/lifecycle slice passed `5` tests
and the complete MainWindow persistence slice passed `197` tests on
2026-07-29. The task-scoped verifier passed with quality `283` and
preprocessing `106`; this task card is included in the allowlisted checkpoint.
