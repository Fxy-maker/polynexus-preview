---
task_id: 2026-07-30-saxs-gui-mask-editor-confirmed-rerun
kind: scientific-cross-module-gui
status: completed
date: 2026-07-30
title: Add a static SAXS GUI mask editor with confirmed rerun
---

# SAXS GUI mask editor confirmed rerun

## Goal

Allow a user to inspect and explicitly edit the detector mask for one static
2D SAXS result, confirm the detached candidate, and invoke exactly one normal
SAXS rerun through the existing quality and physical gates.

## Non-goals

- No directory, temperature, strain, or 1D mask editing.
- No automatic mask inference, interpolation, morphology, AI, automatic rescue,
  new threshold, or publication promotion.
- No changes to existing detector, data-quality, physical, or publication
  semantics.
- No edits to real datasets, generated outputs, `current-state.md`, or
  parallel/untracked scratch files.

## Affected boundaries

- Core preprocessing and `SAXSEngine` raw-data transport.
- GUI result-review action, static eligibility service, editor widget, and
  single-run candidate forwarding.
- Focused Qt/core regression tests and this task's documentation.

## Acceptance criteria

- [x] A static 2D preprocess result exposes a detached boolean base mask for
      the editor; sequence results do not expose an editor context.
- [x] The editor renders the image/mask state and supports explicit mask,
      unmask, reset, cancel, and confirm actions.
- [x] Cancel, close, invalid input, and zero-change edits do not start a run.
- [x] Confirmed candidates pass through the existing digest/shape validation
      and reach one `AnalysisWorker`/`SAXSEngine` static rerun.
- [x] Existing quality, physical, and publication gates remain authoritative.
- [x] TDD RED/GREEN, task verification, SAXS matrix, storage dry-run, diff,
      and explicit allowlist checkpoint are recorded.

## Implementation plan

1. Transport a detached configured detector-mask baseline from static SAXS
   preprocessing through `SAXSEngine.result.raw_data`.
2. Add a fail-closed static single-image eligibility service and a Qt editor
   supporting mask, unmask, reset, cancel, and explicit confirm actions.
3. Forward only confirmed, validated mask candidates through the existing
   `AnalysisWorker` and `SAXSEngine` static rerun boundary.
4. Verify the focused regression slice, structured changed-file checks, the
   current SAXS matrix, storage report/dry-run, and diff hygiene.
5. Record acceptance evidence and durable active-work state, then create one
   explicit allowlist checkpoint with `scripts/auto_commit.py`.

## Verification

```powershell
python -m pytest -q tests/test_saxs_gui_mask_editor_confirmed_rerun.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-gui-mask-editor-red
python -m pytest -q tests/test_saxs_gui_mask_editor_confirmed_rerun.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-gui-mask-editor-green
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
```

The exact SAXS matrix counts only a fresh complete pytest summary with exit
code `0`. Full/boundary release and human scientific/GUI review remain
separate gates. No `test_storage.py --apply` is authorized.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/preprocess.py`
- `polynexus/core/saxs.py`
- `polynexus/gui/saxs_mask_edit_service.py`
- `polynexus/gui/widgets/saxs_mask_editor.py`
- `polynexus/gui/main_window_results_mixin.py`
- `polynexus/gui/main_window_run_mixin.py`
- `tests/test_saxs_gui_mask_editor_confirmed_rerun.py`
- `docs/superpowers/specs/2026-07-30-saxs-gui-mask-editor-confirmed-rerun-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md`
- `docs/agent/tasks/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md`
- `docs/acceptance/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md`
- `docs/agent/memory/active-work.md`
