# Native SAXS strain Editor selection recovery

## Goal

Make the native SAXS strain Gallery-to-Editor route select a usable emitted
figure when the first manifest entry is an assetless diagnostic failure.

## Non-goals

- No SAXS algorithm, quality threshold, publication-role, or Manifest change.
- No automatic rescue, interpolation, fabricated figure, or scientific
  promotion of diagnostic evidence.
- No changes to the parallel full native visual acceptance task or memory
  files.

## Affected boundaries

- `polynexus/gui/plot_gallery_service.py`: initial Gallery selection only.
- `tests/test_plot_gallery_service.py`: pure regression contract.
- Native route evidence: `tests/test_native_gui_real_route_capture.py`.

## Acceptance criteria

- [x] Assetless entries remain present and visible in the Gallery.
- [x] Initial selection skips an assetless entry when a later entry has a
  usable emitted path.
- [x] The selected path is non-empty and the Editor opens in the native SAXS
  strain route.
- [x] Existing preferred-path behavior and all-assetless fallback remain
  intact.

## Implementation plan

1. Add a pure selection-path helper and use it only in the no-preferred-path
   Gallery fallback.
2. Lock the behavior with an assetless diagnostic regression test.
3. Run the native SAXS strain route, focused Gallery/Editor matrix, and the
   structured verifier, then checkpoint only the explicit allowlist.

## Verification

- `python -m pytest -q tests/test_plot_gallery_service.py -k assetless -vv`
- `python -m pytest -q tests/test_plot_gallery_service.py tests/test_figure_window_service.py`
- `python -m pytest -q tests/test_main_window_persistence.py -k 'open_selected_chart_editor or populate_plots or chart_editor_save or chart_editor_static' -vv`
- Native Windows command:
  `python -m pytest -q tests/test_native_gui_real_route_capture.py -k 'saxs.strain' -vv`
- `python scripts/verify.py --task docs/agent/tasks/2026-07-29-native-saxs-strain-editor-selection.md --changed --types`
- `git diff --check`

## TDD evidence

- RED was observed before the shared fix: the native focused route failed at
  `tests/test_native_gui_real_route_capture.py:199` because
  `window._chart_editor` remained `None` after the Gallery selected an
  assetless diagnostic entry.
- GREEN rerun on 2026-07-29: `1 passed, 16 deselected in 25.35s`; the capture
  directory contained `saxs_strain_editor.png`.

## Verification plan

1. `python -m pytest -q tests/test_plot_gallery_service.py -k assetless -vv`
2. Native focused route with `QT_QPA_PLATFORM=windows` and an external
   basetemp.
3. `python -m pytest -q tests/test_plot_gallery_service.py tests/test_figure_window_service.py tests/test_main_window_persistence.py`
4. `python scripts/verify.py --task docs/agent/tasks/2026-07-29-native-saxs-strain-editor-selection.md --changed --types`
5. `git diff --check`

The full repository/native visual acceptance run is not claimed by this task;
the existing full run had no readable final pytest summary and its broader
acceptance remains separately owned.

## Explicit checkpoint allowlist

- `polynexus/gui/plot_gallery_service.py`
- `tests/test_plot_gallery_service.py`
- `docs/agent/tasks/2026-07-29-native-saxs-strain-editor-selection.md`
- `docs/superpowers/specs/2026-07-29-native-saxs-strain-editor-selection.md`
- `docs/superpowers/plans/2026-07-29-native-saxs-strain-editor-selection.md`

Intentionally excluded: `docs/agent/memory/current-state.md`,
`docs/agent/memory/active-work.md`,
`docs/agent/tasks/2026-07-30-full-native-visual-reacceptance.md`, all capture
directories, `.superpowers/`, and all test-storage directories.

## Status

- [x] Root contract, README, and agent memory read.
- [x] Failure reproduced from the prior native run.
- [x] Focused native route green after the minimal Gallery selection fix.
- [ ] Focused matrix, structured verifier, and checkpoint still pending.
