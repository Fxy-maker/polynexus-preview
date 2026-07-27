# Task: SAXS Workbench detector evidence visibility

**Status:** checkpointed

## Goal

Expose existing raw-detector and sector-map quality evidence in the Results
Workbench review channels without changing scientific semantics.

## Affected boundaries

- `polynexus/gui/saxs_results_table_service.py`: presentation-only summary.
- `tests/test_saxs_results_table_service.py`: focused regressions.
- Existing parameter, History, Figure, and Export transport remains unchanged.

## Non-goals

- No detector recalculation, geometry calibration, mask inference, or new
  physical/quality threshold.
- No level promotion, rescue, AI action, Figure-role change, or publication
  authorization.
- No edits to real datasets, generated outputs, GUI scratch, or parallel files.

## Acceptance criteria

- [x] Raw-detector and sector-map reports are displayed as separate evidence
  sources with their existing levels and source kinds.
- [x] Existing frame/evidence counts, coverage, and reason codes are shown only
  as read-only diagnostic context; partial or unusable reports produce an
  advisory review/next-step message.
- [x] Missing reports produce no detector-specific Workbench text.
- [x] English and Chinese output is deterministic, and input mappings are not
  mutated.
- [x] Existing quality levels, physical gates, Figure/Manifest, History, Export,
  and AI/rescue behavior remain unchanged.

## Implementation plan

1. [x] Add focused RED tests for the formatter and Workbench integration.
2. [x] Implement the smallest presentation-only formatter and combine its text with
   existing metric/axis/sequence review text.
3. [x] Run the focused Workbench/SAXS consumer matrix and exact SAXS matrix.
4. [x] Run the structured verifier, inspect the diff/allowlist, and create the
   explicit checkpoint with `scripts/auto_commit.py`.

## Verification

Required commands:

```powershell
python -m pytest -q tests/test_saxs_results_table_service.py -vv --basetemp C:\Temp\PolyNexus_saxs_workbench_detector_redgreen
python -m pytest -q tests/test_saxs_results_table_service.py tests/test_saxs_export_bundle.py tests/test_saxs_figure_evidence_binding.py -vv --basetemp C:\Temp\PolyNexus_saxs_workbench_detector_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-workbench-detector-evidence-visibility.md --changed --types
git diff --check
```

An unfinished full/boundary run is not counted as evidence for this task.

## Verification record

- TDD RED: `3 failed, 44 deselected`; every failure was the expected absence of
  detector evidence text in the existing Workbench presentation.
- TDD GREEN: detector-focused tests passed `3 passed, 44 deselected`.
- Consumer matrix: `64 passed` for the Workbench, Export, and Figure evidence
  tests.
- Exact SAXS matrix: `374 passed, 5 warnings` in `32.91s` using external
  basetemp `C:\Temp\PolyNexus_saxs_workbench_detector_saxs_matrix`. Warnings
  are existing Arial CJK glyph warnings plus the existing missing-geometry
  warning from the raw-detector transport test.
- Structured verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-workbench-detector-evidence-visibility.md --changed --types`
  exited `0`; task/memory, Ruff, compile/type baseline, quality `283`,
  preprocessing `106`, and whitespace checks passed. The verifier used
  external basetemp `C:\Temp\PolyNexus_saxs_workbench_detector_verify_final`.
- `git diff --check` exited `0` through the structured verifier. The explicit
  allowlist checkpoint was created by `scripts/auto_commit.py`; no push was
  performed and no parallel GUI/editor/scratch files were included.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-28-saxs-workbench-detector-evidence-visibility.md`
- `docs/superpowers/specs/2026-07-28-saxs-workbench-detector-evidence-visibility-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-workbench-detector-evidence-visibility.md`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_results_table_service.py`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`

## Scientific limitation

Workbench text is provenance and review context only. Detector geometry,
beam-center meaning, mask scientific validity, saturation interpretation, and
publication approval still require human review against the instrument and raw
data.
