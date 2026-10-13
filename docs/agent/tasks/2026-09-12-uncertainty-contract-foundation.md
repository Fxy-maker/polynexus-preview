---
task_id: 2026-09-12-uncertainty-contract-foundation
kind: schema
status: implementation_complete_review_required
date: 2026-09-12
title: Add a diagnostic measurement-uncertainty contract
---

# Diagnostic Measurement-Uncertainty Contract

## Goal

Add one shared, JSON/hash/replay-stable DTO for measurement-error and
repeatability evidence, with a small deterministic RSS projection into the
existing `ComputeResult.uncertainty` and metric manifest fields.

## Non-goals

- No change to existing metric values or compute admission.
- No universal metrology model, confidence claim, capability promotion, or
  automatic scientific conclusion.
- No requirement that a provider emit uncertainty when its inputs do not
  contain repeatability, resolution, calibration, baseline, or fit evidence.
- No GUI-specific or AI-specific uncertainty representation.

## Shared objects and entry points

- Objects: `UncertaintyComponent`, `UncertaintySummary`, `ComputeResult`,
  metric manifest, evidence-package shared projection.
- AI/Codex/CLI and GUI: consume the same serialized uncertainty mapping;
  existing routes remain backward compatible with legacy mappings.
- Cross-entry rule: the DTO serializes through the existing ComputeResult,
  ComputeRun, project evidence, and provider-result contracts.

## Affected boundaries

- `polynexus/core/ai_platform/contracts.py`: shared DTO validation and
  serialization.
- `polynexus/core/compute/models.py`: accept nested shared DTOs in the existing
  compute projection.
- `polynexus/core/project_workflow/package.py`: unchanged consumer; it already
  forwards the shared uncertainty projection and is covered by existing
  contract tests.

## Implementation plan

1. Add strict component and summary DTOs with deterministic RSS/coverage
   projection and content hashes.
2. Make the existing AI, ComputeRun, and ProviderResultInput JSON boundaries
   serialize the DTO without changing legacy mappings.
3. Add focused regression tests for available/unavailable, invalid, replay, and
   cross-projection behavior.
4. Run the focused matrix and structured verifier, then create an allowlisted
   local checkpoint.

## Acceptance criteria

- [ ] Components validate finite non-negative values, source kind, unit, and
  input metric bindings.
- [ ] A summary deterministically derives standard uncertainty by RSS and can
  optionally derive expanded uncertainty from an explicit coverage factor.
- [ ] Missing evidence is represented as `unavailable` without hiding the
  metric or blocking the run.
- [ ] DTO round-trip and content hash are stable; unknown schema/value models
  fail closed.
- [ ] New DTO values appear in metric manifests and evidence projections while
  legacy uncertainty mappings remain readable.
- [ ] Focused regression tests cover valid, unavailable, invalid, replay, and
  cross-projection cases.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_uncertainty_contract.py tests/test_compute_models.py tests/test_ai_platform_contracts.py
python scripts/verify.py --task docs/agent/tasks/2026-09-12-uncertainty-contract-foundation.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(contract): add diagnostic uncertainty evidence" `
  --files polynexus/core/ai_platform/contracts.py polynexus/core/ai_platform/__init__.py tests/test_uncertainty_contract.py docs/agent/tasks/2026-09-12-uncertainty-contract-foundation.md
```

## Completion evidence

- Exact commands and outcomes: focused uncertainty/cross-entry tests pass
  (`63 passed`); structured task verifier passes Ruff, compile, type baseline,
  quality gate (`313 passed`), preprocessing (`157 passed`), and whitespace.
- Known limitations or follow-up: provider-specific uncertainty adapters,
  standards/negative controls, and scientific review remain open.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`
  and unrelated untracked research artifacts.
