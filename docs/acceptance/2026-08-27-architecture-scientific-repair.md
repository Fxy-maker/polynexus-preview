# Architecture and scientific repair acceptance

Date: 2026-08-27
Task: `docs/agent/tasks/2026-08-27-architecture-scientific-repair.md`

## Scope

This checkpoint repairs three merge-blocking findings from the architecture
and scientific review. It does not change raw inputs or provider algorithms.

## Changes verified

- Directory conversion hashes now use the same canonical
  `{"kind":"directory_manifest","entries":[...]}` envelope as `RawArtifact`.
- Evidence packaging rejects a step with a missing/incomplete `ComputeRun`, an
  artifact identity/hash mismatch, a template bound to another artifact, or a
  step/recipe mismatch.
- DSC Avrami citation projection keeps finite observations but marks segments
  with quality flags (including low R² and segment-boundary starts) as
  `diagnostic_only`; equivalent `best_avrami` records are not duplicated.
- FTIR, SAXS, and WAXS eligibility rules were not changed.

## Verification

```text
python -m pytest -q tests/test_directory_manifest_hash.py tests/test_project_workflow_package.py tests/test_project_workflow_adapters.py tests/test_evidence_package_view.py
47 passed

python -m pytest -q tests/test_analysis_evidence.py tests/test_dsc_publication_isothermal_provider.py tests/eval/test_dsc_publication_real_data.py -k "dsc or metric or writing"
27 passed, 121 deselected
```

The focused package and scientific matrices pass. Full repository release
verification remains outside this atomic repair and still has the historical
GUI/chart/SAXS failures recorded in project memory.

## Remaining limitations

Package portability/self-containment, Batch persistence projection, mixed
technology plan routing, GUI figure filtering, and generic capability coverage
remain follow-up work. Architecture and scientific boundaries still require
human review before merge.
