---
task_id: 2026-08-29-method-sensitivity-public-contract
kind: scientific
status: active
date: 2026-08-29
title: Publish explicit method-sensitivity candidates
---

# Publish explicit method-sensitivity candidates

## Goal

Expose deterministic primary/candidate method values through the same
ComputeRun and ARS writing projections used by ordinary metrics.

## Non-goals

- Do not infer a candidate from a material name or a scalar value.
- Do not choose a publication method automatically.
- Do not change provider algorithms, thresholds, templates, or raw data.

## Contract

Providers may publish a legacy-result `method_sensitivities` attribute or an
explicit `metrics.method_variants`/`metrics.method_sensitivities` mapping. DSC's existing `baseline_variants` are
adapted recursively. The shared DTO records primary method, candidates,
difference range, parameters, source, and warnings. ARS receives all values as
diagnostic observations until a human/AI workflow makes an explicit decision.

## Affected boundaries

- `AnalysisResult`, `ComputeResult`, and `ComputeRun` shared result objects.
- Project result-table and ARS writing-metric projections.
- FTIR, SAXS, WAXS, NMR, and DSC providers that publish explicit candidates.

## Implementation plan

1. Add a deterministic evaluator and normalize explicit provider candidate
   payloads into `MethodSensitivity`.
2. Persist normalized values and artifact source through `ComputeRun`.
3. Expose candidate values to ARS writing metrics as diagnostic observations.
4. Verify focused consumers and task-level repository checks.

## Acceptance criteria

- [x] Explicit candidate methods are evaluated in stable order and failures are
  retained as warnings.
- [x] `AnalysisResult` and `ComputeResult` expose the same sensitivity DTO.
- [x] DSC baseline variants are adapted recursively without inference.
- [x] ComputeRun fills a missing sensitivity source from its artifact path.
- [x] ARS writing metrics receive primary and candidate values as diagnostics.
- [x] Evidence packages include the shared `result-tables.json` projection and
  manifest link.
- [x] Technique-specific providers remain opt-in: candidates are published only
  after scientific review, and this contract task changes no provider algorithm.

## Verification

```powershell
pytest -q tests/test_method_sensitivity.py tests/test_compute_models.py tests/test_project_writing_metrics.py
python scripts/verify.py --task docs/agent/tasks/2026-08-29-method-sensitivity-public-contract.md --changed --types
git diff --check
```

## Follow-up

Wire technique-specific candidate calculators only when a provider publishes a
deterministic candidate payload; no fallback or material-specific default is
allowed at this boundary.
