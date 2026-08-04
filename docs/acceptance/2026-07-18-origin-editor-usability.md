# Origin editor usability acceptance evidence

Date: 2026-07-18
Branch: `codex/origin-editor-usability-implementation`

## Delivered behavior

- Inspector is a collapsible drawer and the live canvas retains its viewport
  dimensions when the figure style or physical figure size changes.
- The adjacent creation toolbar exposes text, line, arrow, editable quadratic
  Bézier curve, and rectangle tools. Curve geometry includes two endpoints and
  one control point; the Inspector exposes the control coordinates, and all
  endpoint/control edits use the edit session so undo/redo is preserved.
- Static annotations retain curve control geometry during move, drag-sync,
  copy, crop, and style updates.
- Package, OriginPro, and COM adapters share one source-preparation boundary:
  run-relative path candidates are ordered and explicit; pathless inline data
  is staged as CSV; an explicitly declared missing file never falls back to
  inline values and fails before external Origin state is created.
- Package exports preserve the normalized figure document. Direct adapters
  issue an explicit warning when a curve cannot be constructed as a native
  editable Origin curve.

## Automated verification

```powershell
python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor.py tests/test_annotation_canvas.py tests/test_chart_editor_curve.py tests/test_chart_editor_generated_interaction_mixin.py tests/test_chart_editor_generated_document_mixin.py tests/test_chart_editor_generated_geometry_mixin.py tests/test_origin_mapping.py tests/test_origin_package_exporter.py tests/test_originpro_adapter.py tests/test_origin_com_adapter.py tests/test_origin_contracts.py tests/test_chart_editor_origin_export.py -q
```

Result: `335 passed` in 40.70 seconds after rebasing onto `origin/main`.

The repository contract also prescribes:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-18-origin-editor-usability.md --changed --types
python scripts/verify.py --changed --types --full --boundary --base origin/main
```

Result: unavailable in this worktree because `scripts/verify.py` does not
exist. The fallback verification before review is changed-file Ruff, Python
compilation, and `git diff --check`.

## Remaining environment limitation

The package export path runs directly in tests. OriginPro and COM/LabTalk tests
use fakes because no external Origin installation is available in this
environment; live Origin project creation remains an environment-specific
manual check.
