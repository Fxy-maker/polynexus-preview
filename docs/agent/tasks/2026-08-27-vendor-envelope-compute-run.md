---
task_id: 2026-08-27-vendor-envelope-compute-run
kind: architecture
status: implementation_complete_review_required
date: 2026-08-27
title: Retain vendor canonical envelopes on ComputeRun
---

# Retain vendor canonical envelopes on ComputeRun

## Goal

Keep the registry-produced canonical envelope visible on every completed
vendor-format `ComputeRun`, while preserving legacy provider execution and
leaving finite capability items empty when no canonical measurements exist.

## Non-goals

- No vendor parser or provider algorithm changes.
- No raw-data or persistence migration.
- No capability fabrication from opaque vendor bytes.

## Shared objects and entry points

- Producer: `CanonicalConverterRegistry` and `ComputeRunService`.
- Consumers: Quick Analysis, single-file CLI, Batch, GUI persistence, and
  Agent/Codex workflow projections.

## Affected boundaries

- `polynexus/core/compute/service.py` canonical-template attachment.
- `tests/test_compute_service.py` vendor envelope regression coverage.
- Existing provider compatibility execution remains unchanged.

## Implementation plan

1. Add a failing test requiring a ready vendor envelope to remain on
   `ComputeRun` while capability items stay empty.
2. Attach every ready registry template in `ComputeRunService`, executing
   capabilities only when measurements are present.
3. Run shared producer and consumer tests plus the structured verifier.

## Acceptance criteria

- [x] A ready static envelope (`ir.spectrum.v1`, `saxs.profile.v1`, or
  `waxs.profile.v1`) is attached to the completed or failed `ComputeRun`.
- [x] Vendor providers still execute through their existing compatibility path.
- [x] No capability items are emitted without canonical measurements.
- [x] Ambiguous generic tables still block before provider execution.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_compute_models.py tests/test_cli_run_single_service.py tests/test_cli_batch_run_service.py tests/test_agent_workflow_contracts.py tests/test_project_workflow_adapters.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-vendor-envelope-compute-run.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(compute): retain vendor canonical envelopes" `
  --files docs/agent/tasks/2026-08-27-vendor-envelope-compute-run.md polynexus/core/compute/service.py tests/test_compute_service.py
```
