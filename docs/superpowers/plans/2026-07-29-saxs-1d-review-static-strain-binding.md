# SAXS 1D reviewer evidence static/strain binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thread the existing `saxs.1d` reviewer evidence projection through static and strain SAXS Figure providers.

**Architecture:** Reuse `configured_saxs_1d_review()` and `attach_saxs_figure_evidence()` from the temperature slice. Add no new review schema or source policy; only the static and strain provider handoff changes. The generic provider path is guarded to static/strain modes so `saxs.2d` is not accidentally consumed as a 1D review.

**Tech Stack:** Python, existing SAXS FigureDefinition providers, immutable source views, Pytest, Ruff, and the structured verifier.

---

### Task 1: Lock static and strain handoff with RED tests

**Files:**
- Modify: `tests/test_saxs_1d_review_evidence_binding.py`

- [x] **Step 1: Add static provider assertions**

Use the existing static Figure provider fixture shape and attach a complete
accepted `saxs.1d` payload whose `source_refs` match the loaded static source
paths. Assert the first static definition's `quality_provenance` has
`reason == "review_accepted"`, contains all source refs, and retains the
existing role. Add a partial-source static case asserting
`reason == "source_mismatch"`.

- [x] **Step 2: Add strain provider assertions**

Use the existing strain Figure provider fixture shape with two source paths.
Assert a complete accepted payload appears in the strain Figure evidence and
that a missing payload remains `review_missing`; keep the existing strain
publication roles unchanged.

- [x] **Step 3: Run RED**

```powershell
python -m pytest -q tests/test_saxs_1d_review_evidence_binding.py -o addopts= --basetemp=D:\PolyNexus_saxs_1d_review_static_strain_red
```

Expected: the new static/strain assertions fail because those providers do
not pass `scientific_review` yet, while the existing five temperature tests
continue to pass.

### Task 2: Thread static and strain provider handoff

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_static.py`
- Modify: `polynexus/core/saxs_engine/figure_strain.py`
- Modify: `polynexus/core/saxs_engine/figure_provider.py`

- [x] **Step 1: Pass the configured review to static Figures**

Import `configured_saxs_1d_review` beside the existing evidence helpers in
`figure_static.py`. Add
`scientific_review=configured_saxs_1d_review(engine_state)` to its existing
`attach_saxs_figure_evidence()` call. Do not alter the definitions, roles, or
source arrays.

- [x] **Step 2: Pass the configured review to strain Figures**

Import the same helper in `figure_strain.py` and pass it to the existing
strain attachment call. Keep frame order and all current role decisions
unchanged.

- [x] **Step 3: Guard the generic provider path**

At the generic attachment in `figure_provider.py`, pass the configured review
only when `mode_name in {"static", "strain"}`. Use `None` for other modes so
the existing temperature/specialized and future 2D routes cannot consume the
1D reviewer scope accidentally.

- [x] **Step 4: Run GREEN**

```powershell
python -m pytest -q tests/test_saxs_1d_review_evidence_binding.py tests/test_saxs_figure_evidence_binding.py -o addopts= --basetemp=D:\PolyNexus_saxs_1d_review_static_strain_green
```

Expected: all review-binding and existing Figure evidence tests pass.

### Task 3: Regression and checkpoint verification

**Files:**
- Modify: `docs/agent/tasks/2026-07-29-saxs-1d-review-static-strain-binding.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run the focused SAXS review matrix**

```powershell
$tests = @('tests/test_saxs_1d_review_evidence_binding.py','tests/test_saxs_figure_evidence_binding.py','tests/test_saxs_static_figure_panels.py','tests/test_saxs_strain_evidence_filtering.py','tests/test_saxs_workbench_series_evidence.py')
python -m pytest -q $tests -o addopts= --basetemp=D:\PolyNexus_saxs_1d_review_static_strain_matrix
```

- [x] **Step 2: Run the structured verifier and exact SAXS matrix**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-1d-review-static-strain-binding.md --changed --types
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests -o addopts= --basetemp=D:\PolyNexus_saxs_1d_review_static_strain_saxs_matrix
git diff --check
```

Only a final pytest summary with exit code `0` counts as a pass.

- [x] **Step 3: Run storage dry-run**

```powershell
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

Do not run `--apply` and do not include any test directory in the checkpoint.

- [x] **Step 4: Create the explicit checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(saxs): bind 1d review for static strain" --files polynexus/core/saxs_engine/figure_static.py polynexus/core/saxs_engine/figure_strain.py polynexus/core/saxs_engine/figure_provider.py tests/test_saxs_1d_review_evidence_binding.py docs/superpowers/specs/2026-07-29-saxs-1d-review-static-strain-binding-design.md docs/superpowers/plans/2026-07-29-saxs-1d-review-static-strain-binding.md docs/agent/tasks/2026-07-29-saxs-1d-review-static-strain-binding.md docs/agent/memory/active-work.md
```

Exclude `docs/agent/memory/current-state.md`, GUI files, `.superpowers`, and
all pre-existing scratch/test-storage paths.
