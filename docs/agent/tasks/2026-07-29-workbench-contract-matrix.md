---
task_id: 2026-07-29-workbench-contract-matrix
kind: release-verification-audit
status: completed
---

# Results Workbench and Figure contract matrix

## Goal

Re-run the shared and technique-specific Workbench/profile/Figure contract
tests to verify that the requested mode-specific presentation and publication
boundaries remain connected across the current checkout.

## Non-goals

- Do not infer scientific validity or publication readiness from contracts.
- Do not change production code, real datasets, or generated outputs.
- Do not delete or migrate test-storage artifacts.

## Affected boundaries

- Results Workbench profiles and shared cross-technique figure pipeline.
- SAXS series/figure contracts.
- DSC and WAXS Workbench figure contracts.
- IR/NMR/Joint Workbench profiles.

## Implementation plan

1. Run all listed Workbench/profile/Figure contract suites with D: basetemp.
2. Capture the complete pytest summary and exit code.
3. Record the automated scope and the remaining human/scientific gates.

## Acceptance criteria

- [x] Shared Results Workbench profile contracts pass.
- [x] SAXS, DSC, WAXS, IR, NMR, Joint, and cross-technique figure contracts pass.
- [x] The command has a complete summary and exit code.
- [x] Human scientific and restarted-GUI review remain explicit limitations.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_workbench_contract_matrix_20260729'
python -m pytest -q tests/test_results_workbench_profiles.py tests/test_saxs_workbench_figure_contracts.py tests/test_saxs_workbench_series_evidence.py tests/test_dsc_workbench_figure_contracts.py tests/test_waxs_workbench_figure_contracts.py tests/test_ir_nmr_joint_workbench_profiles.py tests/test_cross_technique_figure_pipeline.py
# 57 passed in 10.33s
# WORKBENCH_CONTRACT_EXIT_CODE=0

python scripts/verify.py --task docs/agent/tasks/2026-07-29-workbench-contract-matrix.md --changed --types
git diff --check
```

## Limitations

This proves software contracts, not scientific interpretation, mapping/ROI
semantics, solid-C assignment, Joint conflicts, restarted-GUI visual approval,
or final release authorization. No test data was deleted or migrated.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-29-workbench-contract-matrix.md`
- `docs/acceptance/2026-07-29-workbench-contract-matrix.md`
- `docs/agent/memory/active-work.md`
