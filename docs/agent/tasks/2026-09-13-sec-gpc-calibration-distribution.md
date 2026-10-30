---
task_id: 2026-09-13-sec-gpc-calibration-distribution
kind: scientific
status: implementation_complete_review_required
date: 2026-09-13
title: Add explicit SEC/GPC calibration and molecular-weight distribution
---

# SEC/GPC Calibration and Distribution

## Goal

Allow SEC/GPC `Mn`, `Mw`, `Mz`, and dispersity to be calculated only when an
explicit calibration and response-distribution semantic contract is supplied.

## Non-goals

- No universal calibration inferred from sample names, detector kind, or
  vendor labels.
- No extrapolation outside calibration points.
- No change to source curves, existing peak/integral metrics, or no-spec
  compatibility behavior.
- No formal capability promotion or metrological claim.

## Affected boundaries

- `polynexus/core/sec_processing.py`: strict analysis spec, calibration fit,
  distribution moments, and local unavailable reasons.
- `polynexus/core/sec.py`: consume the canonical `sec_analysis` payload and
  publish units/methods/parameters through the existing result projection.
- `polynexus/core/compute/service.py` and CLI: bind an explicit SEC spec to the
  canonical template using the shared direct-run path.
- AI/Codex/project and GUI consumers: unchanged object shape; they receive the
  same `ComputeResult`/metric manifest projection and remain free to omit the
  spec.

## Implementation plan

1. Add immutable `SECCalibrationSpec` with finite calibration points, explicit
   response measurement, polynomial degree, and mass/number distribution mode.
2. Fit `log10(M)` against the declared coordinate, reject duplicate points and
   out-of-range curve coordinates, and compute deterministic distribution
   moments without mutating source arrays.
3. Attach the normalized spec through `CanonicalExperiment` and
   `ComputeRunService`, including the SEC/GPC CLI analysis-spec route.
4. Add focused direct, canonical, CLI, replay/hash, and unavailable-path tests.
5. Run the task verifier and create an allowlisted local checkpoint.

## Acceptance criteria

- [ ] No spec leaves molecular-weight moments unavailable.
- [ ] A valid explicit calibration computes `Mn`, `Mw`, `Mz`, and dispersity
  with calibration fit provenance and units.
- [ ] Missing/invalid semantics, duplicate standards, nonpositive response,
  and extrapolation make only the molecular-weight summary unavailable.
- [ ] Source values and existing descriptive metrics remain unchanged.
- [ ] Direct, canonical, CLI, Agent/project consumers use one template/result
  projection; no private result representation is added.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_sec_processing.py tests/test_sec.py
python scripts/verify.py --task docs/agent/tasks/2026-09-13-sec-gpc-calibration-distribution.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(sec): add explicit calibration distribution" `
  --files polynexus/core/sec_processing.py polynexus/core/sec.py polynexus/core/compute/service.py polynexus/cli/parser.py polynexus/cli/run_single_service.py tests/test_sec_processing.py tests/test_sec.py docs/agent/tasks/2026-09-13-sec-gpc-calibration-distribution.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes: SEC/CLI focused coverage passes `22 passed,
  1 deselected` (the deselected case is a pre-existing format-inspection
  expectation outside this task); structured verification passes Ruff, compile,
  type baseline, quality gate (`313 passed`), preprocessing (`157 passed`),
  and whitespace.
- Known limitations or follow-up: multi-detector response-factor calibration,
  vendor-specific readers, independent standards/negative controls, formal
  uncertainty, capability promotion, and human scientific review remain open.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`
  and unrelated untracked research artifacts.
