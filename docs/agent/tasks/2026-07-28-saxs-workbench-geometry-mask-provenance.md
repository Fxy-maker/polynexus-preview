# Task: SAXS Workbench geometry and mask provenance visibility

**Status:** checkpointed (fresh verification complete; checkpoint hash is reported in handoff)

## Goal

Expose the already-transported raw-detector geometry and mask provenance in the
Results Workbench as a read-only diagnostic summary.

## Affected boundaries

- `polynexus/gui/saxs_results_table_service.py`: presentation-only formatter.
- `tests/test_saxs_results_table_service.py`: focused regression coverage.
- `docs/agent/memory/`: durable route state.

## Non-goals

- No detector re-analysis, geometry calibration, mask inference, or scientific
  validity judgment.
- No new threshold, quality-level promotion, rescue, AI action, Figure role,
  publication eligibility, or persistence schema change.
- No merging raw detector and sector-map reports, no sorting frames, and no
  edits to GUI event handlers or parallel scratch files.

## Acceptance criteria

- [x] Raw-detector Workbench review text shows geometry aggregate source and
  field-source counts when provenance exists.
- [x] Raw-detector Workbench review text shows mask source/configured state and
  shape when provenance exists.
- [x] `validity=not_assessed` is presented as a limitation, never as approval or
  failure; existing level/reason/coverage text remains unchanged.
- [x] Missing provenance produces no new geometry/mask text; sector-map evidence
  remains separate and gains no raw provenance claims.
- [x] English/Chinese output is deterministic and input mappings are not
  mutated.
- [x] Focused Workbench, SAXS consumer, task verifier, and explicit checkpoint
  evidence are recorded.

## Implementation plan

1. [x] Add RED tests for complete, mixed, absent, and unconfigured provenance.
2. [x] Add a small presentation-only formatter that reads existing mappings and
   reports source/count/configuration facts without interpreting them.
3. [x] Compose the formatter into the existing detector review text.
4. [x] Run focused and consumer tests, task verifier, diff/allowlist review, and
   create one explicit checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_results_table_service.py -k detector --basetemp C:\Temp\PolyNexus_saxs_workbench_geometry_mask_redgreen
python -m pytest -q tests/test_saxs_results_table_service.py tests/test_saxs_figure_evidence_binding.py tests/test_saxs_export_bundle.py --basetemp C:\Temp\PolyNexus_saxs_workbench_geometry_mask_consumers
$taskPytestOptions = '--basetemp=C:\Temp\PolyNexus_saxs_workbench_geometry_mask_verify'; $env:PYTEST_ADDOPTS = $taskPytestOptions; python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-workbench-geometry-mask-provenance.md --changed --types; Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
git diff --check
```

The repository `.pytest_tmp` directory is known to be protected by unrelated
long-running GUI/pytest processes; an external basetemp is authoritative when
that lock is present.

## Verification record

- TDD RED: `3 failed, 3 passed, 44 deselected`; failures were the expected
  missing Workbench provenance fragments.
- TDD GREEN: detector-focused Workbench tests `6 passed, 44 deselected`.
- Workbench/Export/Figure consumer matrix: `67 passed`.
- Exact SAXS matrix: `380 passed, 6 warnings` using external basetemp
  `C:\Temp\PolyNexus_saxs_workbench_geometry_mask_saxs_matrix`.
- Focused Ruff, compile, and `git diff --check` passed.
- Task-scoped verifier with external basetemp exited `0`; task/memory,
  Ruff/compile/type, quality `283 passed`, preprocessing `106 passed`, and
  whitespace all passed.

## Checkpoint

The explicit allowlist checkpoint is created with `scripts/auto_commit.py` after
this record is finalized. No push or merge is performed.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-28-saxs-workbench-geometry-mask-provenance.md`
- `docs/superpowers/specs/2026-07-28-saxs-workbench-geometry-mask-provenance-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-workbench-geometry-mask-provenance.md`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_results_table_service.py`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`

## Scientific limitation

Workbench text is provenance and review context only. Geometry calibration,
beam-center meaning, mask scientific validity, saturation interpretation, and
release approval remain human scientific gates.
