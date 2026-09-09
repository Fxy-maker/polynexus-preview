---
task_id: 2026-09-09-cross-technique-validation-harness-v1
kind: architecture
status: implementation_complete_review_required
date: 2026-09-09
title: Add cross-technique validation harness v1
---

# Cross-technique validation harness v1

## Goal

Provide one technique-neutral validation runner that can replay a canonical
input through a deterministic calculator, compare expected metrics and public
provenance, and emit an immutable report without mutating ComputeRun or
Evidence Package state.

## Non-goals

- No automatic capability promotion or scientific conclusion.
- No metrological uncertainty claim, instrument calibration claim, or universal
  standard-sample semantics.
- No private vendor-format readers and no real validation data committed to Git.
- No replacement of existing technique-specific replay suites.

## Shared objects and entry points

- Objects: canonical dataset/experiment, ComputeResult projection, validation
  case and validation report. Existing ComputeRun and Evidence Package objects
  are read-only consumers in this slice.
- AI/Codex/CLI: may invoke the runner with the same callable used by Core; no
  private result representation is introduced.
- GUI: unchanged; future GUI/CLI adapters can consume the JSON report.
- Cross-entry rule: the runner accepts a public calculator callback and public
  mapping/ComputeResult projections, so Core, CLI, Agent, and GUI adapters can
  share it without technique-specific branching.

## Affected boundaries

- Core validation boundary: new technique-neutral DTOs and replay/comparison
  service only.
- Canonical/ComputeRun boundary: read-only input/result projections; no schema
  changes to existing canonical or run objects.
- AI/CLI/GUI boundary: public callable/mapping adapter contract is available;
  no entry-point wiring is changed in v1.
- Scientific/security boundary: reports explicitly remain diagnostic and do
  not claim instrument validity, uncertainty, or capability promotion.

## Implementation plan

1. Add immutable `ValidationCase` and `ValidationReport` DTOs with content
   hashes, case kind metadata, expected metrics/tolerances/statuses, and raw
   preservation fields.
2. Add a generic deterministic replay runner with optional technique adapter
   callback. It executes twice, compares canonical output hashes, metric
   expectations, statuses, units/methods/parameters/provenance, and raw hash.
3. Keep comparison failures in the report only; do not mutate ComputeRun or
   Evidence Package. Allow cases without scientific expectations to run generic
   checks.
4. Add focused tests for round-trip/hash, deterministic replay, scalar/series
   comparisons, unavailable/failed outcomes, provenance, raw preservation, and
   cross-technique reuse.

## Acceptance criteria

- [x] Cases and reports round-trip through JSON and reject content-hash tampering.
- [x] Two replays of the same case are compared deterministically.
- [x] Expected metric values use absolute/relative tolerances and preserve path,
  unit, method, parameters, and provenance checks.
- [x] Calculator failures and unavailable metrics become explicit report states;
  no exception is hidden and no upstream run/evidence object is changed.
- [x] Raw input hash preservation is checked when a raw snapshot is supplied.
- [x] The same validator is exercised by at least two techniques without
  technique-specific logic in the runner.
- [x] Standard/negative-control metadata is optional case metadata only.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_validation_harness.py
python scripts/verify.py --task docs/agent/tasks/2026-09-09-cross-technique-validation-harness-v1.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(validation): add cross-technique validation harness" `
  --files polynexus/core/validation_harness.py tests/test_validation_harness.py docs/agent/tasks/2026-09-09-cross-technique-validation-harness-v1.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes: `python -m pytest -p no:cacheprovider -q
  tests/test_validation_harness.py` (7 passed); task verifier passed quality
  gate 313, preprocessing 157, Ruff, compile, and `git diff --check`.
- Known limitations or follow-up: adapters for real instrument replay,
  uncertainty, and human capability review remain separate work.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`
  and unrelated untracked plans/data.
