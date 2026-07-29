# SAXS detector Figure projection provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make partial detector Figure recovery explain exactly how many sampled pixels were retained or omitted.

**Architecture:** Keep the current deterministic detector projection and attach a small internal projection-count DTO. The main Figure recipe serializes only detached counts and status by existing frame index.

**Tech Stack:** Python, NumPy, pytest, existing SAXS Figure contracts and verification scripts.

---

### Task 1: Add the provenance regression

**Files:**
- Modify: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Write the failing test**
- [x] **Step 2: Run the test and confirm RED**

### Task 2: Add projection-count provenance

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_strain.py`

- [x] **Step 1: Return sampled/retained/non-finite counts from the private projection boundary**
- [x] **Step 2: Serialize detached per-frame provenance in the main Figure recipe**
- [x] **Step 3: Run GREEN and existing detector/Figure regressions**

### Task 3: Verify and checkpoint

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_strain.py`
- Modify: `tests/test_saxs_figure_evidence_binding.py`
- Add: this task's task/spec/plan documents.

- [x] **Step 1: Run structured verification and hygiene checks**
- [x] **Step 2: Run a fresh SAXS matrix with external basetemp**
- [x] **Step 3: Run storage report and clean dry-runs only**
- [x] **Step 4: Inspect the explicit allowlist and checkpoint**
