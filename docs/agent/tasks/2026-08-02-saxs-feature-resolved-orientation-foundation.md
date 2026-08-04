---
task_id: 2026-08-02-saxs-feature-resolved-orientation-foundation
kind: scientific
status: design_review
date: 2026-08-02
title: Establish the SAXS feature-resolved orientation foundation
---

# SAXS Feature-Resolved Orientation Foundation

## Goal

Implement the first milestone of the approved SAXS physical-core roadmap:
establish explicit orientation-axis and Herman-convention evidence, preserve
per-bin support through `chi x q` integration, and separate raw detector,
sector map, selected annulus, and radial 1D quality domains.

## Non-goals

- Do not implement continuous multi-q feature detection in this task.
- Do not classify low-q anisotropy as lamellar, chain, or void orientation.
- Do not alter the detector-plane Herman formula or tune thresholds.
- Do not infer a tensile axis from the observed scattering pattern.
- Do not add GUI-side algorithm logic, AI overrides, or publication promotion.
- Do not modify real EDF files, parallel memory changes, or generated outputs.

## Affected boundaries

- `polynexus/core/saxs_engine/preprocess.py`: return support-aware sector-map
  data from NumPy and pyFAI integration paths.
- `polynexus/core/saxs_engine/saxs_anisotropy.py`: consume annulus support and
  emit explicit axis/convention evidence.
- `polynexus/core/saxs_engine/saxs_quality_contracts.py`: serialize detached
  sector/annulus quality and feature-orientation evidence.
- `polynexus/core/saxs_engine/saxs_strain.py`: transport the new evidence and
  keep table-level tensile Herman unavailable without an explicit tensile axis.
- Focused synthetic and read-only real-EDF tests.

## Implementation plan

1. Add RED tests for sector-map occupancy, empty-bin classification, explicit
   versus missing tensile axes, and separation of annulus and radial-1D quality.
2. Introduce the named support-aware sector-map core result and populate it in
   the NumPy and pyFAI integration paths without deriving support from intensity.
3. Add detached orientation-feature and annulus-quality evidence with explicit
   axis, convention, q-range, support, reliability, and reason semantics.
4. Route strain analysis through the new evidence while retaining backward
   readability of legacy raw/effective Herman fields and keeping GUI consumers
   algorithm-free.
5. Run focused synthetic tests, read-only `610` EDF acceptance, the complete
   SAXS matrix, and the structured verifier; review the cumulative diff and
   create one explicit-allowlist checkpoint.

## Acceptance criteria

- [ ] Sector integration retains per-bin valid source-pixel counts and an empty
  bin mask without deriving occupancy from intensity values.
- [ ] NumPy and pyFAI paths expose equivalent support semantics or fail closed
  with `sector_support_unavailable`.
- [ ] Empty sector bins do not create raw-detector `nonpositive_pixels` reasons.
- [ ] Orientation evidence identifies feature/q range, convention, principal
  scattering axis, reference axis, support, reliability, and reason codes.
- [ ] Missing tensile-axis evidence leaves the final tensile Herman value
  unavailable while retaining principal-axis diagnostics.
- [ ] Global 1D low-q defects do not automatically veto a supported annulus;
  applicable blockers identify their quality domain.
- [ ] Existing legacy raw/effective Herman evidence remains readable and is not
  silently reinterpreted.
- [ ] Synthetic support/axis tests and the read-only `610` EDF acceptance pass.
- [ ] The complete SAXS matrix and structured verifier pass before checkpoint.

## Verification

Planned commands:

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_batch_parameters.py -q
python -m pytest -p no:cacheprovider tests/test_saxs_*orientation*.py tests/test_saxs_*detector*.py tests/test_saxs_*strain*.py -q
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-08-02-saxs-feature-resolved-orientation-foundation.md --changed --types
git diff --check
```

The real EDF test must remain read-only and skip with an explicit reason when
the external dataset is unavailable. No generated result is written beside the
source EDF files.

## Explicit changed-file allowlist

The implementation checkpoint is expected to include only the approved design,
this task card, the four core boundaries listed above, and focused SAXS tests.
The exact test-file allowlist will be fixed after the written spec is approved
and before implementation begins.

## Pre-existing workspace changes

The tracked `docs/agent/memory/current-state.md` edit and all untracked test,
Playwright, output, and parallel-task directories predate this task. They are
excluded from this task and must not be staged, modified, cleaned, or committed.
