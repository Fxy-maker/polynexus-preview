---
task_id: 2026-08-27-shared-compute-run-canonical-routing
kind: architecture
status: implementation_complete_review_required
date: 2026-08-27
title: Route canonical templates through shared ComputeRun
---

# Route canonical templates through shared ComputeRun

## Goal

Make Quick Analysis and single-file CLI share canonical conversion and finite
capability results through `ComputeRunService`.

## Non-goals

- No Batch or Agent/Codex migration.
- No DSC thermal-program conversion.
- No provider algorithm or GUI persistence rewrite.
- No vendor parser implementation.

## Shared objects and entry points

- Objects: `CanonicalExperiment`, `CapabilityItemResult`, `ComputeRun`.
- Producer: `ComputeRunService`.
- Consumers: existing Quick Analysis worker and single-file CLI continue to
  consume the same `ComputeRun`; no private result shape is added.
- Batch and Agent/Codex remain explicitly unchanged compatibility consumers.

## Affected boundaries

- `polynexus/core/compute/models.py`: optional source-bound canonical template.
- `polynexus/core/compute/service.py`: generic conversion, item execution, and
  pre-provider `needs_input` boundary.
- Focused compute/CLI/GUI worker tests verify both affected consumers.

## Acceptance criteria

- [x] Ready generic IR/SAXS/WAXS input produces a completed `ComputeRun` with
  canonical template and finite capability items.
- [x] Generic mapping ambiguity returns `needs_input` and provider is not called.
- [x] Vendor-like formats retain legacy provider behavior without canonical
  items.
- [x] Provider failure after canonical conversion retains template/items.
- [x] Single-file CLI and Quick Analysis worker expose the same `ComputeRun`
  fields.
- [x] Existing direct-run and provider regression suites remain green.

## Implementation plan

1. Add failing model/service/CLI/worker tests for canonical fields and routing.
2. Add `canonical_template` validation/serialization to `ComputeRun`.
3. Update `ComputeRunService` to convert generic inputs, execute capabilities,
   block ambiguous mappings, and preserve legacy provider execution.
4. Run focused consumer tests and structured verification; update memory and
   create an allowlisted checkpoint.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_compute_models.py tests/test_compute_service.py tests/test_cli_run_single_service.py tests/test_main_window_workers.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-shared-compute-run-canonical-routing.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(compute): route canonical templates through ComputeRun" `
  --files docs/superpowers/specs/2026-08-27-shared-compute-run-canonical-routing-design.md docs/agent/tasks/2026-08-27-shared-compute-run-canonical-routing.md polynexus/core/compute/models.py polynexus/core/compute/service.py tests/test_compute_models.py tests/test_compute_service.py tests/test_cli_run_single_service.py tests/test_main_window_workers.py docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes: focused consumer matrix `73 passed, 4 skipped`;
  structured verification passed task-check, Ruff, compile, quality `309`,
  preprocessing `157`, and whitespace with
  `python scripts/verify.py --task docs/agent/tasks/2026-08-27-shared-compute-run-canonical-routing.md --changed --types`.
- Known limitations: Batch, Codex, DSC, and GUI persistence migration remain
  follow-up work.
- Pre-existing changes left untouched: permission-protected historical pytest
  directories and all external datasets.
