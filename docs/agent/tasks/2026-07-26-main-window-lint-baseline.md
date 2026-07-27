---
task_id: 2026-07-26-main-window-lint-baseline
kind: maintenance-verification
status: completed
---

# MainWindow lint baseline

## Goal

Make the changed/type verifier reach the quality gate without changing
MainWindow behavior or deleting compatibility imports used by tests and public
module access.

## Non-goals

- Do not refactor MainWindow or its mixin boundaries.
- Do not remove imports solely because Ruff cannot see external re-export use.
- Do not change GUI behavior, scientific calculations, or export contracts.

## Affected boundaries

- `polynexus/gui/main_window.py` module import and logger initialization.
- Ruff changed-file verification and the existing quality/preprocessing gates.

## Acceptance criteria

- [x] Ruff reports no errors for `main_window.py` without broad noqa suppression.
- [x] MainWindow-focused regression remains green.
- [x] Structured verifier reaches and passes its quality/preprocessing gates.
- [x] An allowlisted checkpoint is created.

## Implementation plan

1. Confirm the baseline errors reproduce on `HEAD` and identify intentional
   public compatibility imports.
2. Make the smallest import-order/lint configuration change that preserves
   those contracts.
3. Run focused GUI tests, the structured verifier, and checkpoint the allowlist.

## Verification

```powershell
ruff check polynexus/gui/main_window.py
python -m py_compile polynexus/gui/main_window.py
python scripts/verify.py --task docs/agent/tasks/2026-07-26-main-window-lint-baseline.md --changed --types
```

## Verification result

- `tests/test_main_window_workers.py`: 2 passed.
- `tests/test_main_window_persistence.py`: 197 passed.
- Structured verifier: quality gate 282 passed; preprocessing gate 103
  passed; Ruff, compile, type baseline, memory, and whitespace checks passed.

## Checkpoint

- Atomic checkpoint: `cbb3077`.
