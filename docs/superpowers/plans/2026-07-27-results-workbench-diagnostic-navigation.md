# Results Workbench Diagnostic Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every structured Results Workbench profile navigate to an existing diagnostic figure in the active manifest Gallery.

**Architecture:** Keep profile metadata immutable and technique-neutral. Add exact and prefix candidate resolution to `WorkbenchFigureLink`; MainWindow passes the active Gallery ID set to that resolver, while the Gallery remains the sole source of selectable figure IDs. Add only navigation metadata and regressions; do not alter provider roles or scientific calculations.

**Tech Stack:** Python 3.14, PySide6, pytest, existing Results Workbench and manifest Gallery services.

---

### Task 1: Lock the link-resolution and profile contracts with TDD

**Files:**
- Modify: `tests/test_results_workbench_profiles.py`
- Modify: `tests/test_saxs_workbench_figure_contracts.py`
- Modify: `tests/test_waxs_workbench_figure_contracts.py`
- Modify: `tests/test_dsc_workbench_figure_contracts.py`
- Modify: `tests/test_ir_nmr_joint_workbench_profiles.py`

- [x] **Step 1: Write the failing tests**

Add assertions for immutable exact/prefix resolution and one diagnostic link
per structured profile:

```python
def test_workbench_figure_link_resolves_exact_candidates_before_prefixes():
    link = WorkbenchFigureLink(
        "nmr.frame.deconvolution.001",
        "RESULTS_WORKBENCH_FIGURE_DIAGNOSTIC",
        "diagnostic",
        ("nmr.frame.deconvolution.000",),
        ("nmr.frame.deconvolution.",),
    )
    assert link.resolve({"nmr.frame.deconvolution.003", "nmr.frame.deconvolution.001"}) == "nmr.frame.deconvolution.001"


def test_workbench_figure_link_resolves_prefixes_deterministically():
    link = WorkbenchFigureLink(
        "nmr.frame.deconvolution.001",
        "RESULTS_WORKBENCH_FIGURE_DIAGNOSTIC",
        "diagnostic",
        prefixes=("nmr.frame.deconvolution.",),
    )
    assert link.resolve({"nmr.frame.deconvolution.010", "nmr.frame.deconvolution.002"}) == "nmr.frame.deconvolution.002"
```

- [x] **Step 2: Run the focused tests and verify RED**

```powershell
python -m pytest --basetemp=C:\Temp\PolyNexus_workbench_diag_red tests/test_results_workbench_profiles.py tests/test_ir_nmr_joint_workbench_profiles.py tests/test_saxs_workbench_figure_contracts.py tests/test_waxs_workbench_figure_contracts.py tests/test_dsc_workbench_figure_contracts.py -q
```

Expected result: failures for the missing `prefixes`/`resolve` contract and
missing diagnostic links; no unrelated collection failures.

### Task 2: Implement immutable candidate resolution and profile metadata

**Files:**
- Modify: `polynexus/gui/results_workbench_profiles.py`

- [x] **Step 1: Add the minimal resolver**

Extend `WorkbenchFigureLink` with `prefixes: tuple[str, ...] = ()` and add a
resolver that checks exact candidates in declared order, then sorted prefix
matches, and finally returns `self.key` when no Gallery ID matches.

- [x] **Step 2: Add diagnostic links to each structured profile**

Use these existing provider IDs/prefixes without changing current main/support
link order:

```text
saxs.static.frame.000.correlation       prefix saxs.static.frame.
saxs.temperature.evidence.000          prefix saxs.temperature.evidence.
saxs.strain.low-q.diagnostic
dsc.standard.integration.diagnostic
dsc.isothermal.fit.diagnostic
dsc.nonisothermal.kinetics.diagnostic
waxs.static.fit.diagnostic
waxs.temperature.sequence.diagnostic
waxs.strain.sequence.diagnostic
ir.frame.comparison.001                 prefix ir.frame.comparison.
ir.temperature_2d.synchronous-correlation
ir.mapping.invalid-pixels
nmr.frame.deconvolution.001             prefix nmr.frame.deconvolution.
joint.series.coverage
```

Use role=`diagnostic`; this is navigation metadata only and does not alter the
FigureDefinition publication role.

### Task 3: Route links through the active Gallery resolver

**Files:**
- Modify: `polynexus/gui/main_window_output_mixin.py`
- Modify: `tests/test_saxs_workbench_figure_contracts.py`

- [x] **Step 1: Write the routing regression**

Add a fake Gallery exposing `{"nmr.frame.deconvolution.003"}` and assert that
clicking the diagnostic link selects that available ID. Add a second assertion
that an exact candidate beats a prefix match.

- [x] **Step 2: Implement the routing call**

When a profile link and Gallery ID set are available, call
`link.resolve(available_ids)`; retain the existing requested key when no match
exists so Gallery behavior remains a no-op.

### Task 4: Verify, document, and checkpoint

**Files:**
- Modify: this task card
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run GREEN focused matrix**

```powershell
python -m pytest --basetemp=C:\Temp\PolyNexus_workbench_diag_green tests/test_results_workbench_profiles.py tests/test_ir_nmr_joint_workbench_profiles.py tests/test_saxs_workbench_figure_contracts.py tests/test_waxs_workbench_figure_contracts.py tests/test_dsc_workbench_figure_contracts.py tests/test_results_export_contracts.py -q
```

- [x] **Step 2: Run the structured verifier and diff check**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-results-workbench-diagnostic-navigation.md --changed --types
git diff --check
```

Record exact counts and limitations; do not reuse an older full/boundary run.

- [ ] **Step 3: Create the explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(gui): expose diagnostic figure navigation" --files polynexus/gui/results_workbench_profiles.py polynexus/gui/main_window_output_mixin.py tests/test_results_workbench_profiles.py tests/test_ir_nmr_joint_workbench_profiles.py tests/test_saxs_workbench_figure_contracts.py tests/test_waxs_workbench_figure_contracts.py tests/test_dsc_workbench_figure_contracts.py docs/agent/tasks/2026-07-27-results-workbench-diagnostic-navigation.md docs/superpowers/specs/2026-07-27-results-workbench-diagnostic-navigation-design.md docs/superpowers/plans/2026-07-27-results-workbench-diagnostic-navigation.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

The command must not include pre-existing scratch or unrelated untracked files.
