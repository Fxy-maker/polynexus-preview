# SAXS detector Figure dirty projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve finite detector pixels in strain Figure evidence when only some loaded 2D pixels are malformed.

**Architecture:** Keep the existing detector projection boundary and deterministic sampling. Convert the sampled image to a finite mask, return only original sampled coordinates with finite values, and retain the current unavailable path when no finite pixel remains.

**Tech Stack:** Python, NumPy, pytest, existing SAXS Figure contracts and verification scripts.

---

### Task 1: Add the detector dirty-data regression

**Files:**
- Modify: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Write the failing test**

Patch the detector reader at the Figure boundary with a 2D image containing
finite, `NaN`, and infinite pixels. Assert the 2D evolution definition keeps
the detector source and only finite sampled pixels, while the source
coordinates remain unchanged.

- [x] **Step 2: Run the test to verify RED**

Run the focused test with an external basetemp. It should fail because the
current projection rejects the whole image when any pixel is non-finite.

### Task 2: Implement the minimal projection change

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_strain.py`

- [x] **Step 1: Filter only non-finite sampled detector pixels**

Keep the current dimensionality and empty checks. After deterministic sampling,
retain only finite sampled values and their matching `pixel_x`/`pixel_y`
coordinates. Return `None` if the retained set is empty.

- [x] **Step 2: Run the focused test to verify GREEN**

Run the new regression and the existing detector/orientation and Figure
evidence tests.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_strain.py`
- Modify: `tests/test_saxs_figure_evidence_binding.py`
- Add: task, spec, and plan documents listed by the task card.

- [x] **Step 1: Run the structured verifier and hygiene checks**
- [x] **Step 2: Run the fresh SAXS matrix with an external basetemp**
- [x] **Step 3: Run storage report and clean dry-runs only**
- [x] **Step 4: Inspect the cumulative diff and create the explicit allowlist checkpoint**
