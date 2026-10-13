---
task_id: 2026-09-05-tga-replay-validation-boundary
kind: scientific
status: implementation_complete_review_required
date: 2026-09-05
title: Add TGA replay, anomaly matrix, and uncertainty boundary
---

# Add TGA Replay, Anomaly Matrix, And Uncertainty Boundary

## Goal

Provide a shared, deterministic TGA validation report that replays a bounded
matrix of normal and anomalous curves, preserves local unavailable states, and
reports when measurement uncertainty evidence is unavailable.

## Non-goals

- Do not claim synthetic replay as independent instrument/material validation.
- Do not convert method sensitivity into measurement uncertainty.
- Do not infer polymer chemistry, decomposition mechanism, or publication status.
- Do not modify raw arrays, canonical templates, ComputeRun state, or capability
  maturity.
- Do not add GUI-only, AI-only, or private persistence representations.

## Shared objects and entry points

- Objects: `TGAReplayCase`, `TGAReplayObservation`, `TGAUncertaintyReport`, and
  `TGAValidationReport` are Core-owned JSON-safe DTOs. The processing function
  remains the existing `analyze_tga_curve` contract.
- AI/Codex/CLI: may call the same pure replay suite and consume its report;
  no new private result path is introduced.
- GUI: unchanged; it can later consume the report through the shared DTO.
- Cross-entry rule: replay uses the same TGA processing implementation as
  ComputeRun and does not create a second algorithm or mutate source data.

## Affected boundaries

- New `polynexus.core.tga_validation` DTOs and deterministic replay suite.
- Core package exports and focused regression tests.
- No change to capability promotion or evidence-package admission.

## Implementation plan

1. Define immutable, content-addressed replay-case, observation, uncertainty,
   and validation-report DTOs with JSON round trips.
2. Replay every case twice through `analyze_tga_curve`, retaining expected and
   observed branch status, source-preservation, deterministic-output, axis, and
   event-bound checks.
3. Provide a default normal/anomalous curve matrix without material-specific
   semantics or a separate TGA implementation.
4. Return a structured unavailable measurement-uncertainty report until
   experimental evidence and a reviewed uncertainty model are available.
5. Exercise normal, anomalous, serialization, and uncertainty-boundary paths
   with focused regression tests and the structured verifier.

## Acceptance criteria

- [x] Built-in replay cases cover single-step, double-step, noise, too few
  points, non-monotonic axis, nonpositive initial mass, time axis, unknown
  temperature unit, and out-of-range residue target.
- [x] Every case returns a retained observation with check-level status and
  local failure reasons; one anomalous case cannot hide other results.
- [x] Replay verifies source-array preservation, deterministic rerun equality,
  expected computed/unavailable branches, and valid event bounds where present.
- [x] Uncertainty report returns `unavailable` with an explicit reason when no
  replicate measurements, instrument error, calibration error, or standard
  sample evidence is supplied. It never emits fabricated intervals.
- [x] DTOs round-trip through strict JSON-safe dictionaries and expose a
  content hash for persisted/reviewed reports.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_tga_validation.py tests/test_tga_processing.py tests/test_tga_sensitivity.py
python scripts/verify.py --task docs/agent/tasks/2026-09-05-tga-replay-validation-boundary.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add tga replay validation boundary" `
  --files docs/agent/tasks/2026-09-05-tga-replay-validation-boundary.md `
          polynexus/core/tga_validation.py polynexus/core/__init__.py `
          tests/test_tga_validation.py docs/agent/memory/active-work.md `
          docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes:
  - Initial red test: `tests/test_tga_validation.py` failed collection because
    the public validation module was absent.
  - `python -m pytest -p no:cacheprovider -q tests/test_tga_validation.py
    tests/test_tga_processing.py tests/test_tga_sensitivity.py` - 12 passed.
  - `python -m pytest -p no:cacheprovider -q tests/test_tga_validation.py
    tests/test_tga_processing.py tests/test_tga_sensitivity.py
    tests/test_compute_service.py tests/test_method_sensitivity.py` - 79
    passed, 3 skipped.
  - `python scripts/verify.py --task
    docs/agent/tasks/2026-09-05-tga-replay-validation-boundary.md --changed
    --types` - passed Ruff, compile, quality 313, preprocessing 157, and
    whitespace.
  - `git diff --check` - passed.
- Known limitations or follow-up: synthetic replay is an algorithm-boundary
  regression suite, not independent instrument/material replay. Independent
  data, standard samples, calibration/instrument models, an implemented
  measurement-uncertainty model, and human scientific review remain required
  before capability promotion.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  manuscript plans/specs, `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/`.
