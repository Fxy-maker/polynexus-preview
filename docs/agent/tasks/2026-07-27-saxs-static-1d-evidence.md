# Agent Task

## Goal

Close the static SAXS 1D evidence chain from `SAXSResult` through parameters,
Workbench, History, and Export for both one frame and an unconditioned
multi-file batch.

## Non-goals

- No changes to Guinier/Porod/Kratky/invariant/lamellar algorithms.
- No new physical thresholds, acceptance gates, rescue actions, or AI calls.
- No temperature/strain trend inference from static file ordering.
- No 2D detector/orientation or publication-role changes.
- No cleanup of unrelated pre-existing GUI or temporary workspace changes.

## Context

Relevant existing contracts:

- `polynexus/core/saxs_engine/core.py:SAXSResult` already stores the evidence
  DTOs.
- `polynexus/core/saxs.py:SAXSEngine.get_parameters()` transports temperature
  and strain series evidence but not static evidence.
- `polynexus/core/saxs_batch_helpers.py` builds the existing batch parameter
  payload.
- `polynexus/gui/saxs_results_table_service.py` renders nested evidence and
  review text without running analysis.
- `polynexus/core/saxs_export_bundle.py` writes `quality_evidence.json`.

Design: `docs/superpowers/specs/2026-07-27-saxs-static-1d-evidence-design.md`
Plan: `docs/superpowers/plans/2026-07-27-saxs-static-1d-evidence.md`

## Acceptance criteria

- [x] Static single `get_parameters()` preserves legacy values and transports
      existing `data_quality_report`, `guinier_evidence`, and
      `metric_evidence` without mutation.
- [x] Static batch rows carry evidence only from their aligned result; failed
      frames remain missing.
- [x] Static batch top-level evidence uses the existing conservative summary
      contract and declares `metric_evidence_scope=static_batch`.
- [x] Workbench labels the summary as batch quality and keeps complete nested
      evidence in Diagnostics.
- [x] Existing History persistence round-trips the payload unchanged.
- [x] Static Export preserves single-frame evidence and adds aligned batch
      frame/summary evidence.
- [x] Existing SAXS physical calculations and quality gates remain unchanged.
- [x] Focused tests, SAXS regression tests, task verifier, strict JSON checks,
      and `git diff --check` are run and reported.

## Affected boundaries

- [ ] GUI algorithm logic
- [x] Analysis engine transport
- [x] Result/presentation payload contract
- [x] Persistence through existing parameters path
- [x] Export provenance
- [x] Focused regression tests
- [x] Documentation and agent memory

## Implementation plan

1. Add failing tests for static single transport and static batch alignment.
2. Add the smallest engine/batch-helper transport implementation.
3. Add failing Workbench tests for static-batch wording and Diagnostics.
4. Extend the presentation formatter using the scope metadata.
5. Add failing Export tests for static batch frame/summary evidence.
6. Extend the existing static quality payload without changing its single
   frame shape.
7. Run focused tests, then SAXS matrix and repository verifier.
8. Update durable memory and create one atomic checkpoint with an explicit
   allowlist.

## Verification

```powershell
$taskTempRoot = 'C:\Temp\PolyNexus_saxs_static_1d_evidence'
$env:PYTEST_ADDOPTS = "-o addopts= --basetemp=$taskTempRoot"
pytest tests/test_saxs_batch_parameters.py tests/test_saxs_results_table_service.py tests/test_saxs_export_bundle.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-static-1d-evidence.md --changed --types
git diff --check
```

The complete SAXS regression matrix is also required before handoff. Any
pre-existing failure or lint finding must be reported separately and left
untouched.

## Risks and compatibility

- Nested evidence increases parameters payload size but is bounded by existing
  JSON-safe evidence DTOs.
- Static batch summaries could be misread as trends; the explicit scope field
  and batch-quality wording are mandatory safeguards.
- Legacy numeric rows and Export files remain compatible because new fields are
  additive.

## Memory and review

- [x] Update `docs/agent/memory/current-state.md` and `active-work.md` with the
      final evidence and known limitations.
- [ ] Add a decision entry only if the static batch scope becomes a durable
      cross-module architectural rule.
- [x] Scientific/data-contract review is required before merge.

## Handoff

At completion report changed files, exact verification outputs, known
limitations, and all pre-existing workspace changes intentionally left alone.

## Verification result

- TDD RED was observed for missing helper symbols, static parameter transport,
  scoped Workbench wording, and static batch Export provenance.
- Static evidence/Workbench/History/Export focused matrix: `77 passed`.
- Complete SAXS matrix: `290 passed, 4 existing font warnings`.
- Task-scoped verifier: passed task-card validation, durable-memory validation,
  changed-file Ruff, compile, type baseline, quality gate `282`, preprocessing
  gate `106`, and selected checks.
- `git diff --check`: passed.
- Strict static batch Export JSON assertions passed with no `NaN` or `Infinity`.

## Changed-file allowlist

- `polynexus/core/saxs.py`
- `polynexus/core/saxs_batch_helpers.py`
- `polynexus/core/saxs_export_bundle.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_batch_parameters.py`
- `tests/test_saxs_export_bundle.py`
- `tests/test_saxs_workbench_series_evidence.py`
- `docs/agent/tasks/2026-07-27-saxs-static-1d-evidence.md`
- `docs/superpowers/specs/2026-07-27-saxs-static-1d-evidence-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-static-1d-evidence.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`
