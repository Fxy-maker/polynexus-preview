# MainWindow lint baseline acceptance

The monolithic MainWindow module now keeps only imports required by its own
implementation or by the existing mixin/module compatibility boundary. Dynamic
symbols consumed through `main_window_module.<name>` remain explicitly
annotated as compatibility exports; no broad file-level noqa was added.

## Verification evidence

```text
ruff check polynexus/gui/main_window.py
All checks passed!

python -m pytest --basetemp=C:\Temp\PolyNexus_main_window_workers_lint3 tests/test_main_window_workers.py -q
2 passed in 0.37s

python -m pytest --basetemp=C:\Temp\PolyNexus_main_window_persistence_lint_final2 tests/test_main_window_persistence.py -q
197 passed in 185.80s (0:03:05)

python scripts/verify.py --task docs/agent/tasks/2026-07-26-main-window-lint-baseline.md --changed --types
selected checks passed; quality gate 282 passed; preprocessing gate 103 passed
```

The remaining full release visual/scientific acceptance is tracked by the
full-software ledger and is not implied by this maintenance checkpoint.
