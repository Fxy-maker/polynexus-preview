---
task_id: 2026-09-04-generic-curve-canonical-execution
kind: architecture
status: implementation_complete_review_required
date: 2026-09-04
title: Execute generic curve modules from their canonical templates
---

## Goal

Make direct TGA and DMA ComputeRuns execute the already validated
CanonicalExperiment rather than reparsing the same raw table inside the
provider engine.

## Non-goals

- Do not migrate existing DSC/IR/NMR/SAXS/WAXS provider lifecycles.
- Do not alter numerical summaries, mapping semantics, or raw data.
- Do not add a separate engine-private template/result object.

## Shared objects and entry points

- Objects: CanonicalExperiment, ComputeRun, AnalysisResult, capability items.
- AI/Codex/CLI: direct runs use the canonical template selected by
  ComputeRunService.
- GUI: its existing ComputeRun worker follows the same route without a
  TGA/DMA-specific UI path.
- Cross-entry rule: a generic curve engine exposes only a template-consuming
  adapter; ComputeRun remains the public producer of the template.

## Affected boundaries

- ComputeRunService provider dispatch and TGA/DMA engine lifecycle adapters.
- No persistence, evidence, figure, or raw artifact contract changes.

## Implementation plan

1. Add a narrow `run_canonical_template` lifecycle to TGA and DMA engines.
2. Prefer that adapter in ComputeRunService when a validated template exists.
3. Prove direct runs do not fall back to raw-table `load()` after canonical
   conversion and preserve the public result projection.
4. Run focused regression and structured verification.

## Acceptance criteria

- [x] A source-bound TGA/DMA canonical template reaches its engine directly.
- [x] `ComputeRunService.run_direct()` does not reparse the raw table for
  these template-aware engines.
- [x] Existing single-file `run_pipeline()` remains a compatibility route.
- [x] CLI/GUI/AI-facing public ComputeRun output remains unchanged in shape.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_tga.py tests/test_dma.py tests/test_compute_service.py tests/test_cli_run_single_service.py
python scripts/verify.py --task docs/agent/tasks/2026-09-04-generic-curve-canonical-execution.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "fix(core): execute generic curves from canonical templates" `
  --files docs/agent/tasks/2026-09-04-generic-curve-canonical-execution.md `
          polynexus/core/compute/service.py polynexus/core/tga.py `
          polynexus/core/dma.py tests/test_tga.py tests/test_dma.py `
          docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes:
  - `python -m pytest -p no:cacheprovider -q tests/test_tga.py tests/test_dma.py tests/test_compute_service.py tests/test_cli_run_single_service.py` — 74 passed, 3 skipped.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-04-generic-curve-canonical-execution.md --changed --types` — passed (Ruff, compile, quality `313 passed`, preprocessing `157 passed`, whitespace).
- Known limitations or follow-up:
  - This narrow adapter currently applies only to the new generic TGA/DMA
    curve providers. Existing mature providers retain their established
    lifecycle adapters until separately migrated and replay-validated.
  - Scientific meaning of TGA/DMA advanced metrics still requires its own
    method, uncertainty, and review work before capability promotion.
- Pre-existing changes left untouched:
  - `polynexus/core/agent_workflow/service.py`, manuscript plans/specs,
    `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/` remain outside this
    checkpoint.
