---
task_id: 2026-09-05-tga-method-sensitivity-replay
kind: scientific
status: implementation_complete_review_required
date: 2026-09-05
title: Add canonical TGA method-sensitivity replay
---

# Add Canonical TGA Method-Sensitivity Replay

## Goal

Allow an explicit TGA request to replay selected DTG/event-processing parameter
candidates against the same validated `CanonicalExperiment` and publish their
numeric differences through the shared `MethodSensitivity` projection.

## Non-goals

- Do not generate candidates automatically, optimize a parameter, or select a
  winning method.
- Do not represent parameter sensitivity as instrument measurement uncertainty.
- Do not add a TGA-private replay, audit, evidence, or persistence object.
- Do not promote TGA capability maturity, infer material chemistry, or add
  multi-rate kinetics.
- Do not modify source files, canonical templates, or raw data during replay.

## Shared objects and entry points

- Objects: `CanonicalExperiment`, `ComputeRun`, `ComputeResult`, and
  `MethodSensitivity`.
- AI/Codex services may submit the existing `method_sensitivity` pipeline
  option and read the same result projection. Existing CLI callers can read
  the projection but do not gain a new command-line candidate syntax here.
- GUI: unchanged; its shared ComputeRun worker receives sensitivity results
  without a TGA-specific analysis path.
- Cross-entry rule: primary and candidate TGA runs consume the validated
  canonical template whenever it is available; candidate runs must not call
  `load()` or create a raw-file-only result.

## Affected boundaries

- Shared ComputeRun method-sensitivity replay adapter and its immutable-config
  handling.
- Shared MethodSensitivity dimension inventory and public result serialization.
- TGA processing configuration only; canonical conversion, raw artifacts,
  capability maturity, evidence packaging, and GUI presentation are unchanged.

## Sensitivity contract

- `dtg_window`: positive integer local-polynomial window candidates.
- `dtg_polynomial_order`: positive integer local-polynomial order candidates.
- `event_prominence`: nonnegative robust-noise multiplier candidates.
- `event_minimum_mass_loss`: nonnegative percent-initial-mass candidates.

Each candidate is user/AI-proposed, has a deterministic method label, and
retains failed/unavailable values rather than disappearing. The emitted
difference ranges are method sensitivity only, not experimental uncertainty.

## Implementation plan

1. Declare the bounded TGA sensitivity dimensions in the existing shared
   method-sensitivity inventory.
2. Make candidate configuration replacement support immutable dataclass
   configs while preserving existing mutable mappings and objects.
3. Route template-aware candidate engines through the already admitted
   canonical template and record primary/candidate input modes separately.
4. Add focused regressions for window candidates, invalid candidates,
   immutable primary state, public serialization, and existing service paths.

## Acceptance criteria

- [x] Explicit TGA candidates produce shared `MethodSensitivity` records with
  primary method, candidate values, source, and dimension metadata.
- [x] An immutable `TGAProcessingConfig` can be varied without mutating the
  primary engine configuration.
- [x] TGA candidate replay reuses the canonical template and never calls raw
  `load()` after the primary conversion.
- [x] Invalid candidates remain explicitly unavailable/failed and do not alter
  the completed primary run.
- [x] Existing mutable-config technique sensitivity behavior remains covered.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_tga_sensitivity.py tests/test_tga_processing.py tests/test_compute_service.py tests/test_method_sensitivity.py
python scripts/verify.py --task docs/agent/tasks/2026-09-05-tga-method-sensitivity-replay.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add canonical tga sensitivity replay" `
  --files docs/agent/tasks/2026-09-05-tga-method-sensitivity-replay.md `
          polynexus/core/compute/service.py `
          polynexus/core/compute/method_sensitivity.py `
          tests/test_tga_sensitivity.py tests/test_compute_service.py `
          tests/test_method_sensitivity.py docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes:
  - Initial TGA sensitivity tests failed as expected because shared service
    support and the TGA dimensions were absent.
  - `python -m pytest -p no:cacheprovider -q tests/test_tga_sensitivity.py
    tests/test_compute_service.py tests/test_method_sensitivity.py` - 69
    passed, 3 skipped.
  - `python scripts/verify.py --task
    docs/agent/tasks/2026-09-05-tga-method-sensitivity-replay.md --changed
    --types` - passed Ruff, compile, quality 313, preprocessing 157, and
    whitespace.
- Known limitations or follow-up: this is not independent instrument replay or
  measurement uncertainty. Standards, negative controls, cross-instrument
  data, uncertainty models, capability promotion, and FigurePlan remain
  separate review-required work.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  manuscript plans/specs, `li2020.txt`, `lotz2021.txt`, and
  `tests/_tmp_phase3/` remain outside this task.
