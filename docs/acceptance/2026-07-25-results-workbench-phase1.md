# Results Workbench Phase 1 acceptance

## Delivered

The shared Results Workbench now consumes a typed, immutable profile for the
current analysis mode. SAXS static, temperature, and strain have distinct
narratives, tab labels, review actions, and manifest figure IDs. DSC, WAXS, IR,
NMR, and Joint modes are registered through the same profile boundary so they
can be refined without adding technique branches to Qt event handlers.

The panel exposes profile title/subtitle, hero metrics, structured result tabs,
empty/error state, figure-link signals, and review-action signals. The main
window routes figure links to the manifest-backed gallery and review actions
back to the results tab.

## Evidence

- `tests/test_results_workbench_profiles.py`: profile registry, model
  propagation, Qt empty/error state and figure-link behavior.
- Focused Results Workbench/SAXS/main-window matrix: 101 tests passed before
  the main-window routing additions; the expanded matrix passed 51 tests.
- `python -m ruff check` on changed Python files: passed.
- `python -m compileall -q` on changed Python files: passed.
- `git diff --check`: passed.

## Boundary and limitations

- Profile metadata is presentation-only; scientific calculations and evidence
  gates remain in their existing services.
- Generic non-SAXS figure links are initial role-level entry points and will be
  replaced with validated mode-specific manifest IDs in each vertical slice.
- Human restarted-GUI visual review remains part of the final release gate.
