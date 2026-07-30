---
kind: task
status: completed
date: 2026-07-30
title: Add a SAXS detector provenance structural audit
---

# SAXS Detector Provenance Structural Audit

## Goal

Make existing raw 2D detector geometry and mask provenance structurally
auditable through the existing scientific acceptance audit.

## Non-goals

- No new detector reader, pyFAI calibration, beam-center inference, mask
  inference, or instrument-specific interpretation.
- No new physical or numeric thresholds and no changes to existing SAXS
  calculations, quality gates, publication roles, or rescue behavior.
- No edits to GUI event handlers, real datasets, generated outputs, scratch
  directories, or parallel NMR/Joint files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`: read-only audit
  projection of existing raw detector reports.
- `tests/test_saxs_detector_provenance_structural_audit.py`: focused contract
  and fail-closed regression coverage.
- This task card, its spec, plan, and acceptance record.

## Contract

The acceptance audit adds `detector_provenance_audit`, keyed by
`raw_detector_quality_report`. Each record is detached and strict JSON safe.
It reports only relationships present in the supplied report:

- raw detector source kind and two-dimensional non-empty shape;
- pixel-count coherence;
- required geometry field-source names;
- configured mask shape equality with the detector shape;
- explicit geometry and mask validity values.

`validated` provenance with no structural contradiction yields
`status=structurally_consistent` and level `Trend`. Missing, unknown, or
`not_assessed` validity yields `status=review_required` and level `Diagnostic`.
An explicit `invalid` validity or a structural contradiction yields
`status=unusable` and level `Unusable`. No report is treated as calibrated
merely because it has a header or config source. Sector-map reports do not
receive fabricated raw-detector provenance audit records.

The existing audit `status`, evidence levels, provenance validity, physical
gate evidence, publication fields, and `publication_decision_changed` retain
their current semantics.

## Implementation plan

1. Add RED tests for coherent, unassessed, invalid/mismatched, and sector-map
   inputs, including detached and strict-JSON assertions.
2. Extend the existing recursive acceptance audit with a private structural
   projection helper that copies only supplied report fields.
3. Run focused tests, the exact SAXS matrix, the structured verifier, and
   `git diff --check`.
4. Record acceptance evidence and create one checkpoint using only the
   explicit allowlist below.

## Acceptance criteria

- [x] Coherent validated raw-detector provenance is visible as structural
  consistency without being treated as publication approval.
- [x] Unassessed or missing validity remains `review_required`/`Diagnostic`.
- [x] Invalid validity and shape/count contradictions fail closed as
  `unusable`/`Unusable`.
- [x] Sector-map evidence does not receive fabricated raw-detector audit data.
- [x] Existing audit semantics and source payloads remain unchanged.
- [x] Output is detached and passes strict JSON serialization.
- [x] TDD RED/GREEN, focused tests, exact SAXS matrix, structured verifier,
  diff check, and allowlist checkpoint are recorded.

## Verification

```powershell
python -m pytest -q tests/test_saxs_detector_provenance_structural_audit.py -vv --basetemp D:\PolyNexus_saxs_detector_provenance_structural_audit
python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName) --basetemp D:\PolyNexus_saxs_detector_provenance_structural_audit_saxs_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-detector-provenance-structural-audit.md --changed --types
git diff --check
```

Test-storage report/clean remains separate and dry-run by default. A timeout
or process exit without a complete pytest summary is not a pass.

## Verification evidence

- TDD RED: `4 failed, 1 passed`; the four failures were the expected missing
  `detector_provenance_audit` projection key.
- TDD GREEN: `5 passed in 0.15s`.
- Adjacent 2D/acceptance/transport matrix: `52 passed in 50.35s`.
- Fresh complete SAXS matrix: `626 passed, 6 warnings in 426.09s`.
- Structured verifier passed task validation, memory validation, Ruff,
  compile, type baseline, quality gate `290 passed`, preprocessing gate
  `106 passed`, and whitespace checks.
- `git diff --check`: passed.
- Test-storage report was read-only: `82` artifacts, `17,271,367,037` bytes,
  `eligible_bytes=0`; no `--apply` was run for this task.

The six SAXS warnings are existing Arial glyph warnings and two explicit
real-fixture geometry-default warnings. This task adds no calibration or
scientific acceptance claim. Real detector calibration, mask validity,
orientation meaning, human scientific review, and release approval remain
open external gates.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `tests/test_saxs_detector_provenance_structural_audit.py`
- `docs/superpowers/specs/2026-07-30-saxs-detector-provenance-structural-audit-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-detector-provenance-structural-audit.md`
- `docs/agent/tasks/2026-07-30-saxs-detector-provenance-structural-audit.md`
- `docs/acceptance/2026-07-30-saxs-detector-provenance-structural-audit.md`
