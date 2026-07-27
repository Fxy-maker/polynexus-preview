---
task_id: 2026-07-27-gui-responsive-shell
kind: gui-acceptance
status: completed
---

# GUI responsive shell

## Goal

Close the concrete restarted-GUI usability defect found during the full
software acceptance walkthrough: the canonical Workbench shell must remain
usable without right-edge clipping at default and maximized sizes.

## Non-goals

- Do not change scientific semantics, analysis thresholds, evidence states,
  publication roles, or export contracts.
- Do not modify real fixtures, generated outputs, secrets, or pre-existing
  scratch directories.
- Do not treat this task as human scientific sign-off or final release approval.

## Affected boundaries

- `polynexus/gui/main_window_shell_mixin.py`
- `polynexus/gui/main_window.py`
- `polynexus/gui/main_window_history_mixin.py`
- `tests/test_main_window_shell_mixin.py`
- `tests/test_ui_function_streamlining.py`
- This task's design, plan, acceptance, and durable memory entries.

## Implementation plan

1. Add a focused failing shell regression that proves compact decisions use
   actual content width and preserve the task card.
2. Update `MainWindowShellMixin` to collapse optional metrics and top-bar
   shortcuts in compact content while retaining menu routes.
3. Make MainWindow header labels and top-bar widgets compressible, and put the
   History action toolbar in an internal horizontal scroll container.
4. Run the structured and full/boundary verifiers, restart the canonical GUI,
   inspect the resulting layout, and checkpoint the explicit allowlist.

## Acceptance criteria

- [x] Compact mode uses actual content width rather than only full window width.
- [x] Task card and workspace title remain visible in compact mode.
- [x] Secondary metrics and top-bar shortcuts collapse in a documented priority
  order when their layout overflows.
- [x] Focused regression tests cover compact and wide shell states.
- [x] Restarted canonical GUI/Qt-grab inspection shows no right-edge clipping.
- [x] Structured verifier and the full/boundary verifier pass, with any
  pre-existing warnings recorded rather than hidden.
- [x] One allowlisted checkpoint commit is created by `scripts/auto_commit.py`.

## Verification result

- Fresh focused GUI matrix: `18 passed in 6.50s`.
- Fresh task-scoped verifier with an isolated basetemp: task/memory checks,
  Ruff, compile/type baseline, quality `282`, preprocessing `106`, and
  whitespace all passed.
- Fresh full/boundary verifier with an isolated basetemp: `2773 passed, 10
  warnings in 1451.67s`; compile, quality, preprocessing, Ruff/type,
  whitespace, and boundary checks passed. Warnings were the existing
  tight-layout, DSC polynomial-conditioning, and Arial CJK glyph warnings.
- The GUI allowlist checkpoint was created locally with `scripts/auto_commit.py`;
  no push, merge, deploy, or scratch cleanup was performed.

## Verification

```powershell
python -m pytest tests/test_main_window_shell_mixin.py tests/test_ui_function_streamlining.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-gui-responsive-shell.md --changed --types
python scripts/verify.py --changed --types --full --boundary
python scripts/launch_gui.py --diagnose
python scripts/verify.py --task docs/agent/tasks/2026-07-27-gui-responsive-shell.md --changed --types
```

## Changed-file allowlist

- `polynexus/gui/main_window_shell_mixin.py`
- `polynexus/gui/main_window.py`
- `polynexus/gui/main_window_history_mixin.py`
- `tests/test_main_window_shell_mixin.py`
- `tests/test_ui_function_streamlining.py`
- `docs/superpowers/specs/2026-07-27-gui-responsive-shell-design.md`
- `docs/superpowers/plans/2026-07-27-gui-responsive-shell.md`
- `docs/acceptance/2026-07-27-gui-responsive-shell.md`
- `docs/agent/tasks/2026-07-27-gui-responsive-shell.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
