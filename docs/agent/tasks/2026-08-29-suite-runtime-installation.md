---
task_id: 2026-08-29-suite-runtime-installation
kind: architecture
status: proposed
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

- Exact commands and outcomes:
- Known limitations or follow-up:
- Pre-existing changes left untouched:
