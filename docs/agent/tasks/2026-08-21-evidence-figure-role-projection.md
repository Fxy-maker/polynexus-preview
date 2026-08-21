---
task_id: 2026-08-21-evidence-figure-role-projection
kind: architecture
status: active
date: 2026-08-21
title: Preserve ARS-selected figure roles in evidence packages
---

# Preserve ARS-Selected Figure Roles In Evidence Packages

## Goal

New packages label explicitly selected ARS group figures as manuscript or
supporting candidates, while unselected run-output figures remain diagnostics
and every figure has its actual producing technique.

## Non-goals

- Change calculation, scientific eligibility, or raw data.
- Auto-promote unselected ordinary figures.
- Rewrite historical immutable packages.

## Shared objects and entry points

- Objects: evidence package, export.
- Producer: `ProjectEvidencePackager` creates `figure-index.json` from runs
  and optional `FigureCandidateSet`.
- AI/Codex/CLI: unchanged consumer of the same figure index and candidate
  manifest.
- GUI: unchanged consumer via `EvidencePackageView.figure_views`.
- Cross-entry rule: role and technique originate in the packager, then flow
  unchanged to every reader; no consumer infers scientific status.

## Acceptance criteria

- [ ] Explicit main/supporting candidate SVGs receive distinct candidate roles.
- [ ] Unselected run outputs remain diagnostic.
- [ ] Index technique is the producing run/candidate technique, not a
  package-wide first-evidence fallback.
- [ ] All candidate entries remain `review_only` until human review.
- [ ] Existing index DTO and legacy reader continue to load the package.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_workflow_package.py tests/test_ars_group_figure_candidates.py tests/test_evidence_package_view.py
python scripts/verify.py --task docs/agent/tasks/2026-08-21-evidence-figure-role-projection.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py --message "fix(evidence): preserve selected figure roles" --files polynexus/core/project_workflow/package.py tests/test_project_workflow_package.py tests/test_ars_group_figure_candidates.py docs/superpowers/specs/2026-08-21-evidence-figure-role-projection-design.md docs/superpowers/plans/2026-08-21-evidence-figure-role-projection.md docs/agent/tasks/2026-08-21-evidence-figure-role-projection.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md docs/acceptance/2026-08-21-evidence-figure-role-projection.md
```

## Completion evidence

- Exact commands and outcomes:
- Known limitations or follow-up:
- Pre-existing changes left untouched: `.superpowers/`, `tests/_tmp_phase3/`.
