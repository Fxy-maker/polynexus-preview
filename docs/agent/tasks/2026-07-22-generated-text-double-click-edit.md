# Generated text double-click editing

## Goal

Allow users to double-click an existing generated text object on the canvas,
edit its actual displayed text in the existing inline editor, and commit the
change through the normal undoable document-edit path.

## Affected boundaries

- Generated ChartEditor button-press routing and rendered text hit testing.
- Shared inline text editor initialization and generated text commit handling.
- Qt workflow regression coverage.

## Non-goals

- Do not change text-box geometry, coordinate-space semantics, rendering, or
  scientific analysis behavior.
- Do not change line, curve, rectangle, legend, or plot-series interactions.
- Do not modify generated outputs, runtime files, or pre-existing drafts.

## Acceptance criteria

- [x] Double-clicking text opens the inline editor with the current text.
- [x] Submitting edited text updates the text field through `UpdateTextCommand`.
- [x] Undo restores the previous text.
- [x] Existing text creation and drag behavior remain green.

## Implementation plan

1. Reproduce the missing double-click route with a real Matplotlib `MouseEvent`.
2. Route a text-body double-click to the existing inline editor using the
   rendered text bounds and preserve the current text as the edit value.
3. Commit generated text edits through `UpdateTextCommand`, then run focused
   tests and repository verification.

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_chart_editor_workflow.py tests/test_chart_editor_curve.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-22-generated-text-double-click-edit.md --changed --types
python scripts/verify.py --changed --types
```

## Known limitations

- The running GUI must be restarted from `D:\PolyNexus\scripts\launch_gui.py`
  before visually testing the new interaction.
