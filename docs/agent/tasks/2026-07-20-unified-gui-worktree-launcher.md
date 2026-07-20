# Unified GUI Worktree Launcher

## Goal

Make the desktop GUI launch the source checked out in `D:\PolyNexus` instead of
silently following an older Python editable-install worktree.

## Non-goals

- Do not merge, delete, or synchronize unrelated Git worktrees.
- Do not add hot reload to the running Qt process.
- Do not change chart-editor, analysis, export, or user-data behavior.

## Context

- The desktop shortcut currently launches bundled Python with `-m polynexus`
  and relies on editable-install resolution.
- Multiple Superpowers worktrees exist, including older Origin editor trees.
- The canonical GUI runtime worktree is `D:\PolyNexus` on the active development
  branch.

## Acceptance criteria

- [x] `scripts/launch_gui.py --diagnose` reports the canonical source root,
  active branch, commit, interpreter, and imported package path.
- [x] The launcher prepends its resolved root to `PYTHONPATH` and rejects an
  imported `polynexus` package outside that root.
- [x] The normal launcher starts `python -m polynexus --gui` with the resolved
  root as cwd and propagates the child exit code.
- [x] The desktop shortcut invokes the launcher from `D:\PolyNexus` and no
  longer references `D:\PolyNexus-runtime-stability` for its icon.
- [x] The README explains the canonical GUI worktree and restart-after-switch
  workflow.

## Affected boundaries

- [x] Documentation/tooling
- [x] GUI startup boundary
- [x] Regression tests

## Implementation plan

1. Add failing launcher tests covering root resolution, environment ordering,
   package-path validation, diagnostic metadata, and child command construction.
2. Implement the repository-local launcher without importing Qt modules.
3. Document the canonical worktree workflow and record the new durable launch
   boundary in agent memory.
4. Update and inspect the machine-local desktop shortcut.

## Verification

```bash
pytest tests/test_launch_gui.py -q
python scripts/launch_gui.py --diagnose
Python\pythoncore-3.14-64\python.exe scripts/launch_gui.py --diagnose
python scripts/verify.py --task docs/agent/tasks/2026-07-20-unified-gui-worktree-launcher.md --changed --types
```

## Risks and compatibility

- User-visible risk: launching from an invalid or stale root will fail with an
  explicit diagnostic instead of opening the wrong version.
- Existing editable installations remain usable for CLI callers; the launcher
  takes precedence only for the desktop GUI path.

## Memory impact

- [x] Update `docs/agent/memory/current-state.md` and
  `docs/agent/memory/active-work.md` with the launcher boundary and evidence.
