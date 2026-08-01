---
task_id: 2026-08-01-saxs-ai-reference-evidence-transport
kind: scientific-cross-module
status: completed
date: 2026-08-01
title: Transport SAXS AI candidate-reference evidence to consumers
---

# SAXS AI candidate-reference evidence transport

## Goal

Expose the existing diagnostic AI candidate-reference resolution consistently
through SAXS Workbench, Figure/Manifest, and Export evidence surfaces.

## Non-goals

- no new scientific formula, threshold, quality level, physical gate, or rescue
  algorithm;
- no candidate execution, validation, interpolation, frame repair, or config
  mutation;
- no prompt, Advisor normalization, RoundRecord schema, Figure role, Manifest
  lifecycle, or publication-policy change;
- no raw q/I, detector pixels, source paths, real fixtures, generated outputs,
  memory, scratch, or test-storage cleanup change;
- no `scripts/test_storage.py --apply`.

## Affected boundaries

- `polynexus/orchestrator_run_round.py`: attach latest detached resolution to
  current SAXS engine/result state after the existing resolver;
- `polynexus/core/saxs_batch_helpers.py`: reuse the existing AI evidence copy
  channel used by SAXS `get_parameters()`;
- `polynexus/core/saxs_engine/figure_evidence.py`: compact Figure/Manifest
  provenance projection;
- `polynexus/core/saxs_export_bundle.py`: Export quality evidence projection;
- `polynexus/gui/saxs_results_table_service.py`: Workbench advisory text;
- focused consumer tests and this task's spec/plan/acceptance note.

## Implementation plan

1. Add RED coverage for shared SAXS evidence copying, Workbench advisory text,
   compact Figure/Manifest provenance, Export quality evidence, and latest
   orchestrator state attachment.
2. Attach the resolver's detached latest record to the active SAXS engine and
   result through the existing AI evidence channel without executing candidates
   or changing scientific gates.
3. Project only diagnostic identity fields into Workbench and Figure surfaces;
   retain the full detached record under Export `ai_rescue` evidence.
4. Run focused consumer, resolver, Advisor/prompt, and acceptance-context
   regressions, then run the SAXS matrix and task-scoped verifier.
5. Record the temperature/strain contract correction: temperature asserts
   `guinier_sequence_evidence`; strain asserts `metric_evidence.guinier`.
6. Run storage report/clean dry-runs, audit the explicit allowlist, and create
   one checkpoint only for this task's changed files.

## Verification

```powershell
python -m pytest -q tests/test_saxs_workbench_series_evidence.py tests/test_saxs_figure_evidence_binding.py tests/test_saxs_export_bundle.py tests/test_saxs_orchestrator_loop.py tests/test_saxs_ai_rescue_bridge.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_acceptance_audit_context.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-reference-evidence-transport.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

The first command completed with `104 passed in 20.94s`. The fresh full SAXS
matrix was attempted twice; the first run exited `124` after 124 seconds and
the second exited `124` after 604 seconds without a pytest summary, so neither
run is counted as a pass. Storage commands remain dry-run only.

## Scientific boundary

The resolution proves only that an AI-referenced ID matches an existing
deterministic candidate. `validation_required`, current physical metrics,
quality levels, sequence integrity, and publication gates remain authoritative.
Workbench and Figure projections never display proposed candidate parameters.

## Acceptance criteria

- [x] Current latest resolution reaches shared SAXS parameters and Workbench.
- [x] Figure provenance and Manifest-backed figure documents retain compact,
      strict-JSON diagnostic identity without changing roles.
- [x] Export quality evidence retains the detached full resolution under the
      existing `ai_rescue` section.
- [x] Empty/malformed/non-SAXS paths remain fail-closed and non-fatal.
- [x] Focused RED/GREEN, SAXS matrix, structured verifier, storage dry-runs,
      diff audit, acceptance note, and explicit allowlist checkpoint are recorded.

## TDD evidence

- RED: the four new consumer tests failed as expected (`4 failed`): shared copy
  lacked the field, Workbench produced no advisory text, Figure lacked the
  compact projection, and Export lacked the `ai_rescue` section.
- GREEN: fresh focused consumer/resolver/orchestrator/Advisor/prompt/context
  regression passed (`104 passed in 20.94s`). The temperature Figure assertion
  uses `guinier_sequence_evidence`; the strain assertion uses
  `metric_evidence.guinier`, matching their existing contracts.
- Structured verifier passed: task-check valid, Ruff, compile, quality gate
  (`297 passed`), preprocessing gate (`106 passed`), and whitespace check.
- Fresh isolated full SAXS matrix passed: `744 passed, 6 warnings in
  704.21s`, exit code `0`. The warnings are existing font and EDF geometry
  default warnings; no test failed.
- Storage report/clean were dry-run only: `162` artifacts, `eligible_bytes=0`,
  clean `removed=0`, `failures=0`. No `--apply` was run.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_workbench_series_evidence.py tests/test_saxs_figure_evidence_binding.py tests/test_saxs_export_bundle.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts= --basetemp=D:\PolyNexus_saxs_reference_transport_matrix_20260801
python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-reference-evidence-transport.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Only complete pytest summaries with exit code `0` count as pass evidence. The
isolated full matrix completed with `744 passed, 6 warnings` in `704.21s`.
Storage commands are dry-run only.

## Explicit changed-file allowlist

- `polynexus/orchestrator_run_round.py`
- `polynexus/core/saxs_batch_helpers.py`
- `polynexus/core/saxs_engine/figure_evidence.py`
- `polynexus/core/saxs_export_bundle.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_workbench_series_evidence.py`
- `tests/test_saxs_figure_evidence_binding.py`
- `tests/test_saxs_export_bundle.py`
- `tests/test_saxs_orchestrator_loop.py`
- `docs/superpowers/specs/2026-08-01-saxs-ai-reference-evidence-transport-design.md`
- `docs/superpowers/plans/2026-08-01-saxs-ai-reference-evidence-transport.md`
- `docs/agent/tasks/2026-08-01-saxs-ai-reference-evidence-transport.md`
- `docs/acceptance/2026-08-01-saxs-ai-reference-evidence-transport.md`

Parallel memory, GUI review-hint, real-data, generated-output, scratch, and
test-storage changes remain outside this checkpoint.
