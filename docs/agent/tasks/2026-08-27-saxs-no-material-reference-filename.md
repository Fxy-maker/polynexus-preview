---
task_id: 2026-08-27-saxs-no-material-reference-filename
kind: scientific
status: active
date: 2026-08-27
title: Remove material-name filename bias from SAXS reference selection
---

# Remove material-name filename bias from SAXS reference selection

## Goal

Make SAXS static reference-frame selection deterministic and material-agnostic by removing the special-case preference for filenames containing PA6.

## Non-goals

- Do not change SAXS equations, calibration formulas, or quality thresholds.
- Do not infer sample identity from filenames.
- Do not add a GUI material database or new required context fields.

## Affected boundaries

- Core: static SAXS batch reference-frame selection.
- Shared consumers: GUI, CLI, Batch, Agent/Codex continue using the same SAXS provider and ComputeRun contract.
- Evidence: reference frame remains source-indexed and reviewable.

## Acceptance criteria

- [x] Static SAXS selection does not inspect filenames for material names.
- [x] The selected reference is the first analyzed frame with a finite invariant, falling back to the first available frame only when needed.
- [x] Renaming a PA6-like file cannot change the selected reference when data and ordering are unchanged.
- [x] Empty/invalid reference data still produces the existing unavailable-calibration behavior.

## Implementation plan

1. Add failing tests that expose PA6 filename preference and define stable data-based selection.
2. Remove filename inspection and select a valid data-backed reference deterministically.
3. Run SAXS-focused and shared ComputeRun tests, then structured verification and checkpoint.

## Verification

python -m pytest -p no:cacheprovider -q tests/test_saxs_no_material_reference.py tests/test_saxs_batch_parameters.py tests/test_saxs_temperature.py tests/test_compute_service.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-saxs-no-material-reference-filename.md --changed --types
git diff --check

## Checkpoint allowlist

python scripts/auto_commit.py --message "fix(saxs): remove material filename reference bias" --files polynexus/core/saxs.py tests/test_saxs_no_material_reference.py docs/agent/tasks/2026-08-27-saxs-no-material-reference-filename.md docs/superpowers/specs/2026-08-27-saxs-no-material-reference-design.md docs/superpowers/plans/2026-08-27-saxs-no-material-reference.md docs/agent/memory/active-work.md

## Completion evidence

- Exact commands and outcomes: pending implementation.
- Known limitations or follow-up: explicit project-context reference-frame selection can be added later if a study needs a non-first control.
- Pre-existing changes left untouched: active_run.json, runs/, tests/_tmp_phase3/.
