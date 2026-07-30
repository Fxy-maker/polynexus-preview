---
kind: task
status: completed
date: 2026-07-30
title: Show SAXS detector provenance audit in Workbench
---

# SAXS Workbench Detector Provenance Audit

## Goal

Expose existing raw-detector geometry and mask structural-audit evidence in
the SAXS Workbench review channels.

## Non-goals

- No changes to detector analysis, calibration, mask inference, geometry
  thresholds, orientation calculations, quality gates, rescue, or publication
  roles.
- No edits to Figure/Manifest/Export consumers because they already carry the
  complete acceptance audit.
- No GUI event-handler branching or changes to parallel NMR/Joint files.

## Affected boundaries

- `polynexus/gui/saxs_results_table_service.py`: presentation-only review text.
- `tests/test_saxs_workbench_detector_provenance_audit.py`: focused regression.
- This task card, spec, plan, and acceptance record.

## Contract

Read `scientific_acceptance_audit.detector_provenance_audit`, whose raw
detector records contain `status`, `level`, `geometry`, `mask`, and
`reason_codes`. For each valid record, display status/level and the supplied
geometry/mask validity values. `review_required` and `unusable` are risk
evidence; `structurally_consistent` is not a risk. Every displayed record
adds a next-step statement that this is structural evidence only and does not
establish calibration or physical acceptance.

Ignore malformed records and absent audit mappings. Do not synthesize a
record from `provenance_validity`, `raw_detector_quality_report`, or Figure
rendering. Keep detector provenance separate from generic 1D metric review
text and preserve the input mapping.

## Implementation plan

1. Add RED tests for review-required, unusable, and structurally-consistent
   audit records, plus malformed and immutability boundaries.
2. Implement one presentation helper and add its risk/next sections to the
   existing SAXS Workbench composition.
3. Run focused Workbench tests, the relevant SAXS consumer matrix, task
   verifier, and diff hygiene checks.
4. Record acceptance evidence and create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] Workbench shows detector provenance status, level, geometry/mask
  validity, and reasons.
- [x] Review-required/unusable states are visible as risk; consistent state
  is not falsely presented as a risk.
- [x] Next-step text explicitly preserves the calibration/physical-review
  boundary.
- [x] Malformed/absent input is ignored and generic 1D metric text is
  unchanged.
- [x] Input is not mutated and all focused/consumer/task checks pass.

## Verification

```powershell
python -m pytest -q tests/test_saxs_workbench_detector_provenance_audit.py --basetemp D:\PolyNexus_saxs_workbench_detector_provenance_audit
python -m pytest -q tests/test_saxs_workbench_series_evidence.py tests/test_saxs_2d_review_consumer_propagation.py tests/test_saxs_2d_review_evidence_binding.py --basetemp D:\PolyNexus_saxs_workbench_detector_provenance_audit_consumers
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-workbench-detector-provenance-audit.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_workbench_detector_provenance_audit.py`
- `docs/superpowers/specs/2026-07-30-saxs-workbench-detector-provenance-audit-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-workbench-detector-provenance-audit.md`
- `docs/agent/tasks/2026-07-30-saxs-workbench-detector-provenance-audit.md`
- `docs/acceptance/2026-07-30-saxs-workbench-detector-provenance-audit.md`
