# SAXS azimuthal Figure projection provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explain partial azimuthal chi/I Figure recovery with deterministic pair counts.

**Architecture:** Keep the existing finite-pair projection and attach a small per-frame count mapping to the existing azimuthal Figure recipe.

**Tech Stack:** Python, NumPy, pytest, existing SAXS Figure contracts and verification scripts.

---

### Task 1: Add the azimuthal provenance regression

**Files:**
- Modify: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Write the failing test**
- [x] **Step 2: Run the test and confirm RED**

### Task 2: Add detached chi/I projection counts

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_strain.py`

- [x] **Step 1: Count aligned, retained, and non-finite pairs**
- [x] **Step 2: Add the counts to the azimuthal recipe parameters**
- [x] **Step 3: Run GREEN and existing orientation/Figure regressions**

### Task 3: Verify and checkpoint

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_strain.py`
- Modify: `tests/test_saxs_figure_evidence_binding.py`
- Add: this task's task/spec/plan documents.

- [x] **Step 1: Run structured verification and hygiene checks**
- [x] **Step 2: Run a fresh SAXS matrix with external basetemp**
- [x] **Step 3: Run storage report and clean dry-runs only**
- [x] **Step 4: Inspect the allowlist and checkpoint**

### Verification record

- RED: both new regressions failed on the absent recipe field.
- GREEN/focused matrix: `59 passed`.
- Structured verifier: quality `287 passed`, preprocessing `106 passed`.
- Fresh SAXS matrix: `545 passed, 6 warnings` in `289.88s`.
- Storage dry-run: `350` artifacts; `57` eligible, `9` process referenced,
  `284` younger than retention; removed `0`.
