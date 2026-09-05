---
task_id: 2026-09-05-tga-dtg-event-candidates
kind: scientific
status: implementation_complete_review_required
date: 2026-09-05
title: Add traceable TGA normalization, DTG, and event candidates
---

# Add Traceable TGA Normalization, DTG, And Event Candidates

## Goal

Extend the sample-neutral TGA Core route with deterministic normalized-mass
curves, DTG curves, material-neutral mass-loss event candidates, and residue at
explicitly requested coordinates. Preserve every source value and expose
method, parameter, unit, canonical-index-range, warning, and unavailable-reason
context
through the existing `AnalysisResult` and `ComputeRun` projections.

## Non-goals

- Do not infer polymer identity, decomposition chemistry, or a named mechanism.
- Do not use material-specific temperature windows or silently choose a
  publication interpretation.
- Do not calculate kinetics from one curve or implement multi-rate kinetic
  models in this task.
- Do not promote TGA capability descriptors beyond their reviewed maturity or
  add a TGA-private run, evidence, provenance, figure, GUI, or persistence DTO.
- Do not add a publication FigureDefinition provider in this task.

## Shared objects and entry points

- Objects: `CanonicalExperiment`, `AnalysisResult`, `ComputeRun`, metric
  manifest, and the existing generic curve capability items.
- AI/Codex/CLI: read the same `ComputeRun` metrics, metadata, derived series,
  warnings, and local unavailable states produced by Core.
- GUI: unchanged; its shared ComputeRun worker receives the same result and no
  technique-private calculation is added to an event handler.
- Cross-entry rule: `TGAEngine.run_pipeline()` and
  `TGAEngine.run_canonical_template()` call one processing implementation; the
  latter remains the canonical route used by `ComputeRunService`.

## Affected boundaries

- TGA signal-processing and engine-result construction.
- Shared `ComputeResult`/metric-manifest consumption is exercised but its DTO
  schema and parser are unchanged.
- Capability maturity declarations remain unchanged until independent replay,
  standards, uncertainty work, and human scientific review are available.

## Implementation plan

1. Add a validated, material-neutral TGA processing configuration and a pure
   curve-analysis function.
2. Normalize against an explicit initial-window statistic while retaining the
   original signal and normalization reference.
3. Derive DTG with a local polynomial method that uses the actual coordinate
   values and records window, polynomial order, sign convention, and boundary
   handling.
4. Detect positive mass-loss-rate peaks and derive candidate onset/endset
   bounds from prominence bases; retain event IDs, canonical indices, values,
   units, parameters, and boundary warnings.
5. Emit final recorded residue and linearly interpolated residue only at
   explicitly requested in-range coordinates; never extrapolate.
6. Keep normalization, DTG, event, and requested-residue failure states local
   so the descriptive TGA run still completes when its canonical curve is
   valid.

## Acceptance criteria

- [x] Source x/mass arrays are byte-for-byte value-equivalent after analysis;
  normalized mass and DTG are separate derived series.
- [x] A deterministic two-step synthetic curve yields two ordered event
  candidates with onset/peak/endset, canonical index range, interval mass loss,
  and explicit method/parameter/unit context. Canonical indices are not
  represented as raw source-row numbers.
- [x] Specified-coordinate residue is interpolated in canonical axis units;
  out-of-range targets are explicit and are never extrapolated.
- [x] Non-increasing or undersampled axes make only DTG-dependent quantities
  unavailable; normalization, final residue, and the base ComputeRun survive.
- [x] Time-axis and unknown-unit inputs remain calculable without being
  mislabeled as temperature or a known derivative unit.
- [x] The complete derived result is visible through `ComputeRun` and its
  metric manifest without a CLI-, GUI-, or AI-private representation.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_tga_processing.py tests/test_tga.py
python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_capability_execution.py tests/test_canonical_nd_adapters.py
python scripts/verify.py --task docs/agent/tasks/2026-09-05-tga-dtg-event-candidates.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add traceable tga event candidates" `
  --files docs/agent/tasks/2026-09-05-tga-dtg-event-candidates.md `
          polynexus/core/tga_processing.py polynexus/core/tga.py `
          tests/test_tga_processing.py README.md docs/OPEN_SOURCE.md `
          docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes:
  - Initial focused test run failed during collection because the processing
    module did not exist, establishing the expected red state.
  - `python -m pytest -p no:cacheprovider -q tests/test_tga_processing.py
    tests/test_tga.py` - 11 passed.
  - `python -m pytest -p no:cacheprovider -q tests/test_compute_service.py
    tests/test_capability_execution.py tests/test_canonical_nd_adapters.py` -
    88 passed, 3 skipped.
  - JSON-safe direct `ComputeRun` smoke - completed with two event candidates
    and 93 metric-manifest records.
  - `python scripts/verify.py --task
    docs/agent/tasks/2026-09-05-tga-dtg-event-candidates.md --changed --types`
    - passed Ruff, compile, quality 313, preprocessing 157, and whitespace.
- Known limitations or follow-up: multi-rate kinetics, uncertainty validation,
  independent instrument/material replay, capability promotion, and the shared
  FigureDefinition provider remain follow-up work.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  manuscript plans/specs, `li2020.txt`, `lotz2021.txt`, and
  `tests/_tmp_phase3/` are outside this task.
