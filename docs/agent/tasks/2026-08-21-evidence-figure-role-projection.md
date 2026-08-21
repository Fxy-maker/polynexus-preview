---
task_id: 2026-08-21-evidence-figure-role-projection
kind: architecture
status: implementation_complete_review_required
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

## Affected boundaries

- `ProjectEvidencePackager` asset descriptors and canonical SVG index
  projection.
- `figure-candidates.json` package-relative candidate asset references.
- Existing `FigureIndexEntry` / `EvidencePackageView.figure_views` readers in
  AI/CLI and GUI; their serialized fields remain unchanged.

## Implementation plan

1. Add a failing package regression proving a selected IR candidate is not
   projected as a DSC diagnostic.
2. Carry role, technique, group, and review-only eligibility from producing
   runs or explicit ARS candidates into asset descriptors.
3. Deduplicate same logical SVG/PNG siblings, retain other run figures as
   diagnostics, and reject missing-SVG or role-conflicting candidates.
4. Verify package producer plus ARS, package-view, AI/CLI, and Gallery
   consumers, then replay the read-only PA6 FTIR selected group.

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
  - Focused red regression before implementation:
    `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_package.py -k "preserves_ars_selected_figure_role_and_technique"` -> expected failure: index emitted `diagnostic`, `DSC`, and no group for a selected IR candidate.
  - Focused producer and consumer matrix:
    `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_package.py tests/test_ars_group_figure_candidates.py tests/test_evidence_package_view.py tests/test_ai_native_project_entrypoint.py tests/test_plot_gallery_service.py` -> `64 passed`.
  - `ruff check polynexus/core/project_workflow/package.py tests/test_project_workflow_package.py`, `python -m compileall -q polynexus/core/project_workflow/package.py`, and `git diff --check` -> passed.
  - Read-only real PA6 FTIR replay created `D:\PolyNexus-pa6-four-technique-smoke-20260814\.polynexus\evidence\pa6-role-projection-smoke-v002`; its selected FTIR overlay is indexed as `manuscript_candidate`, `IR`, group `ir:pa6-jw:temperature_C`, and `review_only`, alongside 18 IR diagnostic entries. The raw input junction was not modified.
- Known limitations or follow-up: only FTIR has an ARS group-figure renderer;
  DSC/SAXS/WAXS/WAXS group-level candidate generators remain future work.
- Pre-existing changes left untouched: `.superpowers/`, `tests/_tmp_phase3/`.
