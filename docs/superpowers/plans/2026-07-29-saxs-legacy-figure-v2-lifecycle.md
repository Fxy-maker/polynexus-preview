# Legacy SAXS Figure V2 Lifecycle Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the legacy static/strain/temperature Figure-to-Manifest V2 lifecycle executable and regression-covered.

**Architecture:** Reuse the existing lightweight fixtures, provider builders, `build_v2_definition_artifact`, and `FigurePipeline`. Add no production adapter or consumer layer.

**Tech Stack:** Python 3.14, NumPy, pytest, FigurePipeline, V2 capability artifact.

---

### Task 1: Add the three-mode lifecycle acceptance regression

**Files:**

- Modify: `tests/test_saxs_temperature_figure_provider.py`

- [x] **Step 1: Add the existing-GREEN acceptance test**

```python
def test_legacy_saxs_v2_lifecycle_is_ready_for_all_modes(tmp_path) -> None:
    cases = (
        ("static", "saxs_static", build_saxs_figure_definitions(_saxs_provider_state(
            _batch_results=[
                _analyzed_saxs_frame("a", [0.1, 0.2], [10.0, 5.0]),
                _analyzed_saxs_frame("b", [0.1, 0.2], [9.0, 4.0]),
            ]
        ))),
        ("strain", "saxs_strain", build_saxs_figure_definitions(_saxs_provider_state(
            _strain_result=SimpleNamespace(strains=np.asarray([0.0, 25.0])),
            _q_list=[np.asarray([0.1, 0.2]), np.asarray([0.1, 0.2])],
            _I_list=[np.asarray([10.0, 5.0]), np.asarray([9.0, 4.0])],
            _conditions=[0.0, 25.0],
        ))),
        ("temperature", "temperature_saxs", build_saxs_temperature_definitions(
            TempSeriesResult(
                temperatures=np.asarray([30.0, 60.0]),
                L_array=np.asarray([12.0, 11.0]),
                lc_array=np.asarray([4.0, 3.0]),
                lc_effective_array=np.asarray([4.0, 3.0]),
                Q_star_array=np.asarray([100.0, 90.0]),
                Xc_array=np.asarray([0.4, 0.42]),
            ),
            (np.asarray([0.1, 0.2, 0.3]),) * 2,
            (np.asarray([10.0, 5.0, 2.0]),) * 2,
        )),
    )
    for mode, adapter, definitions in cases:
        assert definitions
        assert all(item.recipe["v2_adapter"] == adapter for item in definitions)
        assert all(
            build_v2_definition_artifact(item).capability["v2_runtime"] == "ready"
            for item in definitions
        )
        manifest = FigurePipeline().run(
            output_root=tmp_path,
            run_id=f"legacy-saxs-v2-{mode}",
            technique="saxs",
            definitions=(definitions[0],),
        )
        entry = manifest.figures[0]
        assert entry.status == "ready"
        assert entry.capability_report["v2_runtime"] == "ready"
        assert (
            tmp_path / "runs" / f"legacy-saxs-v2-{mode}"
            / entry.capability_report["v2_sidecar"]
        ).is_file()
```

- [x] **Step 2: Run the focused acceptance test**

Run: `python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k legacy_v2`

Expected: existing GREEN with one passing test; no production code is changed.

### Task 2: Verify the boundary and checkpoint

**Files:**

- Modify: task card, spec, and plan with actual evidence.

- [x] **Step 1: Run focused consumers**

Run: `python -m pytest -q tests/test_saxs_temperature_figure_provider.py tests/test_saxs_publication_pack_upgrade.py tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 2: Run structured and complete SAXS verification**

Run the exact verifier and PowerShell-expanded matrix in the task card; record
only completed commands with exit code 0 and final pytest summaries.

- [x] **Step 3: Run storage dry-run and diff hygiene**

Run `report --json`, `clean --older-than-hours 24` without `--apply`, and
`git diff --check`.

- [x] **Step 4: Create the allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "test(saxs): lock legacy figure v2 lifecycle" --files docs/agent/tasks/2026-07-29-saxs-legacy-figure-v2-lifecycle.md docs/superpowers/specs/2026-07-29-saxs-legacy-figure-v2-lifecycle-design.md docs/superpowers/plans/2026-07-29-saxs-legacy-figure-v2-lifecycle.md tests/test_saxs_temperature_figure_provider.py
```

Expected: one local commit with exactly the four listed files and no push or
parallel-workspace mutation.
