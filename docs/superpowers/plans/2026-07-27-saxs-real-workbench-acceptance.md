# SAXS Real Data and Workbench Acceptance Implementation Plan

> **For agentic workers:** This is an acceptance-only task. Do not alter SAXS
> scientific semantics while executing it.

**Goal:** Verify the implemented SAXS quality/evidence/export contracts against
real static, temperature, and strain data and record the remaining human gates.

**Architecture:** Use the existing core engine and shared figure lifecycle,
then inspect the mode-scoped SAXS export provenance and Workbench contracts.
All replay output is external temporary data; source fixtures and repository
generated outputs remain read-only.

**Tech Stack:** Python, pytest, PySide6 offscreen tests, JSON manifest checks,
PowerShell launcher diagnostics.

---

### Task 1: Replay real SAXS lifecycle

**Files:**
- Read: `tests/test_real_published_run_walkthrough.py`
- Read: real fixtures under `测试数据/saxs/`

- [x] Run `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_real_published_run_walkthrough.py -k 'saxs' -q` with an external basetemp.
- [x] Confirm static, temperature, and strain cases pass and that no output is written to the real fixture directories.

### Task 2: Verify real export provenance

**Files:**
- Read: `polynexus/core/saxs_export_bundle.py`
- Read: `polynexus/core/saxs.py`
- Diagnostic output: `C:\Temp\PolyNexus_saxs_stage9_real_bundle`

- [x] Run each real mode through `run_pipeline` and `export_bundle` into the external diagnostic root.
- [x] Assert each bundle is `ok`, each manifest registers `quality_evidence.json`, and mode-scoped evidence is preserved.
- [x] Record validation errors as gates rather than treating them as successful scientific publication.

### Task 3: Verify Results Workbench contracts

**Files:**
- Read: `tests/test_saxs_workbench_figure_contracts.py`
- Read: `tests/test_results_workbench_profiles.py`

- [x] Run both focused suites with `QT_QPA_PLATFORM=offscreen`.
- [x] Confirm all three SAXS modes expose mode-specific narrative, tabs, figure IDs, and fallback routing.

### Task 4: Verify the restart boundary

**Files:**
- Read: `scripts/launch_gui.py`

- [x] Run `python scripts/launch_gui.py --diagnose` after the checkpoint.
- [x] Confirm source root, branch, commit, interpreter, and imported package agree.
- [ ] Perform human visual review after a real GUI restart.

### Task 5: Release gate

**Files:**
- Update: task card, acceptance note, and durable memory.

- [ ] Obtain human scientific sign-off for real trends, quality downgrades,
  publication roles, and any future AI rescue policy.
- [ ] Run the structured verifier after the acceptance records are updated.
- [ ] Create the atomic local checkpoint with the explicit documentation allowlist.
