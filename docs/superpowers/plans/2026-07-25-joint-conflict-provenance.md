# Joint Conflict Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve exact source-run provenance for Joint conflicts and figures.

**Architecture:** Serialize existing `JointRunRecord` and `_run_evidence_context` data at the dataset boundary, then reuse the same serializer in figure recipes. Numeric calculations and shared figure lifecycle remain untouched.

**Tech Stack:** Python, pytest, SampleDB, FigureDefinition/Manifest.

---

### Task 1: Red tests

**Files:**
- Modify: `tests/test_joint_hub_dataset.py`
- Modify: `tests/test_joint_figure_provider.py`

- [ ] Assert a validation conflict contains source run IDs and evidence weights.
- [ ] Assert every Joint recipe contains the relevant batch/run provenance.
- [ ] Run the focused tests and observe the new assertions fail.

### Task 2: Dataset provenance

**Files:**
- Modify: `polynexus/core/joint/dataset.py`

- [ ] Add a JSON-safe run provenance serializer.
- [ ] Attach source mappings to each validation output without changing the
  existing `check`, `severity`, `passed`, `message`, or `details` fields.
- [ ] Run the Joint dataset tests.

### Task 3: Figure recipe provenance

**Files:**
- Modify: `polynexus/core/joint/figure_provider.py`

- [ ] Add batch-row provenance to the shared recipe builder.
- [ ] Preserve all existing figure IDs, roles, data values, and Manifest output.
- [ ] Run the Joint provider and provenance matrix.

### Task 4: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-25-joint-conflict-provenance.md`
- Create: `docs/acceptance/2026-07-25-joint-conflict-provenance.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [ ] Record exact test and verifier counts.
- [ ] Run `scripts/auto_commit.py` with the explicit file allowlist.
