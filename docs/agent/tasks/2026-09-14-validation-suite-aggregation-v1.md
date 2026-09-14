---
task_id: 2026-09-14-validation-suite-aggregation-v1
kind: architecture
status: implementation_complete_review_required
date: 2026-09-14
title: Aggregate existing replay and smoke evidence into one validation report
---

# Validation suite aggregation v1

## Goal

Collect the existing public deterministic replay batch and the external
all-module smoke report into one compact, hash-bound validation-suite report
that AI, CLI, and future GUI consumers can read without copying raw data or
creating another result representation.

## Non-goals

- No new technique algorithms, vendor readers, calibration, uncertainty, or
  capability promotion.
- No claim that parser replay or smoke output is a certified standard or
  publication validation.
- No execution of arbitrary commands or code from a JSON manifest.
- No replacement of the existing ValidationCase, ProjectValidationBatch, or
  ComputeRun contracts.

## Shared objects and entry points

- Inputs: `ProjectValidationBatch` from the existing public replay route and
  the external all-module smoke report.
- Output: immutable `ValidationSuiteReport` with typed evidence entries,
  source hashes, coverage counts, and explicit review limitations.
- CLI: new `polynexus validation-suite` command; optional project persistence
  stays under `.polynexus/validation`.
- GUI/Agent: unchanged consumers in this slice; they can consume the same JSON
  report later.

## Affected boundaries

- Core validation aggregation only; existing replay calculators and providers
  remain unchanged.
- External validation-data root is read-only and remains outside Git.
- Scientific status is split into deterministic replay, smoke-only, and
  unavailable rather than collapsed into one capability claim.

## Implementation plan

1. Define immutable aggregate entry/report DTOs over existing replay and smoke
   projections, with content hashes and explicit evidence kinds.
2. Add a pure aggregator that retains source hashes, replay state, route/status,
   reason codes, and scientific limitations without recalculating metrics.
3. Add the `validation-suite` CLI and project persistence route under the
   existing `.polynexus/validation` boundary.
4. Exercise round-trip/tamper behavior, mixed replay/smoke classification,
   and a real external aggregation using the existing validation assets.

## Acceptance criteria

- [x] Public replay reports become one entry per case with batch/report hashes,
  deterministic state, replay count, and review limitations.
- [x] All-module smoke entries are classified as `smoke_only` or `unavailable`
  without treating smoke completion as scientific validation.
- [x] The aggregate report is JSON round-trippable, content-hash bound, and
  rejects tampering.
- [x] CLI can run the existing public replay manifest, merge an existing smoke
  report, and optionally persist one report under project validation storage.
- [ ] No raw archive is copied into the repository and no ComputeRun/Evidence
  Package/capability state is mutated.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_validation_suite.py tests/test_cli_validation_suite.py
python scripts/verify.py --task docs/agent/tasks/2026-09-14-validation-suite-aggregation-v1.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(validation): aggregate replay and smoke evidence" `
  --files README.md polynexus/core/validation_suite.py polynexus/core/project_workflow/workspace.py polynexus/core/__init__.py polynexus/cli/parser.py polynexus/cli/run_validation_suite_service.py polynexus/__main__.py tests/test_validation_suite.py tests/test_cli_validation_suite.py docs/agent/tasks/2026-09-14-validation-suite-aggregation-v1.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes: focused suite coverage passes `5`; actual
  external aggregation produced `5` deterministic replay, `4` smoke-only, and
  `6` unavailable entries across `10` techniques with status
  `complete_with_review`. Task verification passes task-card/memory checks,
  Ruff, compile, quality `313`, preprocessing `157`, and whitespace.
- Known limitations: module unit-test results remain ordinary software-quality
  evidence; this report does not promote scientific capabilities. Independent
  standards/negative controls, formal uncertainty, and human scientific review
  remain required.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  unrelated plans/specs, literature text, and temporary test artifacts.
