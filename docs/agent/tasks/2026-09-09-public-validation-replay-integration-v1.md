---
task_id: 2026-09-09-public-validation-replay-integration-v1
kind: architecture
status: implementation_complete_review_required
date: 2026-09-09
title: Add hash-bound replay for external public validation data
---

# Public validation replay integration v1

## Goal

Replay explicitly selected members of the external public validation pack
through the existing canonical and ComputeRun path, then compare the two
deterministic public projections with the shared project validation batch.

## Non-goals

- No third-party raw data in Git and no arbitrary code or plugin loading.
- No calibration, metrology/uncertainty claim, capability promotion, or
  scientific conclusion.
- No replacement of the existing direct, GUI, or Agent result contracts.

## Shared objects and entry points

- Objects: `PublicReplayCase`, `ValidationCase`, `ProjectValidationEntry`,
  `ProjectValidationBatch`, `CanonicalDataset`, `CanonicalExperiment`, and
  `ComputeRun`.
- CLI: add `polynexus public-validate`; optional project persistence uses the
  existing `.polynexus/validation/latest.json` helper.
- GUI and Agent: unchanged consumers; they can consume the same persisted batch
  later. No private validation representation is introduced.

## Affected boundaries

- External validation data root and public replay manifest (kept outside Git).
- Canonical converter registry, `ComputeRunService`, validation harness, and
  project validation persistence; existing provider algorithms are unchanged.
- CLI parser/dispatcher for the new `public-validate` command.

## Security and scientific boundary

- Archive/member/file paths are constrained below an explicitly supplied data
  root; archive, member, extracted content, and canonical IDs are hash-bound.
- ZIP traversal, symlink members, oversized archives, and member-count/size
  violations fail closed before provider execution.
- Negative/unavailable cases remain explicit status observations. Public data is
  parser/replay evidence only, not a certified standard or capability evidence.

## Implementation plan

1. Add immutable replay-case DTOs with archive/member/file hashes and explicit
   canonical admission metadata.
2. Implement bounded ZIP member extraction and path-independent raw identity,
   then replay through the existing `ComputeRunService` twice.
3. Project both runs through `ValidationCase` and `ProjectValidationBatch`, and
   expose optional project persistence through the CLI.
4. Add focused tamper, traversal, format, unavailable-status, and CLI tests;
   run the selected external five-case manifest without copying raw data into
   the repository.

## Acceptance criteria

- [x] A selected archive member can be extracted and replayed twice through
  `ComputeRunService` with a path-independent artifact and `CanonicalDataset`
  binding.
- [x] Archive/member/file hash changes, traversal, missing members, and status
  mismatches fail before a result is accepted.
- [x] Successful and unavailable cases both become ordinary project validation
  entries; failures do not mutate ComputeRun, Evidence, or capability state.
- [x] CLI emits the shared batch report and optionally persists it beneath the
  project derived validation directory.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_public_validation.py tests/test_cli_public_validation.py
python scripts/verify.py --task docs/agent/tasks/2026-09-09-public-validation-replay-integration-v1.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(validation): replay public validation pack" `
  --files polynexus/core/public_validation.py polynexus/cli/run_public_validation_service.py polynexus/cli/parser.py polynexus/__main__.py polynexus/core/__init__.py polynexus/core/compute/models.py tests/test_public_validation.py tests/test_cli_public_validation.py tests/test_compute_models.py docs/agent/tasks/2026-09-09-public-validation-replay-integration-v1.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes: `python -m pytest -p no:cacheprovider -q
  tests/test_public_validation.py tests/test_cli_public_validation.py
  tests/test_project_validation.py tests/test_validation_harness.py
  tests/test_cli_validation.py` (20 passed); `python scripts/verify.py --task
  docs/agent/tasks/2026-09-09-public-validation-replay-integration-v1.md
  --changed --types` passed quality gate 313, preprocessing 157, Ruff,
  compile, and whitespace checks. A real five-case external replay (IR, SAXS,
  NMR, DSC, TGA) passed and persisted its report under the external replay
  project.
- Known limitations or follow-up: selected external cases still require
  scientific review, independent replay, standards/negative controls, and
  uncertainty before any capability promotion.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`
  and unrelated untracked plans/data.
