# Chart Editor Visual Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with review checkpoints.

**Goal:** Make the chart editor's canvas, left tool rail, inspector, and object actions feel like one coherent professional editing workspace.

**Architecture:** Keep `EditSession` and existing callbacks as the command boundary. Change only the Qt presentation layer: a themed tool rail, a responsive canvas/inspector shell, and a selection action strip that calls the existing visibility, lock, alignment, distribution, grouping, and delete routes.

**Tech Stack:** Python, PySide6, Qt layouts/widgets, existing ThemeEngine tokens, pytest/Qt offscreen tests.

---

### Task 1: Lock down the desired shell layout

**Files:**
- Modify: `tests/test_chart_editor_layout.py`
- Modify: `tests/test_chart_editor_tool_icons.py`

- [ ] **Step 1: Write failing layout assertions**

Add assertions that the editor uses an expanding canvas, a visible non-scrolling
inspector tab bar, and a tool rail wide enough for text-under-icon labels.

- [ ] **Step 2: Run the focused tests**

Run:

```bash
python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor_tool_icons.py -q
```

Expected: the new assertions fail against the current 36 px icon-only rail and
scrolling inspector tabs.

### Task 2: Implement the polished shell and tool rail

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor_layout_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_inspector_drawer_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/theme.py`

- [ ] **Step 1: Make the rail readable**

Configure `_EditorContextToolbar` with a 72–84 px width, 20–22 px icons,
`ToolButtonTextUnderIcon`, separators before history/export actions, and
localized accessible names. Preserve the existing action ids and callbacks.

- [ ] **Step 2: Balance the shell**

Use expanding size policies for the canvas stack, set the inspector minimum and
remembered width to 360–400 px, and retain the existing collapsible toggle.
Configure the inspector tab bar not to use scroll arrows and to expand tabs to
the available width.

- [ ] **Step 3: Run focused layout tests**

Run:

```bash
python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor_tool_icons.py -q
```

Expected: PASS.

### Task 3: Put common object actions beside the layer tree

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/widgets/chart_editor_layout_mixin.py`
- Modify: `tests/test_chart_editor_layout.py`
- Modify: `tests/test_chart_editor_context_menu.py`

- [ ] **Step 1: Write failing action-surface assertions**

Assert that the Object tab contains named controls for visibility, lock,
align, distribute, group, ungroup, and delete, and that the menu actions call
the same callbacks as the existing context menu.

- [ ] **Step 2: Implement the action strip**

Add a compact row of `QToolButton`/menu buttons immediately below object search
and above the layer tree. Reuse existing translation keys and callbacks; do
not duplicate command logic. Enable/disable the controls from the existing
selection synchronization path.

- [ ] **Step 3: Add theme-aware states**

Apply object names and existing theme tokens so hover, pressed, disabled, and
checked states are visually distinct without hard-coded technique colors.

- [ ] **Step 4: Run focused action tests**

Run:

```bash
python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor_context_menu.py tests/test_chart_editor_context_style_mixin.py -q
```

Expected: PASS.

### Task 4: Verify, update memory, and checkpoint

**Files:**
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/tasks/2026-07-20-editor-visual-polish.md`

- [ ] **Step 1: Run the structured verifier**

```bash
python scripts/verify.py --task docs/agent/tasks/2026-07-20-editor-visual-polish.md --changed --types
```

- [ ] **Step 2: Run the default verifier**

```bash
python scripts/verify.py --changed --types
```

- [ ] **Step 3: Record evidence and mark the task card completed**

Record exact focused and verifier results, then use the explicit allowlist
checkpoint:

```bash
python scripts/auto_commit.py --message "feat(editor): polish editor workspace" --files \
  polynexus/gui/widgets/chart_editor.py \
  polynexus/gui/widgets/chart_editor_layout_mixin.py \
  polynexus/gui/widgets/chart_editor_inspector_drawer_mixin.py \
  polynexus/gui/theme.py \
  tests/test_chart_editor_layout.py \
  tests/test_chart_editor_tool_icons.py \
  tests/test_chart_editor_context_menu.py \
  tests/test_chart_editor_context_style_mixin.py \
  docs/agent/tasks/2026-07-20-editor-visual-polish.md \
  docs/agent/memory/active-work.md
```
