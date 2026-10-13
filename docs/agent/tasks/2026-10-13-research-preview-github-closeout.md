---
task_id: 2026-10-13-research-preview-github-closeout
kind: architecture
status: implementation_complete_review_required
date: 2026-10-13
title: Close out completed research-preview work for GitHub integration
---

# Research-preview GitHub closeout

## Goal

Prepare the 50 completed commits after public preview `f63b3586` for a
reviewable GitHub pull request into `Fxy-maker/polynexus-preview` branch
`research-preview-v0.1`, with current capability documentation and cumulative
integration verification.

## Non-goals

- Implement the proposed ReferenceEvidence layer or infer reference values
  for unknown materials.
- Promote scientific capabilities, publish datasets or packages, change
  repository visibility, or integrate unrelated local branches.
- Include personal drafts, literature files, temporary tests, or raw archives.

## Shared objects and entry points

- Objects under cumulative review: CanonicalExperiment/CanonicalDataset,
  ComputeRun, Metric Manifest, FigureDefinition, Evidence Package, portable
  export manifests, uncertainty projections, and validation reports.
- Producers: canonical readers, technique providers, and ComputeRunService.
  Consumers: CLI, Agent/Codex, project workflow, and GUI workers/import dialogs.
  Closeout changes documentation and CI only unless a concrete integration
  defect needs a focused regression repair.
- Scientific outputs remain diagnostic; validation reports do not promote
  capabilities or constitute scientific approval.

## Affected boundaries

- README and open-source capability statements, CI preview-branch triggers,
  cumulative release verification, and GitHub PR metadata.
- Use an isolated managed checkout at the completed HEAD; preserve the
  original workspace and all unrelated worktrees.

## Implementation plan

1. Resolve the public repository/base and inspect the cumulative commit/file
   scope, release artifacts, and known limitations.
2. Refresh capability statements and enable existing CI for the public base.
3. Run full/boundary verification against the actual public base; repair
   concrete in-scope integration defects with regression proof.
4. Record verification and review needs, checkpoint an explicit allowlist,
   and push the integration branch.
5. Create a PR with the completed scope and evidence. Merge after required
   checks and repository-required human review are satisfied.

## Acceptance criteria

- [x] Only completed tracked work and explicit closeout changes enter the PR.
- [x] Public documentation describes actual diagnostic routes and limits.
- [x] Existing GitHub CI triggers on the public preview base branch.
- [x] Cumulative full/boundary verification outcomes are recorded honestly.
- [ ] PR links the task and verification evidence; architecture/scientific
  human review required by AGENTS.md remains explicit before merge.
- [x] Original workspace personal and temporary files remain untouched.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-10-13-research-preview-github-closeout.md --base preview/research-preview-v0.1 --changed --types --full --boundary
git diff --check preview/research-preview-v0.1
```

## Checkpoint allowlist

Initial scope: `.gitignore`, `.github/workflows/ci.yml`, `README.md`, `docs/OPEN_SOURCE.md`,
this task card, `docs/acceptance/2026-10-13-research-preview-github-closeout.md`,
and focused agent memory updates. Add source/test paths only for a documented
integration repair after its regression check.

## Completion evidence

The cumulative full gate ran and failed with `49 failed, 4948 passed,
45 skipped`. An unchanged public-baseline checkout reproduced 44 failures
from the 48 existing cases. Closeout repairs and targeted replay leave 38
failures, all reproduced on that baseline (`38 failed, 7 passed, 5 skipped`).
Focused closeout contracts pass `62` with `4` missing-vendor-data skips.
The completed-module test selection passes `438` with `3` skips.
Ruff/compile, phased Pyright (0 errors), core quality (313), preprocessing
(157), whitespace, and the separate boundary audit passed.

The PR will be a draft. Human architecture/scientific review and the decision
on the existing failing baseline remain merge blockers. No numerical model
was changed to conceal those failures. Details:
`docs/acceptance/2026-10-13-research-preview-github-closeout.md`.
