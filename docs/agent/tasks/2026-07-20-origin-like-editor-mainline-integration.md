---
kind: task
status: completed
date: 2026-07-20
title: Integrate Origin-like editor interactions into the canonical GUI branch
---

# Origin-like editor mainline integration

## Goal

Bring the tested Origin-like canvas interactions from
`codex/origin-editor-stability-and-usability` into the canonical
`D:\PolyNexus` GUI branch while preserving the current branch's editor workflow,
gallery, export, and maintenance improvements.

## Non-goals

- Do not merge the entire divergent worktree history or its older agent contract.
- Do not remove current object-tree, template, batch-edit, comparison, export,
  launcher, or repository-maintenance features.
- Do not change scientific analysis algorithms, generated real-data outputs, or
  Origin adapter semantics unless a focused editor interaction contract requires
  it.
- Do not push to a remote or delete worktrees/branches.

## Affected boundaries

- ChartEditor and annotation-canvas interaction mixins
- Figure edit command/render contracts used by interactive annotations
- Focused ChartEditor, annotation, and render regression tests
- Canonical GUI launch branch and local mainline integration

## Acceptance criteria

- [x] Text, line, arrow, rectangle, and curve interactions from the selected
      Origin-like commits are available in the canonical GUI branch.
- [x] Dragging uses preview/commit behavior and does not remove the current
      object tree, batch, comparison, template, export, or launcher behavior.
- [x] Focused Origin-like editor regressions pass.
- [x] `python scripts/verify.py --task docs/agent/tasks/2026-07-20-origin-like-editor-mainline-integration.md --changed --types` passes.
- [x] The local `main` worktree fast-forwards to the finished source branch.

## Implementation plan

1. Preserve the canonical editor workflow and transplant the selected
   Origin-like product/test paths rather than merging the divergent worktree
   history.
2. Verify static and generated direct-canvas creation, preview-only dragging,
   geometry handles, cancellation, persistence, and overlay-free export.
3. Repair any integration regression at the shared gesture-to-command boundary
   and rerun focused editor, core, lint, and compile checks.
4. Run the structured repository verifier, create the explicit checkpoint, and
   fast-forward the local `main` worktree without pushing or deleting worktrees.

## Implementation and verification evidence

- Source commits `93c265f7`, `a033494b`, and `cc900fa6` were integrated by
  product/test paths into `codex/origin-editor-usable-controls`; unrelated
  source-worktree agent tooling and drafts were excluded.
- The release path now routes `plot_series` and `legend` through the same
  preview/commit transaction as line, curve, and rectangle drags. This keeps
  preview motion out of the document while persisting exactly one edit on
  release.
- Focused editor matrix: `238 passed` for `tests/test_chart_editor.py` and
  `120 passed` for the remaining Origin-like canvas/layout/workflow files
  listed below (`358 passed` total).
- Origin-like drag/render/core matrix: `66 passed`.
- Ruff, `python -m compileall polynexus/core/figures polynexus/gui/widgets -q`,
  and `git diff --check` passed.
- A combined Qt process once terminated with a Windows access violation in a
  QListWidget visibility test; that test passed independently and the same
  matrix passed when split into stable Qt batches.

## Selected source commits

- `93c265f7` — Origin editor usability foundation
- `a033494b` — Origin-like canvas interactions
- `cc900fa6` — Origin-style drag stabilization

Only product/test paths belonging to these interaction contracts will be
transplanted. Older documentation and agent-tooling changes from the source
worktree are intentionally excluded.

## Verification

```bash
pytest tests/test_annotation_canvas.py tests/test_annotation_render_adapter.py tests/test_chart_editor.py tests/test_chart_editor_curve.py tests/test_chart_editor_layout.py tests/test_chart_editor_workflow.py tests/test_chart_editor_generated_geometry_mixin.py tests/test_chart_editor_generated_press_target_mixin.py tests/test_chart_editor_generated_preview_mixin.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-20-origin-like-editor-mainline-integration.md --changed --types
```

## Known limitations

- The full repository `pytest` suite may exceed the local five-minute runtime
  budget; exact timeout evidence will be reported if it recurs.
- Existing unrelated untracked worktree files remain untouched.
