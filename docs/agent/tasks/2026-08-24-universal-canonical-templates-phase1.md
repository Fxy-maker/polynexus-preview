---
task_id: 2026-08-24-universal-canonical-templates-phase1
kind: architecture
status: active
date: 2026-08-24
title: Add generic one-dimensional canonical conversion
---

## Goal

Convert valid generic IR/SAXS/WAXS CSV/TXT/Excel 1D tables into immutable,
material-neutral canonical measurements with mapping provenance and source
locators.

## Non-goals

- Capability execution.
- Direct-run/GUI/CLI/Batch/Codex migration.
- DSC generalization.
- Numerical algorithm change.
- Legacy deletion.
- Material mapping.
- AI-generated values.
- Real-data mutation.
- Paper workflow.

## Affected boundaries

- `core.canonical_experiments` public contracts and converter.
- Backwards-compatible canonical persistence.
- Consumers untouched.

## Acceptance criteria

- [ ] Canonical measurements preserve immutable order, values, units, locators, and
  source/hash provenance.
- [ ] IR tables convert to `spectrum_1d`.
- [ ] SAXS/WAXS tables convert to `scattering_1d`, including workbook sheets.
- [ ] Unknown units produce a warning.
- [ ] Ambiguous mappings resolve to `needs_input`.
- [ ] A source/table-bound user or AI proposal may resolve ambiguity only after
  validated ambiguity checks.
- [ ] No material routes or legacy routes change.

## Implementation plan

1. Define the generic one-dimensional canonical conversion task boundary and
   acceptance contract.
2. Verify the task card and record an allowlisted local checkpoint.

## Verification

```text
python -m pytest -q -p no:cacheprovider tests/test_canonical_measurements.py tests/test_canonical_one_dimensional.py tests/test_canonical_experiment_templates.py tests/test_dsc_canonical_isothermal_conversion.py
python scripts/verify.py --task docs/agent/tasks/2026-08-24-universal-canonical-templates-phase1.md --changed --types
git diff --check
```
