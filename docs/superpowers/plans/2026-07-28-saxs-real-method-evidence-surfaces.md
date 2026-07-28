# Real SAXS Method-Evidence Surfaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify real SAXS method-evidence consistency across final parameters,
Figure provenance, and Export without changing analysis behavior.

**Architecture:** The test replays existing fixtures through the public SAXS
engine, treats the final parameter `metric_evidence` as authoritative, and
checks exact equality at Export plus field-preserving subset semantics in the
compact Figure projection. All outputs use an external pytest root.

**Tech Stack:** Python, pytest, strict JSON, SAXS Figure Manifest, Export bundle,
and repository task verifier.

---

### Task 1: Add the real method-evidence contract regression

**Files:**
- Create: `tests/test_saxs_real_method_evidence_surfaces.py`

- [x] **Step 1: Write the real fixture and projection assertions**

  Resolve the existing Static EDF, Temperature directory, and Strain
  directory. For each available mode, assert strict JSON for the final
  `metric_evidence`; compare Export exactly; compare each Figure metric mapping
  as a recursive field-preserving subset.

- [x] **Step 2: Run the focused real regression**

```powershell
python -m pytest -q tests/test_saxs_real_method_evidence_surfaces.py -vv --basetemp C:\Temp\PolyNexus_saxs_real_method_evidence_surfaces
```

Expected: three real modes pass, or unavailable fixtures are explicit skips.

### Task 2: Bind the authoritative series-point frame evidence

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_evidence.py`

- [x] **Step 1: Confirm the RED mismatch**

The fresh RED run passed Static and failed Temperature and Strain because the
Figure frame record read `_batch_results`, while Export and final parameters
read the corresponding series point.

- [x] **Step 2: Apply the minimal binding fix**

Temperature uses the existing point `source_index`; Strain uses existing frame
order. No metric calculation or scientific threshold is introduced.

- [x] **Step 3: Run focused GREEN**

`3 passed in 41.92s`.

### Task 3: Verify and checkpoint

**Files:**
- Modify: this task card, acceptance record, plan, and `active-work.md`.

- [x] **Step 1: Run the structured verifier and diff check**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-real-method-evidence-surfaces.md --changed --types
git diff --check
```

- [x] **Step 2: Run the test-storage dry-run**

```powershell
python scripts/test_storage.py report --json
```

Record that the command is dry-run and do not remove existing artifacts.

- [x] **Step 3: Create the explicit allowlist checkpoint**

Use `scripts/auto_commit.py` with exactly the task card allowlist. Do not stage
`current-state.md`, datasets, generated outputs, or scratch directories.
