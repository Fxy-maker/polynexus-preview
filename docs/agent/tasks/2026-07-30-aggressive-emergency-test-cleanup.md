---
kind: task
status: completed
date: 2026-07-30
title: Aggressive emergency cleanup for test storage
---

# Aggressive emergency test cleanup

## Goal

Allow the local test-storage janitor to reclaim known disposable test output
after two hours when the target volume has less than 10% free space, without
deleting review/evidence or live/protected data.

## Non-goals

- Do not automatically delete review, evidence, archive, baseline, real-data,
  source, worktree, or unknown directories.
- Do not stop live pytest processes or bypass Windows ACLs automatically.
- Do not delete or move real C: or D: data during verification.
- Do not implement a background service or autonomous coding runner.

## Affected boundaries

- `scripts/test_storage.py`: emergency plan timing, legacy discovery, PID
  reconciliation, report fields, and running-manifest safety.
- `tests/test_test_storage.py`: decision, discovery, CLI, reconciliation, and
  deletion-failure regressions.
- `AGENTS.md` and `README.md`: operator contract.
- This task card, its design, and its implementation plan.

## Policy

Normal retention remains unchanged. Below 10% free space, failed/interrupted
`ephemeral` runs and known test-class `legacy` directories older than two hours
become eligible. Review, evidence, live PID, running manifest,
cleanup-pending, tracked, protected, symlinked, invalid, archive-like, and
unknown paths remain ineligible.

Known legacy discovery is limited to managed `run-*` paths and explicit
matrix/pytest test naming patterns. Names containing `archive`, `review`,
`evidence`, or `baseline` are excluded from emergency classification.

## Implementation plan

1. Extend cleanup decisions with emergency age and byte/report markers.
2. Reconcile managed manifests against a PID snapshot and discover known
   matrix/pytest legacy names without treating archives as test output.
3. Recompute disk pressure during every CLI plan build and expose emergency
   eligibility in JSON and human reports.
4. Preserve per-path deletion failures and protect running/cleanup-pending
   manifests before age evaluation.
5. Update operator documentation and validate the structured task card.
6. Run the focused storage matrix, task verifier, and real dry-run without
   applying emergency deletion.

## Acceptance criteria

- [x] Emergency pressure is evaluated during every cleanup-plan build.
- [x] Failed/interrupted ephemeral and known legacy artifacts older than two
  hours are emergency-eligible below 10% free space.
- [x] Running and cleanup-pending manifests remain protected; dead manifests
  are reconciled in memory as interrupted without report-side deletion.
- [x] Review, evidence, active, tracked, protected, symlink, invalid, archive,
  baseline, and unknown paths remain protected.
- [x] JSON and human reports show emergency status, emergency eligible bytes,
  and per-path deletion failures.
- [x] Focused storage tests, task-scoped verifier, and real dry-run pass.

## Verification

```powershell
python -m pytest -q tests/test_test_storage.py
python scripts/task_check.py --task docs/agent/tasks/2026-07-30-aggressive-emergency-test-cleanup.md
python scripts/verify.py --task docs/agent/tasks/2026-07-30-aggressive-emergency-test-cleanup.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
```

Do not run real `clean --apply` as part of this task. A first emergency apply
requires a separately reviewed JSON inventory and explicit authorization.

## Explicit changed-file allowlist

- `scripts/test_storage.py`
- `tests/test_test_storage.py`
- `AGENTS.md`
- `README.md`
- `docs/agent/tasks/2026-07-30-aggressive-emergency-test-cleanup.md`
- `docs/superpowers/specs/2026-07-30-aggressive-emergency-test-cleanup-design.md`
- `docs/superpowers/plans/2026-07-30-aggressive-emergency-test-cleanup.md`

## Pre-existing workspace changes

The shared checkout contains unrelated scientific-review source/test changes,
`docs/agent/memory/current-state.md`, `.superpowers/`, work-in-progress task
files, and many generated pytest directories. They remain outside this task's
checkpoint.

## Checkpoints

- `91012d7`: emergency decision contract.
- `d454c0b`: stale manifest reconciliation and known legacy discovery.
- `62a7d6b`: CLI pressure wiring and emergency report fields.
- `bc14678`: running-manifest deletion protection.

## Verification evidence

- Storage matrix: `38 passed, 1 skipped in 6.43s`.
- Task-scoped verifier: exit code `0`; task and memory checks passed, Ruff and
  compile passed, quality gate `290 passed`, preprocessing gate `106 passed`,
  and whitespace passed.
- Real report dry-run: emergency mode `true`, `126` artifacts,
  `76,595,807,762` bytes eligible in the first process snapshot.
- Real clean dry-run: emergency mode `true`, `126` artifacts, `93` emergency
  eligible artifacts, `116,946,589,183` eligible bytes, `removed: []`, and no
  failure records. The difference from the report snapshot reflects process
  reference revalidation between scans.
- No real `--apply`, ACL takeover, process termination, push, merge, or deploy
  was performed.
