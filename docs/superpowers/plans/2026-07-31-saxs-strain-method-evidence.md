# SAXS Strain Method Evidence Diagnostic Figure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Project existing strain per-frame Porod, Kratky, invariant, and lamellar evidence into a diagnostic Figure without recalculation or promotion.

**Architecture:** Add a private provider helper beside the existing strain Figure builders. It reads `SAXSFrameView.condition`, `index`, `source_path`, and `analysis.metric_evidence`, creating detached nullable audit sources and finite plot sources. The helper is appended before the existing strain evidence attachment and does not alter existing definitions.

**Tech Stack:** Python, NumPy, immutable Figure contracts, pytest, repository verifier.

---

### Task 1: Write the strain method-evidence regression tests

**Files:**
- Create: `tests/test_saxs_strain_method_evidence.py`

- [ ] **Step 1: Add a three-frame strain engine fixture**

Build a `SimpleNamespace` engine with three finite q/I frames, strain
conditions `0.0`, `25.0`, and `50.0`, source paths, publication-eligible
parameters, and per-frame evidence. Give one frame a missing value and one
non-finite value so audit and finite projection behavior are observable.

- [ ] **Step 2: Add the Figure contract test**

Assert `saxs.strain.method_evidence`, four audit sources, nullable values,
source paths, levels, reason codes, finite plot pairs, diagnostic role, recipe
flags, strict JSON, V2 readiness, and input detachment.

- [ ] **Step 3: Add the no-evidence regression**

Assert the legacy strain Figure set does not contain the new Figure when all
frame `metric_evidence` mappings are empty.

- [ ] **Step 4: Run RED**

```powershell
python -m pytest -q tests/test_saxs_strain_method_evidence.py -o addopts=
```

Expected result: the new Figure lookup fails because the provider does not yet
emit `saxs.strain.method_evidence`.

### Task 2: Implement the minimal strain provider projection

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_strain.py`

- [ ] **Step 1: Add method metadata and nullable reason-code projection**

Define the four method labels/units/colors and read only each frame's existing
mapping. Convert non-finite strain/value tokens to `None`, preserve the frame
index and source path, and serialize reason-code sequences with the existing
pipe-delimited convention.

- [ ] **Step 2: Build audit and finite renderer sources**

Always append an audit source when any supported mapping exists. Append a plot
source and scatter object only when at least two finite strain/value pairs
exist; this is a renderer validity constraint, not a scientific threshold.

- [ ] **Step 3: Append the diagnostic Figure**

Create the four-panel `saxs.strain.method_evidence` definition with
`publication_role="diagnostic"`, the recipe flags from the spec, and
`v2_adapter="saxs_strain"`. Add it to the existing definitions before sorting
and evidence attachment.

- [ ] **Step 4: Run GREEN**

```powershell
python -m pytest -q tests/test_saxs_strain_method_evidence.py -o addopts=
```

Expected result: all new tests pass.

### Task 3: Verify and checkpoint the atomic task

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_strain.py`
- Create: `tests/test_saxs_strain_method_evidence.py`
- Create: task/spec/plan/acceptance files listed in the task card

- [ ] **Step 1: Run focused strain and structured checks**

Run the focused test, relevant strain/figure evidence regression, and the task
verifier. Record exact counts and any pre-existing baseline limitation.

- [ ] **Step 2: Run the exact SAXS matrix and storage dry-run**

Run the explicit SAXS file-list matrix with a complete summary requirement,
then storage report and non-destructive clean. Never run `--apply`.

- [ ] **Step 3: Review the explicit allowlist and checkpoint**

Leave `active-work.md`, `current-state.md`, parallel EDF files, NMR files,
scratch, and test directories untouched. Then run:

```powershell
python scripts/auto_commit.py --message "feat(saxs): add strain method evidence figure" --files polynexus/core/saxs_engine/figure_strain.py tests/test_saxs_strain_method_evidence.py docs/agent/tasks/2026-07-31-saxs-strain-method-evidence.md docs/superpowers/specs/2026-07-31-saxs-strain-method-evidence-design.md docs/superpowers/plans/2026-07-31-saxs-strain-method-evidence.md docs/acceptance/2026-07-31-saxs-strain-method-evidence.md
```

Expected result: one local checkpoint commit, with no push, merge, or cleanup
apply.
