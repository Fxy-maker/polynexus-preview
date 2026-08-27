---
task_id: 2026-08-27-ftir-no-pa6-default
kind: scientific
status: active
date: 2026-08-27
title: Remove implicit PA6 defaults from IR analysis
---

# Remove implicit PA6 defaults from IR analysis

## Goal

Ensure IR analysis treats material identity as optional: without an explicit hint or project context it computes generic spectral features and may identify from observed peaks, but never silently injects PA6.

## Non-goals

- Do not delete the existing IR reference-band library.
- Do not change peak detection, fitting, preprocessing, or crystallinity-index equations.
- Do not redesign the GUI material controls in this task.

## Affected boundaries

- Core: IR configuration schema and temperature-series provider argument routing.
- Shared entry points: ComputeRunService may project project_context.material.name into an explicitly supplied IR config.
- GUI/CLI/Batch/Agent: unchanged signatures and shared ComputeRun producer; no required material field.
- Evidence: existing provenance and review rules remain unchanged.

## Acceptance criteria

- [x] IR standard submodule metadata has an empty material default.
- [x] Temperature-series analysis passes an empty material hint when config has none; no PA6 fallback remains.
- [x] Explicit IRConfig(polymer_name=...) still routes assignments and scores as before.
- [x] Generic no-hint analysis still returns detected peaks and does not invent polymer_name solely from a default.
- [x] Existing entry points run without new required arguments.

## Implementation plan

1. Add failing tests for empty IR defaults and no PA6 temperature fallback.
2. Remove the two PA6 defaults and wire explicit context material only through the shared compute service.
3. Run focused IR and cross-entry tests, then structured verification.

## Verification

python -m pytest -p no:cacheprovider -q tests/test_ftir_no_pa6_default.py tests/test_ir_engine.py tests/test_ir_temperature.py tests/test_compute_service.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-ftir-no-pa6-default.md --changed --types
git diff --check

## Checkpoint allowlist

python scripts/auto_commit.py --message "fix(ir): remove implicit PA6 analysis defaults" --files polynexus/core/ir.py polynexus/core/ir_engine/ir_temperature.py tests/test_ftir_no_pa6_default.py docs/agent/tasks/2026-08-27-ftir-no-pa6-default.md docs/superpowers/specs/2026-08-27-ftir-no-pa6-default-design.md docs/superpowers/plans/2026-08-27-ftir-no-pa6-default.md docs/agent/memory/active-work.md

## Completion evidence

- Exact commands and outcomes: pending implementation.
- Known limitations or follow-up: migrate remaining material-library policy and GUI display defaults separately.
- Pre-existing changes left untouched: active_run.json, runs/, tests/_tmp_phase3/.
