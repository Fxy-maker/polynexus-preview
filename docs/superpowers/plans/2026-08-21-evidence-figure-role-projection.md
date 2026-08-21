# Evidence Figure Role Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve ARS-selected figure roles and actual producing techniques in `figure-index.json` while retaining unselected run outputs as diagnostics.

**Architecture:** Extend the packager's internal asset descriptors with bounded role, candidate-group, and technique provenance.  Candidate metadata overrides the default diagnostic descriptor only when it identifies the copied canonical SVG.  `figure-index.json`, the evidence-package DTO, GUI gallery, CLI, and ARS continue to consume the same existing index contract.

**Tech Stack:** Python 3.12, dataclasses, pathlib, JSON, pytest.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `polynexus/core/project_workflow/package.py` | Build provenance-bearing figure descriptors and project them into the index. |
| `tests/test_project_workflow_package.py` | Prove role, group, and technique projection at package creation. |
| `tests/test_ars_group_figure_candidates.py` | Prove ARS candidate package paths retain their selected role. |
| `docs/agent/tasks/2026-08-21-evidence-figure-role-projection.md` | Structured task contract and verification record. |

### Task 1: Add failing package projection regressions

**Files:**
- Modify: `tests/test_project_workflow_package.py`
- Modify: `tests/test_ars_group_figure_candidates.py`

- [ ] **Step 1: Write the minimal failing package test**

Create one completed DSC run and one completed IR run with SVG artifacts.  Pass
a `FigureCandidateSet` with the IR SVG in `main_candidates`, a second IR SVG
in `supporting_candidates`, and leave the DSC SVG unselected.

```python
index = json.loads((package.path / "figure-index.json").read_text(encoding="utf-8"))
by_svg = {entry["svg"]: entry for entry in index["figures"]}
assert by_svg["figures/ftir-main.svg"]["role"] == "manuscript_candidate"
assert by_svg["figures/ftir-main.svg"]["technique"] == "IR"
assert by_svg["figures/ftir-support.svg"]["role"] == "supporting_candidate"
assert by_svg["figures/dsc-output.svg"]["role"] == "diagnostic"
assert by_svg["figures/dsc-output.svg"]["technique"] == "DSC"
```

- [ ] **Step 2: Run the test and observe the expected failure**

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_workflow_package.py -k "candidate_role or figure_role"
```

Expected: failure because all entries currently contain `diagnostic` and the
first evidence technique.

### Task 2: Project declared figure roles into the shared index

**Files:**
- Modify: `polynexus/core/project_workflow/package.py`
- Test: `tests/test_project_workflow_package.py`
- Test: `tests/test_ars_group_figure_candidates.py`

- [ ] **Step 1: Add descriptor provenance**

Change internal figure descriptors to include `technique`, default `role`,
optional candidate `group`, and `writing_eligibility`.  `_asset_descriptors()`
receives the producing run's technique context rather than inferring one
package-wide value.  Its default remains:

```python
{
    "role": "diagnostic",
    "group": None,
    "writing_eligibility": "review_only",
    "technique": producing_technique.upper(),
}
```

- [ ] **Step 2: Overlay exact candidate-path metadata**

For every candidate source path, validate that it lies under the project figure
directory, then construct a descriptor that supplies:

```python
role = {
    "main_candidates": "manuscript_candidate",
    "supporting_candidates": "supporting_candidate",
}[bucket]
```

Copy candidate `technique` and one group ID only when explicitly supplied.
When PNG and SVG siblings share a logical figure directory, transfer the role
to the retained SVG.  Reject a same-source conflict instead of arbitrarily
choosing a role.

- [ ] **Step 3: Make `_canonical_figure_assets()` read descriptor provenance**

Replace its literal role/technique fields with the retained SVG descriptor's
validated values.  Preserve default `diagnostic` behavior for ordinary run
outputs and preserve `review_only` unless future public evidence contracts
provide a different eligibility.

- [ ] **Step 4: Run focused tests and ensure they pass**

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_workflow_package.py tests/test_ars_group_figure_candidates.py tests/test_evidence_package_view.py
```

Expected: selected candidates are layered correctly; index readers remain
compatible.

### Task 3: Record verification and create the local checkpoint

**Files:**
- Create: `docs/agent/tasks/2026-08-21-evidence-figure-role-projection.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`
- Create: `docs/acceptance/2026-08-21-evidence-figure-role-projection.md`

- [ ] **Step 1: Run structured verification**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-21-evidence-figure-role-projection.md --changed --types
git diff --check
```

- [ ] **Step 2: Replay the PA6 project read-only**

Run the existing `project-workflow analyze-project` command with selected
paths/groups where available, inspect `figure-index.json`, and record the role
and technique counts.  Do not modify external raw data or promote any metric.

- [ ] **Step 3: Commit only task files**

```powershell
python scripts/auto_commit.py --message "fix(evidence): preserve selected figure roles" --files polynexus/core/project_workflow/package.py tests/test_project_workflow_package.py tests/test_ars_group_figure_candidates.py docs/agent/tasks/2026-08-21-evidence-figure-role-projection.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md docs/acceptance/2026-08-21-evidence-figure-role-projection.md
```
