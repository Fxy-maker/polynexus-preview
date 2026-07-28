---
kind: task
status: completed
date: 2026-07-28
title: Carry SAXS scientific acceptance audit across review and export surfaces
---

# SAXS acceptance audit surfaces

## Goal

Carry the existing read-only `scientific_acceptance_audit` snapshot from SAXS
parameters into Workbench review text, Figure/Manifest provenance, and the
bundle-level `quality_evidence.json` export.

## Non-goals

- Do not add or change SAXS physical metrics, quality thresholds, publication
  roles, rescue behavior, AI execution, interpolation, or frame alignment.
- Do not recalculate an audit in a consumer when an existing snapshot is
  absent; missing audit remains absent and diagnostic consumers fail closed.
- Do not duplicate the full quality evidence database inside each figure.
- Do not change the existing Figure/Manifest schema outside the nested
  `quality_provenance` evidence mapping or the existing quality export object.

## Affected boundaries

- `polynexus/gui/saxs_results_table_service.py`: presentation-only audit text;
- `polynexus/core/saxs_engine/figure_evidence.py` and providers: detached
  audit attachment under existing `quality_provenance`;
- `polynexus/core/saxs_export_bundle.py`: top-level audit in existing quality
  evidence export;
- focused surface tests and durable task/spec/plan/acceptance records.

## Acceptance criteria

- [x] Workbench reports existing audit status/reasons as advisory review text
  without mutating the parameter payload.
- [x] Figure definitions carry the same strict-JSON audit snapshot under
  `recipe.evidence.quality_provenance` without changing roles or figure IDs.
- [x] `quality_evidence.json` carries the same audit snapshot when parameters
  already expose it; missing audit is not invented.
- [x] Static, temperature, and strain consumers preserve the audit shape and
  existing diagnostic-only/publication boundaries.
- [x] TDD RED/GREEN, focused surface tests, SAXS matrix, task verifier, diff
  check, test-storage report, and explicit allowlist checkpoint are recorded.

## Implementation plan

1. Add focused RED tests for Workbench, Figure provenance, Export, strict JSON,
   immutability, and absent-audit fail-closed behavior.
2. Add the minimal consumer attachment/presentation logic using only the
   existing snapshot; preserve all existing evidence and publication fields.
3. Run GREEN, exact SAXS matrix, structured verifier, diff and test-storage
   audit; update durable records and create one explicit checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_acceptance_audit_surfaces.py -vv --basetemp C:\Temp\PolyNexus_saxs_acceptance_audit_surfaces
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp C:\Temp\PolyNexus_saxs_acceptance_audit_surfaces_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-acceptance-audit-surfaces.md --changed --types
git diff --check
python scripts/test_storage.py report --json
```

## Explicit changed-file allowlist

- `polynexus/gui/saxs_results_table_service.py`
- `polynexus/core/saxs_engine/figure_evidence.py`
- `polynexus/core/saxs_engine/figure_provider.py`
- `polynexus/core/saxs_engine/figure_static.py`
- `polynexus/core/saxs_engine/figure_temperature.py`
- `polynexus/core/saxs_engine/figure_strain.py`
- `polynexus/core/saxs_export_bundle.py`
- `tests/test_saxs_acceptance_audit_surfaces.py`
- `tests/test_saxs_figure_evidence_binding.py`
- this task card
- `docs/superpowers/specs/2026-07-28-saxs-acceptance-audit-surfaces-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-acceptance-audit-surfaces.md`
- `docs/acceptance/2026-07-28-saxs-acceptance-audit-surfaces.md`
- `docs/agent/memory/active-work.md`

## Checkpoint

Create one local `scripts/auto_commit.py` checkpoint after all current
verification evidence is recorded. Do not include `current-state.md`, parallel
GUI/Joint/editor changes, real datasets, or scratch outputs.

## Verification evidence

- Final TDD RED after fixture correction: `3 failed, 1 passed`; failures were
  the missing Workbench, Figure, and Export bindings.
- Focused GREEN: `4 passed in 0.18s`.
- Surface/provider matrix: `15 passed in 4.46s`.
- Exact SAXS matrix: `449 passed, 6 warnings in 154.00s`; warnings are the
  existing font and EDF geometry-default warnings.
- Structured verifier exited `0`: task/memory, Ruff, compile, type baseline,
  quality `287 passed`, preprocessing `106 passed`, and whitespace all passed.
- Independent `git diff --check` passed through the structured quality gate.
- `python scripts/test_storage.py report --json` completed in dry-run mode;
  the task used external basetemp directories and no cleanup/deletion was
  performed.
- Full/boundary verification was not run for this atomic task and is not
  claimed.

## Boundary

This is additive audit transport and advisory presentation only. It does not
approve SAXS physical interpretation, figure eligibility, publication roles,
AI rescue, or final scientific/release review.
