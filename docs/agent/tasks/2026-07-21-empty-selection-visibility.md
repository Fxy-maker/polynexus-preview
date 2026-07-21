# Empty selection visibility follow-up

## Goal

Make the chart editor's empty-selection state visually unambiguous so users do
not mistake the compatibility "Background" row for an actively selected
object.

## Affected boundaries

- ChartEditor inspector selection label and annotation property reset state.
- Object-list background activation behavior.
- Chinese/English editor translations and ChartEditor regression tests.

## Non-goals

- Do not remove the Background row or change explicit background editing.
- Do not change figure-document schema, rendering, analysis, or export behavior.
- Do not touch pre-existing user drafts or runtime directories.

## Acceptance criteria

- [x] Empty generated documents show a localized "No object selected" label.
- [x] Clearing a generated or static annotation selection restores the empty
  selection label.
- [x] Explicit background activation still shows the localized Background label.
- [x] Focused Qt regressions cover initialization, clearing, and background
  compatibility behavior.

## Implementation plan

1. Add localized empty-selection strings for the editor's inspector label.
2. Route initialization and selection-clearing paths to the empty-selection
   label while keeping explicit background activation separate.
3. Add regression assertions for empty generated documents and clear paths.
4. Run focused Qt tests, the structured verifier, and the default changed/type
   verifier; preserve the existing GUI restart limitation in the handoff.

## Verification

```powershell
python -m pytest tests/test_chart_editor.py tests/test_chart_editor_workflow.py -q -k "selection or escape or background"
python scripts/verify.py --task docs/agent/tasks/2026-07-21-empty-selection-visibility.md --changed --types
python scripts/verify.py --changed --types
```

## Known limitations

- The already-running GUI process must be restarted to load the updated source;
  the launcher diagnostic confirms the canonical source root and commit.
- A pre-existing subset of generated-selection tests still expects the newer
  drag-help status wording and is unrelated to this label change.
