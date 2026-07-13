# DSC Publication Figure Packs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver editable, evidence-gated DSC Main/SI/Diagnostics figure packs for standard scans, isothermal crystallisation, and non-isothermal kinetics.

**Architecture:** Start the implementation branch from the latest `main` so DSC consumes the merged FigureDefinition, Figure Document v2, editor, publisher, audit and gallery lifecycle without importing the historical PR #9 chain. Selectively reuse only the DSC provider and test changes from the old isolated worktree. Add a DSC-only provider dispatcher plus one provider module per DSC experiment mode. `DSCEngine.build_figure_definitions()` becomes the single production projection from completed DSC results; `plot()` publishes definitions through `FigureProductionPublisher` with a DSC publication profile and returns an explicit empty result when no definition is available.

**Tech Stack:** Python 3.12, NumPy, Matplotlib renderer through shared figure pipeline, pytest, existing PySide chart editor.

**Mainline adaptation:** The current shared contract stores panel labels as
`PanelDefinition.panel_label` and does not expose a `FigureDefinition` display
order field. DSC providers persist deterministic display order in recipe
metadata and use the shared panel-label field. The DSC slice adds a
`dsc_publication` output profile that preserves the existing default profile
while enabling manifest-backed 600-DPI TIFF assets.

---

## File structure

- Create: `polynexus/core/dsc_engine/figure_common.py` — immutable result views, finite-value helpers, DSC eligibility and common FigureDefinition builders.
- Create: `polynexus/core/dsc_engine/figure_standard.py` — standard scan and multi-scan comparison recipes.
- Create: `polynexus/core/dsc_engine/figure_isothermal.py` — Avrami recipes.
- Create: `polynexus/core/dsc_engine/figure_nonisothermal.py` — non-isothermal conversion and kinetics recipes.
- Create: `polynexus/core/dsc_engine/figure_provider.py` — mode dispatcher and deterministic role ordering.
- Modify: `polynexus/core/dsc.py` — FigureDefinition provider and manifest-backed production cutover.
- Modify: `polynexus/plotting/sci_style.py` — add only DSC labels required by the audit.
- Test: `tests/test_dsc_publication_standard_provider.py`.
- Test: `tests/test_dsc_publication_isothermal_provider.py`.
- Test: `tests/test_dsc_publication_nonisothermal_provider.py`.
- Test: `tests/test_dsc_publication_cutover.py`.
- Test: `tests/eval/test_dsc_publication_real_data.py`.
- Modify: `docs/superpowers/specs/2026-07-11-dsc-publication-figure-packs-design.md` only if implementation reveals a genuine specification contradiction.

### Task 1: Create the DSC implementation worktree from the latest main

**Files:**
- Create: isolated worktree `codex/dsc-publication-packs-v2` based on `origin/main`.
- Import: the DSC design and implementation plan documents only.

- [ ] **Step 1: Create the isolated branch and import the approved specification**

Run:

```powershell
git worktree add C:\Users\Fan Xuyi\.config\superpowers\worktrees\PolyNexus\dsc-publication-figure-packs -b codex/dsc-publication-figure-packs codex/saxs-publication-figure-packs
git -C C:\Users\Fan Xuyi\.config\superpowers\worktrees\PolyNexus\dsc-publication-figure-packs cherry-pick 36069fa
```

Expected: the worktree contains `polynexus/core/figures/`, the SAXS publisher/editor implementation, and the DSC design spec.

- [ ] **Step 2: Verify the inherited foundation before DSC changes**

Run:

```powershell
pytest -q tests/test_figure_production.py tests/test_figure_document.py tests/test_figure_publication_audit.py tests/test_chart_editor*.py
```

Expected: PASS. Do not edit shared lifecycle code in this task.

- [ ] **Step 3: Commit only if the cherry-pick produces a conflict resolution**

```powershell
git status --short
```

Expected: clean worktree; otherwise commit the minimal conflict resolution with `chore: prepare DSC figure-pack worktree`.

### Task 2: Build immutable DSC views and eligibility gates

**Files:**
- Create: `polynexus/core/dsc_engine/figure_common.py`.
- Test: `tests/test_dsc_publication_standard_provider.py`.

- [ ] **Step 1: Write failing tests for finite values and Main eligibility**

```python
def test_low_quality_or_baseline_sensitive_scan_is_not_main() -> None:
    view = _scan_view(quality_score=0.35, quality_flags=["baseline_unstable"])
    assert classify_dsc_scan_eligibility(view).highest_role == "diagnostic"

def test_valid_thermogram_is_main_without_recomputing_parameters() -> None:
    view = _scan_view(Tm_peak_C=181.2, DHm_Jg=82.4, Xc_pct=43.1)
    assert classify_dsc_scan_eligibility(view).highest_role == "main"
    assert view.parameters["Tm_peak_C"] == 181.2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
pytest -q tests/test_dsc_publication_standard_provider.py -k eligibility
```

Expected: FAIL because `figure_common` and `classify_dsc_scan_eligibility` do not exist.

- [ ] **Step 3: Implement the common projection layer**

```python
@dataclass(frozen=True)
class DSCScanView:
    index: int
    label: str
    temperature_C: tuple[float, ...]
    heat_flow_W_g: tuple[float, ...]
    parameters: Mapping[str, Any]
    quality_score: float
    quality_flags: tuple[str, ...]

def classify_dsc_scan_eligibility(view: DSCScanView) -> FigureEligibilityDecision:
    flags = {str(flag).strip().lower() for flag in view.quality_flags}
    if flags & {"baseline_unstable", "integration_failed", "analysis_error"}:
        return FigureEligibilityDecision("diagnostic", ("analysis_quality_failure",))
    if not np.isfinite(view.quality_score) or view.quality_score < 0.50:
        return FigureEligibilityDecision("si", ("low_quality_score",))
    if len(view.temperature_C) < 5 or len(view.heat_flow_W_g) < 5:
        return FigureEligibilityDecision("diagnostic", ("insufficient_curve_points",))
    return FigureEligibilityDecision("main", ("quality_ok",))
```

`scan_views_from_engine(engine)` must copy `DSCResult.T`, `DSCResult.HF`, `DSCResult.parameters`, `quality_score` and `quality_flags`; it must not call `analyze_scan`, `analyze_kinetics`, baseline correction or peak fitting.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
pytest -q tests/test_dsc_publication_standard_provider.py -k "eligibility or immutable"
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add polynexus/core/dsc_engine/figure_common.py tests/test_dsc_publication_standard_provider.py
git commit -m "feat(dsc): add publication figure eligibility views"
```

### Task 3: Implement standard-scan and multi-sample DSC recipes

**Files:**
- Create: `polynexus/core/dsc_engine/figure_standard.py`.
- Modify: `polynexus/plotting/sci_style.py`.
- Test: `tests/test_dsc_publication_standard_provider.py`.

- [ ] **Step 1: Write failing recipe tests**

```python
def test_single_scan_main_contains_thermogram_and_only_valid_quantitative_events() -> None:
    definitions = build_standard_dsc_figure_definitions(_standard_engine(valid_xc=True))
    main = _definition(definitions, "dsc.standard.thermogram")
    assert main.publication_role == "main"
    assert {panel.panel_id for panel in main.layout.panels} == {"thermogram", "quantitative"}
    assert "Xc_pct" in _source(main, "dsc-standard-parameters").values

def test_low_confidence_xc_is_omitted_from_main_but_preserved_in_diagnostics() -> None:
    definitions = build_standard_dsc_figure_definitions(_standard_engine(valid_xc=False))
    assert "dsc.standard.thermogram" in {item.figure_id for item in definitions}
    assert "dsc.standard.integration.diagnostic" in {item.figure_id for item in definitions}
    assert all("Xc" not in item.title for item in definitions if item.publication_role == "main")
```

- [ ] **Step 2: Run failing tests**

```powershell
pytest -q tests/test_dsc_publication_standard_provider.py -k "single_scan or low_confidence_xc"
```

Expected: FAIL because `figure_standard` does not exist.

- [ ] **Step 3: Implement deterministic figure definitions**

Create `build_standard_dsc_figure_definitions(engine) -> tuple[FigureDefinition, ...]` with these stable IDs:

```python
STANDARD_MAIN_ID = "dsc.standard.thermogram"
COMPARISON_MAIN_ID = "dsc.comparison.thermal-events"
INTEGRATION_DIAGNOSTIC_ID = "dsc.standard.integration.diagnostic"

def _event_objects(view: DSCScanView, panel_id: str) -> tuple[dict[str, Any], ...]:
    event_keys = (("Tg_C", "Tg"), ("Tcc_peak_C", "Tcc"), ("Tm_peak_C", "Tm"), ("Tc_peak_C", "Tc"))
    return tuple(
        {"id": f"{panel_id}-{name.lower()}", "type": "line", "panel_id": panel_id,
         "orientation": "vertical", "x": float(value),
         "style": {"color": "#D55E00", "line_width": 0.8, "line_style": "--"}}
        for key, name in event_keys
        if np.isfinite(value := _finite_parameter(view, key))
    )
```

Use a two-panel main layout only when at least one of `DHm_Jg`, `DHc_Jg` or `Xc_pct` is valid and not baseline-sensitive; otherwise emit a one-panel thermogram Main. For two or more Main-eligible scans emit the comparison figure with heat-flow overlays and a three-or-more-point event/enthalpy comparison panel. Emit raw/baseline/integration evidence only as SI or Diagnostics.

Add exact audit labels to `AXIS_LABELS`: `Temperature (°C)`, `Heat flow (W g⁻¹)`, `Enthalpy (J g⁻¹)`, `Crystallinity (%)`.

- [ ] **Step 4: Verify definition and editable pipeline publication**

```powershell
pytest -q tests/test_dsc_publication_standard_provider.py tests/test_figure_production.py
```

Expected: PASS, including `FigurePipeline().run(...)` producing object-editable PDF/SVG/PNG/TIFF assets.

- [ ] **Step 5: Commit**

```powershell
git add polynexus/core/dsc_engine/figure_standard.py polynexus/plotting/sci_style.py tests/test_dsc_publication_standard_provider.py
git commit -m "feat(dsc): add standard publication figure recipes"
```

### Task 4: Implement isothermal DSC/Avrami recipes

**Files:**
- Create: `polynexus/core/dsc_engine/figure_isothermal.py`.
- Test: `tests/test_dsc_publication_isothermal_provider.py`.

- [ ] **Step 1: Write failing Avrami gate tests**

```python
def test_valid_avrami_fit_creates_main_and_keeps_full_series_in_si() -> None:
    definitions = build_isothermal_dsc_figure_definitions(_isothermal_engine(r_squared=0.97))
    assert _definition(definitions, "dsc.isothermal.avrami").publication_role == "main"
    assert _definition(definitions, "dsc.isothermal.series").publication_role == "si"

def test_invalid_avrami_never_becomes_main() -> None:
    definitions = build_isothermal_dsc_figure_definitions(_isothermal_engine(r_squared=0.42))
    assert "dsc.isothermal.avrami" not in {item.figure_id for item in definitions if item.publication_role == "main"}
    assert "dsc.isothermal.fit.diagnostic" in {item.figure_id for item in definitions}
```

- [ ] **Step 2: Run failing tests**

```powershell
pytest -q tests/test_dsc_publication_isothermal_provider.py
```

Expected: FAIL because the provider is absent.

- [ ] **Step 3: Implement Avrami recipes**

`build_isothermal_dsc_figure_definitions(engine)` must read `engine._kinetics_data["avrami"]` and `engine._kinetics_data["avrami_series"]`. A fit is Main-eligible only when `t_data`, `Xt_data` and `Xt_fit` have the same length of at least five, all values are finite, `0 < Xt_data < 1` has at least three points, `n`, `k`, `t_half_min`, and `r_squared` are finite, `r_squared >= 0.90`, and `quality_flags` is empty.

Use stable IDs `dsc.isothermal.avrami`, `dsc.isothermal.series`, and `dsc.isothermal.fit.diagnostic`. The Main definition contains conversion-time data and fitted curve as independent plot-series objects; it may include a temperature-trend panel only with three valid isothermal fits. Preserve all fits, residuals and excluded segments outside Main.

- [ ] **Step 4: Run focused tests and audit**

```powershell
pytest -q tests/test_dsc_publication_isothermal_provider.py tests/test_figure_publication_audit.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add polynexus/core/dsc_engine/figure_isothermal.py tests/test_dsc_publication_isothermal_provider.py
git commit -m "feat(dsc): add isothermal publication figure recipes"
```

### Task 5: Implement non-isothermal DSC recipes

**Files:**
- Create: `polynexus/core/dsc_engine/figure_nonisothermal.py`.
- Test: `tests/test_dsc_publication_nonisothermal_provider.py`.

- [ ] **Step 1: Write failing quality-gate tests**

```python
def test_conversion_curves_are_main_and_unqualified_kinetics_are_not() -> None:
    definitions = build_nonisothermal_dsc_figure_definitions(_nonisothermal_engine(kissinger_r2=0.56))
    assert _definition(definitions, "dsc.nonisothermal.conversion").publication_role == "main"
    assert all(item.figure_id != "dsc.nonisothermal.kissinger" for item in definitions if item.publication_role == "main")

def test_qualified_kinetics_creates_one_second_main_candidate() -> None:
    definitions = build_nonisothermal_dsc_figure_definitions(_nonisothermal_engine(kissinger_r2=0.96))
    assert _definition(definitions, "dsc.nonisothermal.kissinger").publication_role == "main"
```

- [ ] **Step 2: Run failing tests**

```powershell
pytest -q tests/test_dsc_publication_nonisothermal_provider.py
```

Expected: FAIL because the provider is absent.

- [ ] **Step 3: Implement conversion and evidence recipes**

Build `dsc.nonisothermal.conversion` from `NonIsothermalKineticsSeries.curves`, retaining only finite `T_xt_C`/`Xt` pairs and requiring at least two curves for Main. For `kissinger`, `ozawa`, `mo`, and `friedman`, create an SI or Diagnostics definition by default. Promote exactly one method to a second Main candidate only if it has at least three independent rates/points, finite parameters, no quality flags, and `r_squared >= 0.90`; prefer Kissinger, then Ozawa, Mo, Friedman in that order. Record rejected methods and reasons in `recipe["parameters"]["kinetics_gate"]`.

- [ ] **Step 4: Run focused provider and render tests**

```powershell
pytest -q tests/test_dsc_publication_nonisothermal_provider.py tests/test_figure_render_adapter.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add polynexus/core/dsc_engine/figure_nonisothermal.py tests/test_dsc_publication_nonisothermal_provider.py
git commit -m "feat(dsc): add nonisothermal publication figure recipes"
```

### Task 6: Add the DSC dispatcher and production cutover

**Files:**
- Create: `polynexus/core/dsc_engine/figure_provider.py`.
- Modify: `polynexus/core/dsc.py`.
- Test: `tests/test_dsc_publication_cutover.py`.

- [ ] **Step 1: Write failing cutover tests**

```python
def test_dsc_engine_publishes_manifest_backed_assets(tmp_path) -> None:
    engine = _standard_engine_with_results()
    assets = engine.plot(str(tmp_path))
    manifest = Path(engine.result.metadata["figure_manifest"])
    assert manifest.is_file()
    assert assets == engine.result.figures
    assert any(path.endswith(".svg") for path in assets.values())

def test_dispatcher_uses_active_submodule_without_cross_mode_recipes() -> None:
    assert _ids(_engine("dsc.isothermal")) == {"dsc.isothermal.avrami", "dsc.isothermal.series"}
    assert not any(item.startswith("dsc.nonisothermal") for item in _ids(_engine("dsc.isothermal")))
```

- [ ] **Step 2: Run failing tests**

```powershell
pytest -q tests/test_dsc_publication_cutover.py
```

Expected: FAIL because `DSCEngine.build_figure_definitions` is absent and `plot()` calls `generate_all_figures`.

- [ ] **Step 3: Implement dispatch and publisher path**

```python
def build_dsc_figure_definitions(engine: Any) -> tuple[FigureDefinition, ...]:
    submodule = str(getattr(engine, "active_submodule", "") or "")
    builder = {
        "dsc.isothermal": build_isothermal_dsc_figure_definitions,
        "dsc.nonisothermal": build_nonisothermal_dsc_figure_definitions,
    }.get(submodule, build_standard_dsc_figure_definitions)
    role_rank = {"main": 0, "si": 1, "diagnostic": 2}
    return tuple(sorted(builder(engine), key=lambda item: (role_rank[item.publication_role], item.display_order, item.figure_id)))
```

Add `DSCEngine.build_figure_definitions()` delegating to that function. In `DSCEngine.plot()`, call `self.publish_figure_definitions(out, definitions=definitions)` whenever definitions are non-empty. Only retain `generate_all_figures(...)` if the completed result bundle yields no definition; do not call legacy `savefig` code for a definition that the production pipeline can publish.

- [ ] **Step 4: Verify manifest, gallery ordering and editor round trip**

```powershell
pytest -q tests/test_dsc_publication_cutover.py tests/test_plot_gallery_service.py tests/test_chart_editor_generated_document_mixin.py tests/test_chart_editor_save_mixin.py
```

Expected: PASS; gallery roles sort Main before SI before Diagnostics and each generated DSC document opens in object editing mode.

- [ ] **Step 5: Commit**

```powershell
git add polynexus/core/dsc.py polynexus/core/dsc_engine/figure_provider.py tests/test_dsc_publication_cutover.py
git commit -m "feat(dsc): publish figure packs through shared lifecycle"
```

### Task 7: Real-data acceptance, audit and documentation closure

**Files:**
- Create: `tests/eval/test_dsc_publication_real_data.py`.
- Modify: `docs/superpowers/specs/2026-07-11-dsc-publication-figure-packs-design.md` only for verified acceptance notes.

- [ ] **Step 1: Write real-case assertions before execution**

```python
@pytest.mark.parametrize("case_dir, submodule", [
    ("测试数据/dsc/标准DSC数据格式一", "dsc.standard"),
    ("测试数据/dsc/等温结晶动力学数据", "dsc.isothermal"),
    ("测试数据/dsc/非等温结晶动力学数据", "dsc.nonisothermal"),
])
def test_real_dsc_case_publishes_audited_editable_assets(case_dir, submodule, tmp_path):
    engine = DSCEngine()
    engine.active_submodule = submodule
    result = engine.run_pipeline(str(project_root / case_dir), output_dir=str(tmp_path))
    manifest = json.loads(Path(result.metadata["figure_manifest"]).read_text(encoding="utf-8"))
    assert all(item["status"] == "ready" for item in manifest["figures"])
    assert all(item["capability_report"]["object_editing"] for item in manifest["figures"])
```

- [ ] **Step 2: Run the real-data test and inspect declared roles**

```powershell
pytest -q tests/eval/test_dsc_publication_real_data.py
```

Expected: PASS. If a real dataset has no reliable Main, assert a manifest reason and verify that no diagnostic figure was promoted to Main.

- [ ] **Step 3: Run final gates**

```powershell
python scripts/quality_gate.py
pytest -q tests/test_dsc*.py tests/test_figure_*.py tests/test_chart_editor*.py tests/eval/test_dsc_publication_real_data.py
git diff --check
```

Expected: every command exits 0. Verify every ready manifest includes preview, PDF, SVG and TIFF, and TIFF reports equal 600 dpi in both directions.

- [ ] **Step 4: Commit acceptance coverage**

```powershell
git add tests/eval/test_dsc_publication_real_data.py docs/superpowers/specs/2026-07-11-dsc-publication-figure-packs-design.md
git commit -m "test(dsc): verify publication packs on real data"
```

## Plan self-review

- Spec coverage: Tasks 2–5 implement every DSC mode and Main/SI/Diagnostics gate; Task 6 covers editor/publisher/gallery lifecycle; Task 7 covers all three requested real-data modes, format consistency, audit and fallback behavior.
- Scope: the plan consumes completed analysis results and does not alter DSC physics, peak finding, integration or kinetics algorithms.
- Type consistency: all providers return `tuple[FigureDefinition, ...]`; all DSCEngine publication entry points use `build_dsc_figure_definitions`; all eligibility decisions use `FigureEligibilityDecision` from the inherited shared foundation.
- Placeholder scan: no deferred implementation markers or unspecified validation steps remain.
