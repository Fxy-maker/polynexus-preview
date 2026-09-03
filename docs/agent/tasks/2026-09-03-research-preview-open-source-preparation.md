---
task_id: 2026-09-03-research-preview-open-source-preparation
kind: architecture
status: implementation_complete_review_required
date: 2026-09-03
title: Prepare an honest Apache-2.0 research-preview source release
---

# Prepare an honest Apache-2.0 research-preview source release

## Goal

Make the repository ready for a public source release as a clearly scoped
PolyNexus Research Preview: add the Apache-2.0 license, public contribution
and release-boundary documentation, an accurate capability-maturity statement,
and ignore rules for common local run artifacts.

## Non-goals

- Do not push, create a public repository, create a package release, or modify
  remote hosting settings.
- Do not change scientific algorithms, result values, provider behavior, or
  the supported-technique contract.
- Do not delete, move, stage, or publish current user data, local runs, logs,
  drafts, or untracked files.
- Do not claim full-suite green status or scientific maturity beyond the
  documented capability boundary.

## Shared objects and entry points

- Objects: release metadata and public documentation only; project, run,
  chart, evidence package, and export objects are unchanged.
- AI/Codex/CLI: unchanged; documents explain the optional local automation
  entry point without making Codex a required dependency.
- GUI: unchanged.
- Cross-entry rule: this isolated documentation/metadata task changes no
  producer or consumer contract.

## Affected boundaries

- Release boundary: LICENSE, package metadata, README, contribution guidance,
  and release/data-rights documentation.
- Runtime boundary: `.gitignore` only; no project, run, chart, evidence, or
  export object is changed.
- Entry points: AI/Codex, CLI, GUI, and provider implementations are unchanged;
  the documentation describes their existing shared Core boundary.

## Implementation plan

1. Add Apache-2.0 license text and package metadata, using the repository's
   current author identity for the boilerplate notice.
2. Document Research Preview maturity levels, AI/Core responsibilities,
   contribution rules, and the final public-release checklist.
3. Ignore common local runtime artifacts without touching existing user files.
4. Run focused contract tests, task-scoped verification, and whitespace checks;
   record limitations and untouched changes in this task card and memory.

## Context and output budget

- Read first: repository contract, README, memory index/current state/active
  work, release-related public files, and tracked-file inventory.
- Search scope: root release files, `docs/`, `.gitignore`, `pyproject.toml`,
  and capability catalog status only.
- Expand only for: a potential secret, unlicensed third-party material,
  release claim that lacks evidence, or verification failure.
- Report: changed release files, exact verification result, release limitations,
  and untouched user changes.

## Acceptance criteria

- [ ] Repository declares an Apache-2.0 license in a standard `LICENSE` file
  and package metadata.
- [ ] README identifies the project as a Research Preview, names the
  AI/Codex-to-Core boundary, and links to the capability maturity and release
  guidance.
- [ ] Public guidance clearly distinguishes available, experimental, and
  unsupported routes without promising a complete polymer characterization
  platform.
- [ ] Contribution and release-boundary documents require provenance-safe
  changes and an explicit rights review before publishing any sample data.
- [ ] Common local runtime artifacts are ignored; current user-created files
  remain untouched.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_ai_platform_contracts.py tests/test_compute_models.py
python scripts/verify.py --task docs/agent/tasks/2026-09-03-research-preview-open-source-preparation.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "docs(release): prepare research preview open source metadata" `
  --files LICENSE README.md CONTRIBUTING.md docs/OPEN_SOURCE.md .gitignore pyproject.toml docs/agent/tasks/2026-09-03-research-preview-open-source-preparation.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes:
  - `python -m pytest -p no:cacheprovider -q tests/test_ai_platform_contracts.py tests/test_compute_models.py` — passed.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-03-research-preview-open-source-preparation.md --changed --types` — passed for the selected release metadata/documentation boundary.
  - `git diff --check` — passed.
- Known limitations or follow-up:
  - This is a Research Preview, not a claim of publication-validated coverage or production readiness.
  - Capability maturity, scientific semantics, third-party data rights, and the final public release branch still require human review.
  - No remote push, package publication, or sample-data release was performed.
- Pre-existing changes left untouched:
  - `polynexus/core/agent_workflow/service.py`, `active_run.json`, `runs/`, `tests/_tmp_phase3/`, `li2020.txt`, `lotz2021.txt`, and existing `docs/superpowers/plans/*` / `docs/superpowers/specs/*` changes remain outside this checkpoint.
