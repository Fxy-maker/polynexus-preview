# PolyNexus Agent Contract

This file is the repository-level contract for coding agents. Read it before
editing files. Detailed procedures live under `docs/agent/`.

## 1. Choose the lightest workflow

- Daily task: describe the goal and acceptance result in the prompt; a task card
  is optional. Run `python scripts/verify.py --changed --types` before handoff.
- Structured task: create a card under `docs/agent/tasks/` for architecture,
  schema, security, performance, scientific, or cross-module work.

## 2. Before editing

1. Read this file, `README.md`, and the relevant module documentation.
2. Check `git status --short --branch` and preserve pre-existing changes.
3. State the goal, non-goals, affected boundaries, acceptance criteria, and
   verification commands for any non-trivial task.
4. Ask one concise question when an unresolved decision would materially change
   the implementation. Do not guess about scientific semantics or destructive actions.

## 3. While editing

- Keep changes within the requested scope; do not clean up unrelated files.
- Reuse existing public contracts before adding cross-layer interfaces.
- Put analysis behavior in core/services, not GUI event handlers.
- GUI code consumes `AnalysisResult`, DTOs, or view models; it must not branch on
  technique-specific internal algorithm state.
- Add or update a focused regression test for every behavior change.
- Do not edit generated outputs, real regression datasets, secrets, or local
  runtime directories unless explicitly required.
- Do not push, merge, deploy, delete data, or send external messages without
  explicit approval.

## 4. Project artifacts and memory

- Design decisions: `docs/superpowers/specs/`
- Implementation plans: `docs/superpowers/plans/`
- Task cards: `docs/agent/tasks/`
- Agent memory: `docs/agent/memory/`
- Baselines: `docs/baselines/`
- Acceptance notes: `docs/acceptance/`
- Temporary diagnostics: ignored local output directories, never the repository root

At the start of a non-trivial task, read `docs/agent/memory/README.md`,
`current-state.md`, `active-work.md`, and relevant decision or lesson files.
At the end, update durable project state, decisions, lessons, or known issues
when they changed. Do not store secrets, raw logs, or duplicate source code.

## 5. Verification

Default local check:

```bash
python scripts/verify.py --changed --types
```

For a structured task:

```bash
python scripts/verify.py --task docs/agent/tasks/<task>.md --changed --types
```

For release or integration work:

```bash
python scripts/verify.py --changed --types --full --boundary
```

Use `--base <git-ref>` when checking a branch diff. Report exact commands and
results; never claim a check passed without running it.

After verification, create the task checkpoint automatically with an explicit
file allowlist:

```bash
python scripts/auto_commit.py \
  --message "feat(scope): short summary" \
  --files path/to/file.py path/to/test_file.py
```

The helper refuses to mix existing staged files, paths outside the repository,
or files without actual changes. It never pushes.

## 6. Superpowers integration

If the current agent environment provides Superpowers skills, use:

- `brainstorming` for non-trivial design
- `writing-plans` before multi-step implementation
- `test-driven-development` for new behavior or bug fixes
- `systematic-debugging` for failures or unexpected behavior
- `verification-before-completion` before claiming completion
- `requesting-code-review` before merge or handoff when available

If unavailable, follow the equivalent procedures in `docs/agent/`.

## 7. Review and checkpoints

- One atomic task should automatically produce one commit using
  `scripts/auto_commit.py` after verification.
- Link the task card and verification evidence in the commit or PR description.
- Ordinary tasks do not wait for a separate human approval before committing.
- Architecture, schema, security, performance, and scientific-semantics changes
  still require human review before merge.
- Review the cumulative diff at milestones, not only the last commit.
- Never auto-push, auto-merge, or auto-deploy.

## 8. Completion report

Every completed task must summarize:

1. What changed and why.
2. Files changed.
3. Verification commands and outcomes.
4. Known limitations or follow-up work.
5. Pre-existing workspace changes intentionally left untouched.
