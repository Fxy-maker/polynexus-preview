# Full Software Release Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish requirement-by-requirement, evidence-backed release status for every PolyNexus technique and mode.

**Architecture:** Keep this audit outside scientific engine behavior. Existing focused tests, real-fixture walkthroughs, GUI diagnostics, and verifier output are collected into one acceptance note; each result is labeled pass, limitation, or human gate. The task does not change thresholds, providers, or AI policy.

**Tech Stack:** Python 3.12, pytest, PySide6, PowerShell, `scripts/verify.py`, Markdown task/memory/acceptance records.

---

### Task 1: Reproduce the known WAXS publication boundary

**Files:**
- Read: `tests/test_waxs_publication_cutover.py`
- Read: `tests/test_waxs_publication_static_provider.py`
- Read: `tests/test_waxs_publication_temperature_provider.py`
- Read: `tests/test_waxs_publication_strain_provider.py`
- Read: `tests/test_waxs_workbench_figure_contracts.py`
- Read: `tests/test_waxs_figure_provider.py`
- Read: `tests/test_waxs_figure_document.py`

- [x] **Step 1: Run the dedicated WAXS publication matrix**

Run with an isolated basetemp:

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\PolyNexus.pytest_tmp_waxs_pub_matrix'
python -m pytest -q tests/test_waxs_publication_cutover.py tests/test_waxs_publication_temperature_provider.py tests/test_waxs_publication_strain_provider.py tests/test_waxs_publication_static_provider.py tests/test_waxs_workbench_figure_contracts.py tests/test_waxs_figure_provider.py tests/test_waxs_figure_document.py
```

Expected current evidence: `30 passed`.

- [x] **Step 2: Record the result without changing WAXS code**

The focused matrix passed on 2026-07-27. The previous full-suite failure is
therefore retained as historical full-run evidence until a fresh full command
proves otherwise.

### Task 2: Verify the shared AI safety boundary

**Files:**
- Read: `tests/test_preprocess_cross_technique_matrix.py`
- Read: `tests/test_preprocess_ai_off_compat.py`
- Read: `tests/test_preprocess_fault_injection.py`

- [x] **Step 1: Run the cross-technique matrix**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\PolyNexus.pytest_tmp_release_ai2'
python -m pytest -q tests/test_preprocess_cross_technique_matrix.py tests/test_preprocess_ai_off_compat.py tests/test_preprocess_fault_injection.py -vv
```

Expected current evidence: `25 passed`; Joint remains explicitly outside
single-technique preprocessing and is report-level AI review only.

- [x] **Step 2: Keep the scientific boundary explicit**

No external model call, automatic promotion, new threshold, or scientific
sign-off is inferred from these contract tests.

### Task 3: Run bounded lifecycle and real-fixture shards

**Files:**
- Read: `tests/test_real_published_run_walkthrough.py`
- Read: `tests/test_dsc_lifecycle_closure.py`
- Read: `tests/test_waxs_lifecycle_closure.py`
- Read: `tests/test_ir_lifecycle_closure.py`
- Read: `tests/test_nmr_lifecycle_closure.py`
- Read: `tests/test_joint_lifecycle_closure.py`
- Create: `docs/acceptance/2026-07-27-full-software-release-audit.md`

- [x] **Step 1: Run one bounded shard at a time**

Use a different dedicated `--basetemp` for each shard. Run the real walkthrough
and lifecycle files separately so a slow scientific engine is attributable to
one mode and cannot be mistaken for a green combined command.

- [x] **Step 2: Classify each result**

For each mode, record one of `automated-pass`, `diagnostic-only`, `fixture-
missing`, `bounded-timeout`, or `human-review`. Preserve the exact test count,
failure name, and timeout duration.

- [x] **Step 3: Inspect the acceptance note**

Confirm that every objective mode appears exactly once and that diagnostic-only
or assignment-limited output is not promoted to a normal-science release role.

### Task 4: Restart and visually inspect the canonical GUI

**Files:**
- Read: `scripts/launch_gui.py`
- Create: temporary screenshot outside the repository
- Update: `docs/acceptance/2026-07-27-full-software-release-audit.md`

- [x] **Step 1: Launch from the canonical worktree**

```powershell
Set-Location D:\PolyNexus
python scripts/launch_gui.py --diagnose
```

Then restart the GUI from the same worktree and inspect the default empty state,
SAXS static/temperature/strain navigation, Results Workbench, Gallery, Editor,
Export, and History routes. Do not use an isolated worktree as the canonical
GUI source.

- [x] **Step 2: Capture visual evidence**

Save screenshots only under the OS temp directory. Record the path and the
inspected state; screenshots are evidence for human review and do not replace
scientific approval.

- [ ] **Step 3: Record unresolved visual gates**

If a route cannot be exercised without real input or a user decision, record
the exact missing prerequisite rather than marking it passed.

### Task 5: Run the full verifier and close the audit record

**Files:**
- Modify: `docs/acceptance/2026-07-27-full-software-release-audit.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/tasks/2026-07-27-full-software-release-audit.md`

- [x] **Step 1: Run the repository verifier with a dedicated basetemp**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\PolyNexus.pytest_tmp_release_full'
python scripts/verify.py --changed --types --full --boundary
```

Record exact output. The fresh run completed with `2767 passed, 10 warnings`
and the selected boundary audit passed.

- [x] **Step 2: Reconcile durable state**

Update the task card, plan, acceptance note, and memory with the same counts,
limitations, and next action. Do not delete unrelated scratch files or fold
them into the allowlist.

- [x] **Step 3: Create an allowlisted checkpoint**

After the documentation verifier passes, use:

```powershell
python scripts/auto_commit.py --message "docs(release): record full software audit" --files docs/agent/tasks/2026-07-27-full-software-release-audit.md docs/superpowers/plans/2026-07-27-full-software-release-audit.md docs/acceptance/2026-07-27-full-software-release-audit.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

Do not push, merge, deploy, or mark the overall goal complete while any human
release gate remains open.
