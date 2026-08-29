---
task_id: 2026-08-29-suite-runtime-installation
kind: architecture
status: implementation_complete_review_required
date: 2026-08-29
title: Add PolyNexus Suite runtime and skill installation management
---

# PolyNexus Suite Runtime and Skill Installation

## Goal

Provide one shared Suite Manager for Codex/ARS discovery, explicit pinned skill
installation/update with rollback, and package-relative evidence handoff.

## Non-goals

- Embedding ARS or other skill source in Core.
- Making Codex, ARS, network, or RAG mandatory for analysis.
- Recomputing metrics or changing scientific eligibility.
- Automatic installation, uploads, pushes, merges, or deployment.

## Shared objects and entry points

- Objects: evidence package and export/handoff descriptor; project/run objects
  remain unchanged.
- AI/Codex/CLI: consumes Suite Manager DTOs and evidence handoff.
- GUI: consumes the same DTOs through a thin adapter; no second installer.
- Core providers: unchanged; Suite Manager is orchestration/integration only.
- Cross-entry rule: CLI and GUI must call the same service and handoff contract.

## Affected boundaries

- `polynexus.suite`: new integration boundary for external Codex skills.
- `polynexus.cli`: new `suite` command delegates to the shared boundary.
- `polynexus.gui`: thin DTO adapter only; no Qt/provider logic changes.
- `polynexus.core.project_workflow`: read-only consumer through
  `load_evidence_package_view`; no evidence schema changes.
- User configuration: `suite-lock.json` and timestamped backups under the
  PolyNexus user configuration directory.

## Implementation plan

1. Add validated Suite manifest, component, status, and atomic lock contracts.
2. Implement discovery, compatibility, staging, hash validation, activation,
   and rollback in `SuiteManager`.
3. Expose doctor/install/update/rollback/handoff through one CLI dispatcher.
4. Add a Qt-free GUI adapter and cross-entry regression tests.
5. Run focused tests, the task verifier, and whitespace checks; record known
   limitations and preserve existing untracked runtime files.

## Context and output budget

- Read first: the approved design at
  `docs/superpowers/specs/2026-08-29-suite-runtime-installation-design.md`,
  `pyproject.toml`, CLI parser/dispatcher, existing evidence handoff tests, and
  Codex skill-installer contract.
- Preserve pre-existing untracked `active_run.json`, `runs/`, and
  `tests/_tmp_phase3/`.

## Acceptance criteria

- [ ] `suite doctor` reports Codex, ARS, lock, and compatibility state.
- [ ] Explicitly confirmed online or offline installation validates hashes and
      required files before activation.
- [ ] Failed or incompatible updates preserve the previous installation and
      return stable reason codes.
- [ ] CLI and GUI use the same Suite Manager DTOs.
- [ ] `suite handoff --package PATH` validates and references the existing ARS
      evidence files without copying metric payloads.
- [ ] Focused tests, structured verification, and `git diff --check` pass.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_suite_runtime.py tests/test_suite_cli.py tests/test_suite_handoff.py
python scripts/verify.py --task docs/agent/tasks/2026-08-29-suite-runtime-installation.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(suite): add runtime and skill installation manager" `
  --files <changed source files> <changed test files> `
  docs/superpowers/specs/2026-08-29-suite-runtime-installation-design.md `
  docs/agent/tasks/2026-08-29-suite-runtime-installation.md
```

## Completion evidence

- Exact commands and outcomes: 12 focused Suite tests passed; `python
  scripts/verify.py --task docs/agent/tasks/2026-08-29-suite-runtime-installation.md
  --changed --types` passed task validation, Ruff, compile, quality (313),
  preprocessing (157), and whitespace checks.
- Known limitations or follow-up: the official ARS distribution URL, license,
  and production pinned hash still require human confirmation before shipping a
  network catalog entry. Historical full-suite failures remain outside this
  task's boundary.
- Pre-existing changes left untouched: `active_run.json`, `runs/`, and
  `tests/_tmp_phase3/`.
