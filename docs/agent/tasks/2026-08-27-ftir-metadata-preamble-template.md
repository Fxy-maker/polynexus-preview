---
task_id: 2026-08-27-ftir-metadata-preamble-template
kind: scientific
status: implementation_complete_review_required
date: 2026-08-27
title: Parse vendor FTIR metadata preamble in universal template
---

# Parse vendor FTIR metadata preamble in universal template

## Goal

Allow the universal one-dimensional canonical converter to consume the real
FTIR CSV layout whose axis labels and instrument metadata precede numeric rows.

## Non-goals

- No provider algorithm or scientific preprocessing changes.
- No raw-data modification or vendor-specific binary reader.
- No publication-role assignment.

## Shared objects and entry points

- Producer: `convert_one_dimensional_table` and `CanonicalExperiment`.
- Consumers: `ComputeRunService`, project workflow, Batch, GUI, and Agent/Codex
  routes that already use the shared converter.

## Acceptance criteria

- [x] `XLabel,Wavenumber` and `YLabel,Absorbance` rows are recognized as a
  deterministic metadata preamble.
- [x] Non-axis metadata rows before the numeric curve are skipped.
- [x] Mapping and source locators retain the physical header/data row numbers.
- [x] Existing ordinary CSV, commented CSV, workbook, and ambiguity behavior
  remains unchanged.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_canonical_one_dimensional.py
python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_cli_run_single_service.py tests/test_cli_batch_run_service.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-ftir-metadata-preamble-template.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "fix(canonical): parse FTIR metadata preambles" `
  --files docs/agent/tasks/2026-08-27-ftir-metadata-preamble-template.md polynexus/core/canonical_experiments/one_dimensional.py tests/test_canonical_one_dimensional.py
```

## Known limitations

The converter recognizes this tabular FTIR family only when both axis-label
metadata rows are present and at least one finite numeric pair follows. Other
vendor layouts remain subject to the existing mapping proposal boundary.
