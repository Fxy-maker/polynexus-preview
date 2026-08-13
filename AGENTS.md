# PolyNexus Agent Contract

This file is the repository-level contract for coding agents. Read it before
editing files. Detailed procedures live under `docs/agent/`.

PolyNexus is an AI-controllable polymer research workbench that users can also
operate independently. Codex/AI and the GUI work on the same project, run,
chart, evidence, and export objects. Neither entry point may create a private
analysis, provenance, or persistence representation.

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
4. Name affected shared objects and entry points. When a project, run, chart,
   evidence package, or export contract changes, verify the producer and each
   affected AI/CLI or GUI consumer.
5. Ask one concise question when an unresolved decision would materially change
   the implementation. Do not guess about scientific semantics or destructive actions.

## 2a. Token-efficient context

- Read in layers: start with the relevant memory index, task card, public
  contract, and targeted symbols or sections. Do not load entire historical
  memory files, broad source trees, or large generated artifacts by default.
- Scope `rg`, Git diff, and file reads to the affected boundary. Expand only
  when the first result is insufficient or the task is architecture, security,
  scientific semantics, or a repeated failure.
- Run commands with concise output. On failure, inspect the relevant failure
  tail and named files before collecting broader logs.
- Keep progress notes and completion reports short: state outcome, changed
  files, exact verification result, limitations, and untouched pre-existing
  changes. Do not repeat long command output or historical context.

## 3. While editing

- Keep changes within the requested scope; do not clean up unrelated files.
- Reuse existing public contracts before adding cross-layer interfaces.
- Put analysis behavior in core/services, not GUI event handlers.
- GUI code consumes `AnalysisResult`, DTOs, or view models; it must not branch on
  technique-specific internal algorithm state.
- AI/CLI and GUI must use the same public object contracts. AI can organize and
  request deterministic work, but cannot bypass canonical validation or invent
  scientific values.
- Prefer existing concise DTOs, manifests, indexes, and task/memory summaries
  over reparsing raw artifacts or reconstructing context from source code.
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
- Workflow, completion criteria, task template, and test selection:
  `docs/agent/workflow.md`, `docs/agent/definition-of-done.md`,
  `docs/agent/task-template.md`, `docs/agent/testing-matrix.md`
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

Test storage defaults are managed by `conftest.py`: ordinary pytest runs use a
unique external basetemp under `D:\PolyNexus-test-runs` (or the path in
`POLYNEXUS_TEST_ROOT`). Explicit `--basetemp <path>` remains supported for a
specialized run. The storage tool also discovers historical Windows test
directories named `C:\TempPolyNexus*` and the old malformed
`C:\UsersFANXUY~1AppDataLocalTemp*` pattern. Override the external legacy
roots with `POLYNEXUS_LEGACY_TEST_ROOTS` (`;`-separated on Windows), or add
one with `--legacy-root <path>`. Inspect and clean test artifacts with:

```powershell
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
python scripts/test_storage.py clean --older-than-hours 24 --apply
```

The cleanup command is dry-run by default. It skips young, Git-tracked,
protected, and active-process-referenced directories. While any pytest
process is active, all externally discovered legacy test directories remain
protected. Never put real datasets or source files under the managed
test-storage root.

New pytest runs use an explicit retention profile selected by
`POLYNEXUS_TEST_RETENTION`:

- `ephemeral` (default): successful agent-owned runs are removed immediately
  after pytest releases them; failures and interruptions are retained for 24
  hours.
- `review`: passed and failed runs are retained for 7 days.
- `evidence`: passed and failed runs are retained permanently.
- `legacy`: existing directories without a manifest use the 24-hour janitor
  cooldown and never receive an inferred pass/fail result.

Unknown profile values fail closed to `review`. When the target volume has
less than 10% free space, failed or interrupted `ephemeral` runs and known
test-class legacy directories older than two hours may be cleaned. Review,
evidence, active, running-manifest, cleanup-pending, protected, tracked,
symlinked, invalid, unknown, archive-like, and baseline paths keep their normal
safety rules. The CLI still requires explicit `clean --apply`; `report` and
`clean` without `--apply` are non-destructive. Review the JSON inventory before
the first emergency apply on a real drive.

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

## 8. Worktree lifecycle

Agent-created worktrees may be managed automatically only when they are
registered and agent-owned. Use `scripts/worktree_manager.py` rather than
deleting worktree directories directly:

```bash
python scripts/worktree_manager.py register <path-or-branch> --task <task-id>
python scripts/worktree_manager.py list --json
python scripts/worktree_manager.py inspect <path-or-branch>
python scripts/worktree_manager.py finish <path-or-branch> --reason "..."
python scripts/worktree_manager.py archive <path-or-branch> --reason "..."
python scripts/worktree_manager.py adopt-legacy --json
python scripts/worktree_manager.py adopt-legacy --apply
python scripts/worktree_manager.py clean
python scripts/worktree_manager.py clean --apply
```

For old Superpowers worktrees, `adopt-legacy --json` is the read-only report.
Only an explicit `--apply` adopts eligible unregistered `codex/*` worktrees
under the user-level Superpowers directory. Clean candidates enter the normal
one-hour cooldown; dirty candidates are archived and remain ineligible for
cleanup. Adoption never deletes a worktree or branch.

`clean` is dry-run by default and uses a one-hour cooldown. Deletion requires
all of these independent checks: agent ownership, `pending_cleanup` status, a
clean Git worktree, matching branch, matching HEAD/finished commit, and an
elapsed cooldown. Unknown or user-owned worktrees are never auto-deleted.

Dirty worktrees must be archived before removal. Archives are structured as
`diff.patch`, `untracked_files/`, `task_state.json`, and `reason.md` under the
user-level worktree archive directory. Branches are retained; automatic push,
merge, and branch deletion remain forbidden.

## 9. Completion report

Every completed task must summarize:

1. What changed and why.
2. Files changed.
3. Verification commands and outcomes.
4. Known limitations or follow-up work.
5. Pre-existing workspace changes intentionally left untouched.

## 10. Local repository maintenance

For the routine local finish sequence, use the coordinator after an atomic task
has an explicit changed-file allowlist:

```powershell
python scripts/repo_maintenance.py finish `
  --target main `
  --message "feat(scope): short summary" `
  --files path/to/file.py path/to/test_file.py `
  --task docs/agent/tasks/<task>.md `
  --cleanup
```

It runs the structured verifier, calls `scripts/auto_commit.py`, merges the
source branch into the local target worktree with `git merge --ff-only`, and
delegates cleanup to `scripts/worktree_manager.py`. It is local-only: it never
pushes, deploys, deletes branches, or resolves non-fast-forward history.
Existing staged changes, a missing target worktree, or a dirty target stop the
operation before merge. `--cleanup` still honors agent ownership, Git state,
matching branch/HEAD, and the cooldown period.

This coordinator is intentionally separate from the autonomous coding loop:
it does not call an AI model or implement tasks.

The exact user phrase `收尾任务` authorizes the agent to run this finish
sequence for the current atomic task. The agent must derive an explicit
changed-file allowlist from the current task, supply the task card and commit
message, and stop to ask if those values are ambiguous. Ordinary phrases such
as “做完了” or “完成这个任务” do not trigger local mainline integration.

## 11. Autonomous development loop

The repository provides loop primitives and the local maintenance coordinator,
but not a single autonomous coding runner. A loop runner must treat each atomic
task as a state machine:

```text
queued -> inspecting -> implementing -> verifying -> committed
                           ^               |
                           +-- repairing <-+

verifying -> blocked after repeated failure
committed -> next task or completed
```

For each iteration, preserve task state, changed-file scope, verification output,
repair-attempt count, commit hash, and next action. Automatically repair ordinary
test/lint/type failures, but pause after repeated failures or when the change
requires product, architecture, schema, scientific, security, or deployment
decisions. Use `scripts/verify.py` and `scripts/auto_commit.py` for the existing
verification and checkpoint primitives.

Do not claim that a continuous autonomous runner exists until an executable
`scripts/agent_loop.py` or equivalent has been added and tested.
