---
kind: lesson
status: active
date: 2026-07-18
title: Read the repository contract before implementation
---

## Lesson

`AGENTS.md` is part of the repository's implementation contract, not merely a
completion checklist. Before editing, read it together with `README.md`, the
memory snapshot, active-work register, and relevant module documentation.
State scope and acceptance criteria before a non-trivial change, and preserve
pre-existing workspace changes.

## Verification alignment

Use the repository-prescribed verifier when it exists and report the exact
command/result. In this repository, `AGENTS.md` references
`python scripts/verify.py --changed --types`, but the script was absent on
2026-07-18. The correct behavior is to report the unavailable verifier and use
the documented fallback evidence (focused tests, changed-file Ruff, compile,
and diff checks), not to imply that the verifier passed.

## Integration boundary

Do not push, merge, deploy, or send external messages without explicit
approval. A prior approval may be relevant context, but a new integration
should still state which branch/worktree is being changed and whether the
operation is local or remote.
