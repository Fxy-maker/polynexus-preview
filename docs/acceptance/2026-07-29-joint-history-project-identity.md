# Joint history project identity acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-29-joint-history-project-identity.md`
Status: automated display/persistence acceptance passed

## Scope

History restore projects the existing persisted/report identity into the
display-only Joint Workbench project badge. A single report sample uses its
sample name, multiple samples use the translated Joint workspace label, and an
empty report retains the default label. Joint calculations, conflicts,
validation, publication roles, run IDs, manifests, and source-run provenance
are not changed.

## Evidence

- Focused recheck:
  `python -m pytest -q tests/test_joint_lifecycle_closure.py tests/test_main_window_persistence.py -k 'joint_history or joint_hub_finished or joint_report or history_restore_rehydrates_report'`
  returned `4 passed, 194 deselected in 11.13s`, exit code `0`.
- Broader Joint/history recheck:
  `python -m pytest -q tests/test_joint_lifecycle_closure.py tests/test_main_window_history_mixin.py tests/test_main_window_persistence.py -k 'joint or history_restore'`
  returned `21 passed, 178 deselected in 39.10s`, exit code `0`.
- The implementation and regression tests were previously checkpointed in
  commit `6d3b760`; this acceptance/documentation checkpoint does not include
  unrelated source, scratch, or runtime files.

## Limitations

This closes the automated display/persistence regression only. Scientific
interpretation of Joint conflicts, restarted-GUI visual review, and final
release approval remain open under the full-software release audit.
