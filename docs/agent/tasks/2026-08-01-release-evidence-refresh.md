---
task_id: 2026-08-01-release-evidence-refresh
kind: release-readiness
status: completed
date: 2026-08-01
title: Refresh current full-goal release evidence
---

# Current release evidence refresh

## Goal

Synchronize the full-goal acceptance ledger with the latest verified SAXS 2D
review-context checkpoint and current formal verification boundary.

## Non-goals

- Do not change production code, thresholds, publication roles, or scientific
  interpretation.
- Do not promote diagnostic, review-required, assignment-limited, or
  conditional results.
- Do not claim the full/boundary timeout as a test pass.
- Do not modify real data, generated outputs, scratch, or parallel source work.

## Affected boundaries

- Full-goal release acceptance ledger.
- Task/spec/plan evidence records.
- Durable release classification only.

## Implementation plan

1. Read the latest SAXS 2D task, formal verifier task, and current release
   packet.
2. Add a dated evidence amendment with exact commands, summaries, and exit
   classifications.
3. Run task-check, structured verification, boundary audit, and diff checks.
4. Create one explicit four-file allowlist checkpoint.

## Acceptance criteria

- [x] SAXS 2D checkpoint `a9e0743` and independent `700 passed` matrix are
  linked with exact evidence.
- [x] The formal full/boundary timeout remains classified as incomplete.
- [x] IR mapping, NMR solid-C, Joint, restarted-GUI, and owner approval gates
  remain explicit and conditional.
- [x] Task-check, verifier, boundary audit, and diff checks pass.
- [x] One explicit allowlist checkpoint is created.

## Verification

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-08-01-release-evidence-refresh.md
python scripts/verify.py --task docs/agent/tasks/2026-08-01-release-evidence-refresh.md --changed --types
python scripts/boundary_audit.py --root D:\PolyNexus --json
git diff --check
```

## Verification evidence

- `python scripts/task_check.py --task docs/agent/tasks/2026-08-01-release-evidence-refresh.md`
  exited `0`.
- `python scripts/verify.py --task docs/agent/tasks/2026-08-01-release-evidence-refresh.md --changed --types`
  exited `0`; quality `297 passed`, preprocessing `106 passed`, and task,
  memory, Ruff, compile, type-baseline, whitespace checks passed.
- `python scripts/boundary_audit.py --root D:\PolyNexus --json` exited `0`.
- `git diff --check` exited `0`.
- The latest formal full/boundary run remains incomplete: tool exit `124`, no
  pytest summary, and child manifest exit `3` at timeout/reap.

## Explicit changed-file allowlist

- `docs/acceptance/2026-07-31-full-goal-release-evidence-audit.md`
- `docs/agent/tasks/2026-08-01-release-evidence-refresh.md`
- `docs/superpowers/specs/2026-08-01-release-evidence-refresh-design.md`
- `docs/superpowers/plans/2026-08-01-release-evidence-refresh.md`

## Pre-existing workspace changes

Parallel SAXS source edits, memory edits, formal timeout records, scratch
directories, and test-storage artifacts remain outside this checkpoint.
