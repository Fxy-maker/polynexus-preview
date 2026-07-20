# Unified GUI Worktree Launch Design

## Goal

Make the desktop GUI consistently run the currently selected branch in the
canonical development worktree `D:\PolyNexus`, so switching branches no longer
silently leaves the application on an older editable-install target.

## Non-goals

- Do not merge, delete, or synchronize unrelated Git worktrees.
- Do not add hot-reload behavior to the running Qt application.
- Do not change the scientific analysis, chart-editor, or export behavior.
- Do not alter user data, generated figures, or the Python environments beyond
  the launch boundary.

## Approved approach

`D:\PolyNexus` remains the single GUI runtime worktree. Other worktrees can be
used for isolated agent or CI work, but the desktop shortcut intentionally does
not guess between them. A repository-local launcher will derive its source
root from the launcher location, use the bundled Python interpreter, prepend
that root to `PYTHONPATH`, and launch `python -m polynexus --gui` from that root.
This bypasses stale editable-install resolution while preserving the normal
package entry point.

The launcher will provide an explicit diagnostic mode that reports the resolved
root, Git branch, commit, interpreter, and imported `polynexus.__file__`. The
normal GUI launch will fail early with a readable error if the package resolves
outside the selected root. The desktop shortcut will target the launcher and
use the canonical root, so the visible application always corresponds to the
branch checked out in `D:\PolyNexus` after the user restarts it.

## Components and boundaries

1. `scripts/launch_gui.py` owns root resolution, interpreter selection,
   environment preparation, source-path validation, diagnostics, and child
   process startup. It must not import GUI modules itself.
2. `tests/test_launch_gui.py` covers root resolution, environment precedence,
   diagnostic metadata, and rejection of a mismatched imported package without
   starting Qt.
3. `README.md` documents the one-runtime-worktree rule and the restart step
   after switching branches.
4. `docs/agent/memory/current-state.md` and `active-work.md` record the new
   launch boundary and verification evidence.
5. The local desktop shortcut is updated to call the launcher with the bundled
   `pythonw.exe` and `D:\PolyNexus` as working directory. Its icon is changed
   from the stale runtime-worktree path to a stable local icon (a repository
   icon when one exists, otherwise the bundled executable icon). This is a
   machine-local setup action, not a tracked project artifact.

## Launch flow

```text
Desktop shortcut
    -> bundled pythonw.exe scripts/launch_gui.py
    -> resolve D:\PolyNexus from the script path
    -> prepend D:\PolyNexus to PYTHONPATH
    -> validate imported polynexus.__file__ belongs to that root
    -> start `python -m polynexus --gui` with cwd D:\PolyNexus
```

If the user wants to inspect another worktree temporarily, they can run that
worktree's copied/local launcher directly; this is explicit and does not alter
the desktop shortcut's canonical target.

## Error handling

- Missing `pyproject.toml` or package directory: exit non-zero with the
  resolved path and a repair hint.
- Missing bundled interpreter: exit non-zero and name the expected path.
- Imported package outside the resolved root: exit non-zero and report both
  paths, preventing another silent stale-version launch.
- Child GUI exit code: propagate it to the caller.

## Acceptance criteria

- Running the launcher from `D:\PolyNexus` imports
  `D:\PolyNexus\polynexus\__init__.py` regardless of installed editable
  distributions.
- The diagnostic command prints the active branch and commit and exits 0.
- A deliberately mismatched `PYTHONPATH` cannot make the launcher accept an
  outside `polynexus` package.
- The desktop shortcut uses the launcher, bundled Python, and `D:\PolyNexus` as
  working directory without referencing an old runtime worktree for its icon.
- `python scripts/verify.py --changed --types` passes.

## Verification

```text
pytest tests/test_launch_gui.py -q
python scripts/launch_gui.py --diagnose
python scripts/verify.py --changed --types
```
