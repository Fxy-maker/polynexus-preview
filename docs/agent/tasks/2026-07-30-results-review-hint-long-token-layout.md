---
task_id: 2026-07-30-results-review-hint-long-token-layout
kind: gui-regression
status: completed
---

# Results Review Hint long-token layout

## Goal

Prevent the Results Workbench review-hint detail/next row from expanding the
workspace horizontally when diagnostic evidence contains long tokens.

## Non-goals

- No change to analysis, evidence generation, thresholds, severity, or review
  semantics.
- No shortening or normalization of evidence source strings.
- No test-data deletion, migration, or fixture modification.

## Affected boundaries

- Shared display widget: `polynexus/gui/widgets/wrapped_evidence_label.py`.
- Results Workbench consumers:
  `polynexus/gui/widgets/results_table_panel.py` and
  `polynexus/gui/main_window_results_mixin.py`.
- Focused widget regression and real SAXS temperature restore/native route.

## Implementation plan

1. Add a failing ResultsTablePanel regression for long review-hint detail.
2. Move the display-only wrapped evidence label into a shared widget and apply
   it to review-hint detail/next; set ignored horizontal size policies so their
   size hints do not widen the panel.
3. Run focused tests, the real SAXS restore geometry probe, native single-route
   capture, and the structured verifier before checkpointing.

## Acceptance criteria

- [x] Review-hint detail preserves its exact `.text()` source.
- [x] Review-hint detail minimum width is bounded and panel size hint stays
  below 1000 px for the long-token regression.
- [x] Real SAXS temperature restore keeps the workspace content within the
  native viewport width.
- [x] Native SAXS temperature Results capture visibly wraps long evidence.
- [x] Human visual/scientific/release gates remain explicit.

## Verification

```powershell
python -m pytest -q tests/test_results_table_panel.py tests/test_saxs_results_evidence_layout.py tests/test_main_window_results_mixin.py -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-30-results-review-hint-long-token-layout.md --changed --types
git diff --check
```

Native single-route command:

```powershell
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_native_saxs_temp_layout_fixed_20260730'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_native_saxs_temp_layout_fixed_basetemp_20260730'
& 'D:\PolyNexus\Python\pythoncore-3.14-64\python.exe' -m pytest -q tests/test_native_gui_real_route_capture.py -k 'saxs.temperature' -vv
```

## Verification evidence

- TDD RED: the panel size hint measured `1188` px before size-policy bounds.
- Focused widget/GUI matrix: `26 passed in 3.81s`.
- Real SAXS temperature restore geometry probe: exit code `0`; the Results
  panel size hint width was `557`, review hint detail/next geometry widths were
  `375`/`374`, and workspace content width was `1188` against a `1356` viewport.
- Fresh native SAXS temperature route: `1 passed, 16 deselected in 17.09s`, exit
  code `0`; the capture is under
  `D:\PolyNexus_native_saxs_temp_layout_fixed_20260730`.
- Structured verifier: exit code `0`; task/memory checks, Ruff, compile, type
  baseline, quality gate (`287 passed`), preprocessing gate (`106 passed`), and
  whitespace checks passed.

## Known limitations

The native capture validates route construction and visual layout only. IR
mapping vendor/ROI semantics, NMR solid-C assignment correctness, Joint conflict
interpretation, SAXS diagnostic/validation meaning, and final release approval
remain human gates.

## Explicit changed-file allowlist

- `polynexus/gui/widgets/wrapped_evidence_label.py`
- `polynexus/gui/widgets/results_table_panel.py`
- `polynexus/gui/main_window_results_mixin.py`
- `tests/test_results_table_panel.py`
- `docs/superpowers/plans/2026-07-30-results-review-hint-long-token-layout.md`
- `docs/agent/tasks/2026-07-30-results-review-hint-long-token-layout.md`
- `docs/acceptance/2026-07-30-results-review-hint-long-token-layout.md`
- `docs/agent/memory/active-work.md`
