---
kind: state
status: active
date: 2026-07-22
title: Current PolyNexus repository state
---

## Mainline snapshot

- The dedicated local `main` worktree is at merge commit `583709ad`, which
  includes the Origin editor menu, run-root source-path fixes, visible native
  Origin activation, object-document routing, native plot rescaling,
  one-Graph multi-series export, source axis-scale forwarding, user-registry
  capability probing, and the GUI startup boundary restoration. It is ahead of
  `origin/main` locally; it has not been pushed.
- The active development worktree is `D:\PolyNexus` on
  `codex/origin-editor-usable-controls`, at the same merged commit. Its
  pre-existing untracked `.superpowers/` and Origin Lite design drafts are left
  untouched.
- The 2026-07-20 Origin-like editor integration checkpoint is part of the
  canonical branch finish sequence. It preserves the current workflow/editor
  surface while adding the transplanted direct-canvas annotation interactions
  and stabilized preview/commit drag transactions.
- The desktop GUI launch boundary is now `D:\PolyNexus`. The repository-local
  `scripts/launch_gui.py` prepends that root to `PYTHONPATH`, probes the imported
  `polynexus.__file__`, and reports branch/commit identity before starting the
  GUI, so stale editable-install worktrees cannot be selected silently.

## Important boundaries

- The normal figure gallery is manifest-only. Legacy recursive discovery stays
  behind the explicit recovery path; see decision `0003`.
- Generated figure documents store data-source paths relative to the active run
  when `path_kind` is `run_relative`.
- Gallery entries carry `run_root` into ChartEditor. Origin export carries that
  context as `ExportRequest.source_root`, and all Origin adapters use the shared
  `polynexus/origin/path_resolution.py` resolver before falling back to the
  figure directory and process working directory.
- When native Origin automation is available, the ChartEditor action now uses
  the `originpro` adapter to show/activate Origin and leave the created graph
  visible; see decision `0011`.
- Origin capability probing checks `ORIGIN_EXE` in the current process first and
  then reads the Windows user environment registry, so a `setx ORIGIN_EXE ...`
  configuration is recognized without restarting the GUI process.
- Origin export is optional and Windows-only. Adapter order is high-level
  `originpro`, COM/LabTalk, then an Origin-compatible package fallback. The GUI
  must remain usable without Origin installed.
- Native OriginPro export now maps each plot's `data_ref` to its own worksheet,
  applies document colors/names and balanced display line widths, sets the
  four frame-axis thicknesses, and forwards first-panel axis labels in addition
  to axis scales. Mathtext labels are converted to readable Unicode at the
  native boundary, and all plots still reuse one Graph.

## Verification evidence

- The 2026-07-20 editor interaction reliability slice adds stable static body
  drag/resize transactions, generated text/rectangle body dragging, visible
  distance-aware curve bends, line endpoint-preserving body movement, fixed
  context-bar layout, and selection viewport preservation. Focused interaction
  tests pass (`109`), remaining ChartEditor-related modules pass (`156`), and
  targeted legacy ChartEditor drag/undo/static checks pass (`7`). The task card
  is `docs/agent/tasks/2026-07-20-editor-interaction-reliability.md`.

- The 2026-07-20 editor workflow completion slice passed its focused regression
  matrix (`354 passed`), structured verifier, and default verifier. It adds
  document diagnostics, distribution/visibility/layers/context actions,
  templates/format painter, previewed batch editing, comparison/revision diff,
  and export presets; see task card
  `docs/agent/tasks/2026-07-20-editor-workflow-completion.md`.

- Unified GUI launcher tests: 6 passed; system and bundled Python diagnostic
  probes both resolved `D:\PolyNexus\polynexus\__init__.py` on the active
  development branch before the implementation checkpoint.
- Origin capability, adapter, contract, package, and ChartEditor Origin tests:
  44 passed.
- GUI-startup regression checks: 3 passed.
- ChartEditor regression suite: 238 passed.
- Origin-like editor integration matrix: 358 focused editor/layout/workflow
  tests passed in stable Qt batches, plus 66 generated drag/geometry/render/core
  tests.
- Native Origin source/style fidelity suite: 16 passed.
- Native Origin label-display follow-up: 18 passed in the combined focused
  Origin suite.
- Native Origin style-polish follow-up: 18 passed in the combined focused
  Origin suite; the live five-plot smoke read back 1.2-point plot lines and
  0.8-point `x/x2/y/y2` frame axes.
- Automatic-commit regression tests: 2 passed.
- Ruff checks and `compileall` passed for the changed Origin/editor modules.
- The repository verification tooling was restored in commit `6002221`,
  including `scripts/verify.py`, `scripts/agent_memory.py`,
  `scripts/task_check.py`, and `pyrightconfig.json`. The prescribed command
  `python scripts/verify.py --changed --types` now passes, including the
  memory check, changed-file checks, focused quality gate, and preprocessing
  optimization gate.
- Worktree lifecycle management is available through
  `scripts/worktree_manager.py`. It uses a user-level registry, structured WIP
  archives, Git state rechecks, and a one-hour cleanup cooldown; existing
  unregistered worktrees remain protected.

## Known limitations and next actions

- The workflow-convergence Goal is active on `codex/origin-editor-usable-controls`.
  Commits `6857f05`, `8f254d1`, `0cc03b5`, `03e9090`, `a4fa6e3`, and `8a6075f`
  add workspace context safety, editor capability labels, run stages/cancel/retry,
  split export intents, selection-activated gallery actions, a diagnostics drawer,
  and narrow-window shell reduction. Focused checks for these slices are green.
- The 2026-07-23 workflow hardening checkpoint removes the reproducible
  Windows Qt access violation in the legacy `LayerTreeItem` visibility path by
  deferring tree reconstruction until `itemChanged` returns. The full
  `tests/test_chart_editor.py` invocation now passes (`238`) with an external
  `--basetemp` directory.
- `scripts/verify.py --changed --types` currently reports the repository's
  pre-existing Ruff baseline in the monolithic `main_window.py`; changed behavior
  was validated with focused pytest and `py_compile` checks.

- The final workflow-focused matrix passes (`118`, four known Matplotlib
  tight-layout warnings), along with the structured task verifier, quality
  gate (`282`), preprocessing optimization gate (`103`), and GUI launcher
  diagnostic. Copyable error diagnostics and the immutable GUI `RunState`
  service are now explicit boundaries; a human visual walkthrough remains
  pending for static/generated/log-axis interactions and narrow-window shell
  presentation.

- A live style smoke export using the configured `Origin64.exe` returned
  `success/originpro` for a synthetic five-plot document. In-process
  inspection found one Graph, five plots, five document colors, five 1.2-point
  display lines, 0.8-point `x/x2/y/y2` frame axes, five source worksheets,
  named Y columns, a `log10` Y axis, and clean Unicode axis labels. The
  temporary `.opju` remains locked until Origin closes; this is expected
  application ownership.
- The Origin-like editor integration is local-only and is advanced through the
  repository maintenance finish sequence; an explicit push decision remains
  pending.
- The 2026-07-24 LegendLayout refactor is complete on the active branch.
  Generated legend placement, selection, drag/resize, inspector, and export
  now share `polynexus/core/figures/legend_layout.py`; focused compatibility
  and editor coverage is `292 passed`. Manual GUI review of static, log-axis,
  and multi-series visuals remains pending because Chromium is unavailable.
- Reconcile the older active-work entries in `active-work.md` against the
  current branch/PR state before using them as authoritative.
