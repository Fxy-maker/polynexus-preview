# Inline text editor layering fix

## Goal

Ensure the direct-canvas text tool leaves its inline text input above the
Matplotlib canvas so users can see, focus, and type into the newly placed text
box.

## Affected boundaries

- Shared inline text editor widget stacking and focus behavior.
- Generated-canvas real Qt mouse interaction regression coverage.

## Non-goals

- Do not change text geometry, persistence, rendering, or document schema.
- Do not change static/generated text editing semantics beyond visibility and
  focus layering.
- Do not touch analysis code or pre-existing user drafts.

## Acceptance criteria

- [x] A real Qt drag with the generated Text tool opens the inline editor.
- [x] The inline editor is the widget at its visible center, above the canvas.
- [x] Existing generated text creation, commit, cancel, and geometry tests
  remain green.

## Implementation plan

1. Reproduce the generated text drag with real Qt mouse events and inspect the
   widget stack at the inline editor center.
2. Raise the shared inline editor after showing it and before focusing it.
3. Run focused text/interaction tests, the structured verifier, and the default
   changed/type verifier.

## Verification

```powershell
python -m pytest tests/test_chart_editor_workflow.py -q -k "text or inline"
python scripts/verify.py --task docs/agent/tasks/2026-07-21-inline-text-layering.md --changed --types
python scripts/verify.py --changed --types
```

## Known limitations

- The running GUI must be restarted after the fix because Python GUI processes
  do not hot-reload widget code.
