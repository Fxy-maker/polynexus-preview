# PolyNexus Agent Memory

This directory is the durable, repository-grounded memory for coding agents.
Markdown is the source of truth; do not store secrets, raw logs, temporary
diagnostics, or duplicated source code here.

## Read order

At the start of a non-trivial task, read:

1. `current-state.md` for the current branch, boundaries, and known issues.
2. `active-work.md` for ongoing work, blockers, and next actions.
3. Relevant files under `decisions/` and `lessons/`.

Also read the repository `AGENTS.md`, `README.md`, and relevant module
documentation before editing.

## Memory types

- `current-state.md`: concise snapshot of the current mainline and important
  implementation boundaries.
- `active-work.md`: work that is in progress, recently completed, or awaiting
  review. Each active item should include status, blocker, next action, and
  evidence when those details matter to a later agent.
- `decisions/`: durable architectural or cross-boundary choices, with rationale,
  consequences, evidence, and revisit conditions.
- `lessons/`: reusable implementation, debugging, and workflow lessons that do
  not belong to one feature only.

## Update protocol

At the end of a task, update only the durable facts that changed. Prefer a
focused addition or correction over a wholesale rewrite. Keep dates in ISO
format (`YYYY-MM-DD`) and link to task cards, acceptance notes, source
boundaries, or verification commands when available.

If a documented command or artifact is missing, record that fact explicitly
instead of claiming the check passed. Do not mark work complete merely because
tests pass; record known limitations and pending human review as well.
