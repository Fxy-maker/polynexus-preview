# Current-head Real SAXS Boundary Re-audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline execution). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh real SAXS lifecycle and PAD8 2D boundary evidence on current HEAD.

**Architecture:** Execute the two existing read-only pytest contracts in isolated C: basetemps, then preserve their exact output in durable acceptance notes. No production code is in scope.

**Tech Stack:** Python, pytest, C: external basetemps, existing SAXS fixtures, Markdown task artifacts.

---

### Task 1: Run the real PAD8 2D boundary

**Files:**
- Read: `tests/test_saxs_real_2d_scientific_acceptance.py`

- [x] **Step 1: Execute the PAD8 contract**

```powershell
python -m pytest -q tests/test_saxs_real_2d_scientific_acceptance.py -vv --basetemp=C:\Temp\PolyNexus_saxs_real_boundary_pad8_current
```

Record only a complete pytest summary and exit code as pass evidence.

### Task 2: Run real Static/Temperature/Strain lifecycle

**Files:**
- Read: `tests/test_real_published_run_walkthrough.py`

- [x] **Step 1: Execute the SAXS selector**

```powershell
python -m pytest -q tests/test_real_published_run_walkthrough.py -k saxs -vv --basetemp=C:\Temp\PolyNexus_saxs_real_boundary_lifecycle_current
```

Require a complete summary and exit code before recording automated lifecycle
evidence.

### Task 3: Record and checkpoint

**Files:**
- Modify: this task card and plan
- Create: `docs/acceptance/2026-07-30-saxs-real-boundary-current-head-reaudit.md`

- [ ] **Step 1: Record actual results and limits**

Keep detector calibration, mask validity, orientation meaning, and publication
approval as human gates even when both shards pass.

- [ ] **Step 2: Run task/diff checks**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-real-boundary-current-head-reaudit.md --changed --types
git diff --check
```

- [ ] **Step 3: Create the explicit documentation checkpoint**

Use `scripts/auto_commit.py` with only the four allowlisted documents.
