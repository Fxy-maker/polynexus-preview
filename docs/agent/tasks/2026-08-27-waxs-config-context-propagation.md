---
task_id: 2026-08-27-waxs-config-context-propagation
kind: architecture
status: active
date: 2026-08-27
title: Preserve explicit WAXS configuration and project context
---

# Preserve explicit WAXS configuration and project context

## Goal

Make WAXS honor the explicit configuration supplied by shared entry points, including an optional project-context crystal-form hint, instead of silently replacing it with defaults.

## Non-goals

- Do not remove the WAXS reference peak library.
- Do not change peak-fitting equations, detector geometry, or numerical thresholds in this task.
- Do not add a GUI material database or required material fields.

## Affected boundaries

- Core: WAXSEngine configuration construction and ProjectContext projection.
- Shared entry points: ComputeRunService remains the only context-to-provider bridge.
- GUI/CLI/Batch/Agent: unchanged signatures and no-context behavior.
- Evidence: existing provenance remains authoritative.

## Acceptance criteria

- [x] WAXSEngine(WAXSConfig(...)) retains the supplied config values.
- [x] An explicit techniques.waxs.polymer_type context value is applied only when the provider config has no explicit value.
- [x] Missing context leaves WAXS config unchanged and does not require material input.
- [x] Invalid/non-string WAXS context hints are rejected as project_context_invalid.

## Implementation plan

1. Add failing constructor and ComputeRun context-projection tests.
2. Preserve the WAXS config and validate/project an explicit WAXS crystal-form hint.
3. Run WAXS, ComputeRun, and structured verification; create a local checkpoint.

## Verification

python -m pytest -p no:cacheprovider -q tests/test_waxs_config_context.py tests/test_compute_service.py tests/test_waxs_engine.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-waxs-config-context-propagation.md --changed --types
git diff --check

## Checkpoint allowlist

python scripts/auto_commit.py --message "fix(waxs): preserve explicit config and context" --files polynexus/core/project_context.py polynexus/core/compute/service.py polynexus/core/waxs.py tests/test_waxs_config_context.py docs/agent/tasks/2026-08-27-waxs-config-context-propagation.md docs/superpowers/specs/2026-08-27-waxs-config-context-design.md docs/superpowers/plans/2026-08-27-waxs-config-context.md docs/agent/memory/active-work.md

## Completion evidence

- Exact commands and outcomes: pending implementation.
- Known limitations or follow-up: broader WAXS threshold/material-library policy migration remains separate.
- Pre-existing changes left untouched: active_run.json, runs/, tests/_tmp_phase3/.
