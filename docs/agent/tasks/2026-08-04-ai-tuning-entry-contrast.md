---
task_id: 2026-08-04-ai-tuning-entry-contrast
kind: gui
status: completed
date: 2026-08-04
title: Fix AI tuning entry description contrast
---

## Goal

Restore readable contrast for the AI parameter recommendation entry on the
Results page without changing its availability or tuning workflow.

## Non-goals

- Do not change AI candidate generation, safety gates, or rerun behavior.
- Do not change the global muted palette used by other low-priority labels.

## Affected boundaries

- `polynexus/gui/main_window_results_mixin.py`
- `tests/test_main_window_persistence.py`

## Implementation plan

1. Reproduce the low-contrast entry description with a GUI style assertion.
2. Use the existing theme secondary text token for this explanatory label.
3. Run the focused Results/AI tuning regression and task-scoped verifier.

## Acceptance criteria

- [x] AI tuning entry description uses readable secondary text contrast.
- [x] AI tuning entry button remains visible and unchanged.
- [x] Focused GUI tests and task verifier pass.

## Verification

```powershell
python -m pytest -q tests/test_main_window_persistence.py -k "ai_tuning or results_page" tests/test_context_suggestion_service.py
python scripts/verify.py --task docs/agent/tasks/2026-08-04-ai-tuning-entry-contrast.md --changed --types
git diff --check
```

## Evidence

- RED: the new style assertion failed with `color: #555d7a;`.
- GREEN: focused Results/AI tuning tests passed (`22 passed, 185 deselected`).

## Pre-existing state

The worktree contains unrelated staged, unstaged, deleted, and untracked user
changes. They remain untouched and are excluded from the checkpoint.
