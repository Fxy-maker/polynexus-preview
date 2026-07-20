# Worktree Management

PolyNexus uses worktrees as temporary execution environments. A worktree is not
the long-term record of a task; the branch, commits, task state, and archive are.

## Commands

Run these commands from any PolyNexus worktree:

```powershell
python scripts/worktree_manager.py list
python scripts/worktree_manager.py list --json
python scripts/worktree_manager.py inspect <path-or-branch>
python scripts/worktree_manager.py register <path-or-branch> --task <task-id>
python scripts/worktree_manager.py finish <path-or-branch> --reason "task completed"
python scripts/worktree_manager.py archive <path-or-branch> --reason "task interrupted"
python scripts/worktree_manager.py adopt-legacy --json
python scripts/worktree_manager.py adopt-legacy --apply
python scripts/worktree_manager.py clean
python scripts/worktree_manager.py clean --apply
```

## One-time legacy adoption

Worktrees created before the current registry existed are intentionally
unregistered. First inspect eligible candidates without changing anything:

```powershell
python scripts/worktree_manager.py adopt-legacy --json
```

To explicitly adopt those candidates:

```powershell
python scripts/worktree_manager.py adopt-legacy --apply
```

The command considers only unregistered `codex/*` worktrees below the
user-level Superpowers PolyNexus directory. Clean candidates become
`pending_cleanup` with a fresh one-hour cooldown. Dirty candidates are copied
to a structured WIP archive and marked `legacy_dirty`; they are never deleted
by the adoption command. `clean --apply` remains the only deletion path, and
branches are retained.

The manager stores the registry and archives outside the repository, by default
under:

```text
%USERPROFILE%\.config\superpowers\worktrees\PolyNexus\
```

This avoids adding metadata files to every worktree and keeps the repository
clean. The registry is intent/state metadata; Git is the authority used for the
final deletion checks.

## Lifecycle

```text
create → register(active) → work → finish(pending_cleanup)
                                  ↓
                        one-hour cooldown
                                  ↓
                         clean --apply
```

For interrupted or dirty work, archive before cleanup. The archive is designed
for agent recovery rather than only disaster recovery:

```text
wip-archives/<task>/<timestamp>/
├── diff.patch
├── untracked_files/
├── task_state.json
└── reason.md
```

`task_state.json` records the worktree path, branch, HEAD, task metadata, dirty
state, timestamps, and reason. `reason.md` gives a short human-readable
recovery entry point.

## Deletion policy

The manager may remove a worktree only when all checks pass:

- `owner == agent`
- `status == pending_cleanup`
- `git status --porcelain` is empty
- registered branch equals the actual worktree branch
- registered finished commit equals the actual HEAD
- the one-hour cooldown has elapsed

A worktree is retained when it is unregistered, user-owned, dirty, branch/HEAD
metadata disagrees, or the cooldown has not elapsed. The default `clean` command
is a dry-run. `--apply` is the only deletion switch.

Branches are intentionally retained after worktree removal so commits remain
recoverable. The manager never pushes, merges, force-deletes branches, or removes
the current repository worktree.
