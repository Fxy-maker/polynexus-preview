# Origin Editor Stability and Usability Acceptance

## Runtime

- Worktree: `D:\PolyNexus-origin-main`
- Branch: `codex/origin-editor-stability-and-usability`
- Base/runtime source: `origin/main` at `a033494b`; current committed plan
  head is `ce575728`, with implementation remaining uncommitted in the
  isolated worktree at the time of this record.
- GUI test mode: PySide6 offscreen (`QT_QPA_PLATFORM=offscreen`).

## Automated GUI acceptance

The following checks exercise the generated and static editor workflows,
including curve rendering, line/arrow/rectangle creation, text click and drag,
preview-only motion, one-command commit, undo/cancel, selection handles, and
export overlay exclusion:

```text
python -m pytest tests/test_chart_editor.py -q
238 passed in 37.67s

python -m pytest tests/test_chart_editor_curve.py tests/test_chart_editor_workflow.py tests/test_annotation_canvas.py tests/test_annotation_render_adapter.py tests/test_chart_editor_generated_interaction_mixin.py tests/test_chart_editor_generated_drag_mixin.py tests/test_chart_editor_generated_drag_execution_mixin.py tests/test_chart_editor_generated_document_mixin.py tests/test_chart_editor_generated_geometry_mixin.py tests/test_chart_editor_generated_selection_mixin.py tests/test_chart_editor_generated_preview_mixin.py tests/test_figure_render_plan_core.py tests/test_figure_edit_commands.py -q
134 passed in 5.06s
```

The dedicated preview regressions verify that mouse movement does not replace
the canvas figure, change axes limits, mutate the document, or add history;
release creates one command and text drag opens the inline editor only after a
visible preview.

An additional end-to-end Qt interaction pass was run directly from this
worktree with the scientific-stack preload required by the repository's Qt
test bootstrap:

```text
QT_QPA_PLATFORM=offscreen python -
runtime_root C:\Users\FANXUY~1\AppData\Local\Temp\polynexus-origin-acceptance-dtrs3y65
generated_mode True
curve_created annotation-c2a8e008bd6f
text_undo_redo True
rectangle_cancelled True
export_bytes 106647
static_line_history 1
```

The exported PNG from that run was visually inspected and contained the
persisted line, curve, and text only; no selection handles, preview rectangle,
or inline-editor overlay was present.

## Project gates

```text
python scripts/quality_gate.py
compile: passed
focused-tests: 280 passed
preprocess_optimization: 103 passed
whitespace: passed

python -m ruff check polynexus/core/figure_edit_commands.py polynexus/core/figures/renderer.py polynexus/gui/chart_editor_status_service.py polynexus/gui/i18n.py polynexus/gui/widgets/annotation_canvas.py polynexus/gui/widgets/chart_editor.py polynexus/gui/widgets/chart_editor_edit_session_mixin.py polynexus/gui/widgets/chart_editor_generated_document_mixin.py polynexus/gui/widgets/chart_editor_generated_drag_execution_mixin.py polynexus/gui/widgets/chart_editor_generated_drag_mixin.py polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py polynexus/gui/widgets/chart_editor_generated_preview_mixin.py polynexus/gui/widgets/chart_editor_inline_text_mixin.py
All checks passed!

python -m compileall polynexus/core/figures polynexus/gui/widgets -q
passed

git diff --check
passed
```

`python scripts/verify.py --changed --types` was attempted but this baseline
does not contain `scripts/verify.py` (`No such file or directory`). A full
`python -m pytest -q` attempt and the required
`python scripts/quality_gate.py --all-tests` attempt were also made with a
300-second limit; both timed out without a failure report. The relevant full
editor module and the default project quality gate passed independently.

## Remaining limitation

The pass above uses the real PySide6/Matplotlib interaction path with an
offscreen Qt backend. A visible desktop pass is still optional follow-up work;
the existing legacy process may still be serving `D:\PolyNexus`, so it must
not be used as evidence for this branch.
