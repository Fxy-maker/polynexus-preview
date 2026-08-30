---
task_id: 2026-08-30-working-evidence-workspace
kind: architecture
status: complete
date: 2026-08-30
title: Add a mutable current evidence workspace
---

# Current evidence workspace

## Goal

Allow article evidence runs to be appended/replaced in one mutable working set,
then explicitly frozen into an immutable versioned evidence package.

## Non-goals

- Do not mutate existing evidence packages.
- Do not change provider algorithms or scientific review gates.
- Do not copy or rewrite raw research files.

## Shared objects and entry points

- Objects: `ProjectWorkflowRun`, working evidence index, and immutable evidence package.
- AI/Codex/CLI: share `ProjectWorkflowService` methods for upsert, status, and freeze.
- GUI: unchanged and continues reading immutable packages.
- Cross-entry rule: working entries reference validated `.polynexus/runs/*.json` manifests only.

## Affected boundaries

- Project-local `.polynexus/evidence/working.json` state.
- `ProjectWorkflowService` working-set and freeze API.
- Existing `ProjectEvidencePackager` freeze path.

## Acceptance criteria

- [x] Upserting a new run adds it to the working set.
- [x] Upserting a run for the same stable source path replaces the prior run,
      including when the source content hash changes.
- [x] Working status reports current complete/review counts without creating a package.
      Pending/blocked runs remain outside the packageable working frontier and
      continue to be represented by project inventory/run status.
- [x] Explicit freeze creates one immutable versioned package from the current set.
- [x] Existing package loading and source-hash validation remain unchanged.

## Implementation plan

1. Add a validated working-index model and persistence under `.polynexus`.
2. Expose upsert/status/freeze methods from `ProjectWorkflowService`.
3. Add focused tests for append, replace, status, and freeze compatibility.

## Verification

```powershell
python -m pytest -q tests/test_project_evidence_workspace.py
python scripts/verify.py --task docs/agent/tasks/2026-08-30-working-evidence-workspace.md --changed --types
git diff --check
```

## Completion evidence

- `python -m pytest -q tests/test_project_evidence_workspace.py` — 4 passed.
- `python -m pytest -q tests/test_project_workflow_service.py tests/test_project_workflow_package.py tests/test_project_workflow_workspace.py` — 54 passed.
- `python scripts/verify.py --task docs/agent/tasks/2026-08-30-working-evidence-workspace.md --changed --types` — selected checks passed; quality 313 and preprocessing 157 passed.
- `git diff --check` — passed.
- Known limitation: working entries are mutable draft state; only explicit
  `freeze_working_evidence()` creates a versioned immutable package. Existing
  package snapshots and raw inputs are not updated automatically.
- Pre-existing `active_run.json`, `runs/`, and `tests/_tmp_phase3/` were left
  untouched.
