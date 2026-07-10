# WAXS DSC And NMR Figure Provider Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the standard WAXS, DSC, and NMR scientific figures to the shared FigureDefinition contract and prove that all five target techniques publish identical `paper_complete` projects.

**Architecture:** Each new technique provider maps existing result dataclasses into stable, portable semantic figures using only the shared line, scatter, bar, text, and annotation objects. Engine handoff methods expose definitions without changing legacy `plot()` yet; FigurePipeline remains the only new-lifecycle writer and is tested unchanged across IR, SAXS, WAXS, DSC, and NMR.

**Tech Stack:** Python 3.10+, dataclasses, NumPy, Matplotlib Figure API, CSV/JSON, pytest, Ruff.

---

## Scope Boundary

Included:

- WAXS profile/fit, amorphous-crystalline decomposition, and crystallinity overview
- DSC thermogram/event markers, Tg view, deconvolution curves, and crystallinity overview
- NMR spectrum/peaks, deconvolution, experimental-computed comparison, region integrals, and crystallinity overview
- engine `build_figure_definitions()` handoffs
- provider purity scanning through the existing automatic gate
- five-technique complete-asset integration test

Deferred:

- specialized WAXS strain/temperature composites
- DSC Avrami/Kissinger inputs that are not stored on `DSCEngine._results`
- gallery/editor production switch
- legacy output removal and recovery UI

## File Structure

### Create

- `polynexus/core/waxs_engine/figure_provider.py`
- `polynexus/core/dsc_engine/figure_provider.py`
- `polynexus/core/nmr_engine/figure_provider.py`
- `tests/test_waxs_figure_provider.py`
- `tests/test_dsc_figure_provider.py`
- `tests/test_nmr_figure_provider.py`
- `tests/test_five_technique_figure_pipeline.py`

### Modify

- `polynexus/core/waxs.py`
- `polynexus/core/dsc.py`
- `polynexus/core/nmr.py`

## Implementation Order

### Task 1: Add WAXS Providers And Engine Handoff

**Files:**

- Create: `polynexus/core/waxs_engine/figure_provider.py`
- Modify: `polynexus/core/waxs.py`
- Create: `tests/test_waxs_figure_provider.py`

- [ ] **Step 1: Write failing provider tests**

Create two `WAXSResult` instances. The first has `two_theta`, `I`, `I_fit`, `I_amorphous`, `I_crystalline`, peaks, and finite `Xc_pct`; the second has a raw profile and finite crystallinity. Assert:

```python
definitions = build_waxs_figure_definitions(results)
assert [item.figure_id for item in definitions] == [
    "waxs.frame.profile.001",
    "waxs.frame.decomposition.001",
    "waxs.frame.profile.002",
    "waxs.series.crystallinity",
]
assert definitions[0].layout.rows == 2
assert {obj["panel_id"] for obj in definitions[0].objects} == {"profile", "residual"}
assert definitions[1].layout.panels[0].show_legend is True
assert definitions[-1].objects[0]["chart_kind"] == "bar"
for definition in definitions:
    validate_figure_definition(definition)
```

Populate `WAXSEngine._results` and assert `build_figure_definitions()` returns the same IDs.

- [ ] **Step 2: Run tests and verify import failure**

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave3_waxs_red tests/test_waxs_figure_provider.py -q
```

Expected: WAXS provider import fails.

- [ ] **Step 3: Implement deterministic WAXS definitions**

Use:

```python
def build_waxs_figure_definitions(
    results: Sequence[WAXSResult],
) -> tuple[FigureDefinition, ...]:
    definitions = []
    for index, result in enumerate(results, start=1):
        if len(result.two_theta) == 0 or len(result.I) != len(result.two_theta):
            continue
        definitions.append(_build_profile(result, index))
        if (
            len(result.I_amorphous) == len(result.two_theta)
            and len(result.I_crystalline) == len(result.two_theta)
        ):
            definitions.append(_build_decomposition(result, index))
    overview = _build_crystallinity(results)
    if overview is not None:
        definitions.append(overview)
    return tuple(definitions)
```

The profile uses a 2x1 layout. Panel `profile` contains measured and optional fitted series plus at most 16 peak lines/text labels. Panel `residual` contains `I - I_fit` when the fit length matches and otherwise a zero baseline series. Decomposition uses total, amorphous, and crystalline line series from one equal-length source. Crystallinity uses dtype `str` labels and a bar object.

- [ ] **Step 4: Add the engine handoff**

Before `WAXSEngine.plot()` add:

```python
def build_figure_definitions(self):
    from .waxs_engine.figure_provider import build_waxs_figure_definitions

    return build_waxs_figure_definitions(tuple(self._results))
```

- [ ] **Step 5: Run provider and legacy document regression tests**

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave3_waxs_green tests/test_waxs_figure_provider.py tests/test_waxs_figure_document.py -q
python -m ruff check polynexus/core/waxs_engine/figure_provider.py tests/test_waxs_figure_provider.py
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```powershell
git add polynexus/core/waxs_engine/figure_provider.py polynexus/core/waxs.py tests/test_waxs_figure_provider.py
git commit -m "feat: add WAXS figure definition providers"
```

### Task 2: Add DSC Providers And Engine Handoff

**Files:**

- Create: `polynexus/core/dsc_engine/figure_provider.py`
- Modify: `polynexus/core/dsc.py`
- Create: `tests/test_dsc_figure_provider.py`

- [ ] **Step 1: Write failing provider tests**

Build two `DSCResult` values. The first has `T`, `HF`, `HF_fit`, finite Tg/Tm/Tc, two melting `peak_components`, and finite crystallinity; the second has `T`, `HF`, and finite crystallinity. Assert stable IDs:

```python
assert [item.figure_id for item in build_dsc_figure_definitions(results)] == [
    "dsc.frame.thermogram.001",
    "dsc.frame.tg.001",
    "dsc.frame.deconvolution.001",
    "dsc.frame.thermogram.002",
    "dsc.series.crystallinity",
]
```

Assert the thermogram contains vertical line objects for finite events, the Tg definition uses a window around Tg, the deconvolution contains experimental plus component series, and crystallinity is a bar. Validate every definition and test `DSCEngine.build_figure_definitions()`.

- [ ] **Step 2: Run tests and verify import failure**

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave3_dsc_red tests/test_dsc_figure_provider.py -q
```

Expected: DSC provider import fails.

- [ ] **Step 3: Implement DSC mappings**

Use:

```python
def build_dsc_figure_definitions(results: Sequence[DSCResult]) -> tuple[FigureDefinition, ...]:
    definitions = []
    for index, result in enumerate(results, start=1):
        if len(result.T) == 0 or len(result.HF) != len(result.T):
            continue
        definitions.append(_build_thermogram(result, index))
        if math.isfinite(float(result.Tg_C)):
            definitions.append(_build_tg_view(result, index))
        components = _melting_component_curves(result)
        if len(components) >= 2:
            definitions.append(_build_deconvolution(result, index, components))
    overview = _build_crystallinity(results)
    if overview is not None:
        definitions.append(overview)
    return tuple(definitions)
```

Thermogram data contains `temperature_C`, `heat_flow_W_g`, and optional `heat_flow_fit_W_g`. Add line/text pairs for finite `Tg_C`, `Tm_peak_C`, `Tc_peak_C`, and `Tcc_peak_C`. Tg data filters to `abs(T - Tg_C) <= max(DTg_C, 20)` with a 20 C fallback. Component curves use the existing Gaussian formula from `dsc_output.py`: `amp * exp(-0.5 * ((T - mu) / sigma) ** 2)` for valid melting/deconv-melting components.

- [ ] **Step 4: Add the engine handoff**

Before `DSCEngine.plot()` add:

```python
def build_figure_definitions(self):
    from .dsc_engine.figure_provider import build_dsc_figure_definitions

    return build_dsc_figure_definitions(tuple(self._results))
```

- [ ] **Step 5: Run provider and legacy document regressions**

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave3_dsc_green tests/test_dsc_figure_provider.py tests/test_dsc_figure_document.py tests/test_dsc_engine.py -q
python -m ruff check polynexus/core/dsc_engine/figure_provider.py tests/test_dsc_figure_provider.py
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```powershell
git add polynexus/core/dsc_engine/figure_provider.py polynexus/core/dsc.py tests/test_dsc_figure_provider.py
git commit -m "feat: add DSC figure definition providers"
```

### Task 3: Add NMR Providers And Engine Handoff

**Files:**

- Create: `polynexus/core/nmr_engine/figure_provider.py`
- Modify: `polynexus/core/nmr.py`
- Create: `tests/test_nmr_figure_provider.py`

- [ ] **Step 1: Write failing provider tests**

Create two `NMRResult` values. The first has ppm/intensity/fit, peaks, computed matches, region integrals, and crystallinity; the second has a raw spectrum and crystallinity. Assert IDs:

```python
assert [item.figure_id for item in build_nmr_figure_definitions(results)] == [
    "nmr.frame.spectrum.001",
    "nmr.frame.deconvolution.001",
    "nmr.frame.comparison.001",
    "nmr.frame.region-integrals.001",
    "nmr.frame.spectrum.002",
    "nmr.series.crystallinity",
]
```

Assert spectrum and deconvolution x axes are reversed, comparison uses `chart_kind="scatter"`, region integrals and crystallinity use bars, validate all definitions, and test `NMREngine.build_figure_definitions()`.

- [ ] **Step 2: Run tests and verify import failure**

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave3_nmr_red tests/test_nmr_figure_provider.py -q
```

Expected: NMR provider import fails.

- [ ] **Step 3: Implement NMR mappings**

Use the same deterministic composition pattern:

```python
for index, result in enumerate(results, start=1):
    if len(result.ppm) and len(result.intensity) == len(result.ppm):
        definitions.append(_build_spectrum(result, index))
        if len(result.intensity_fit) == len(result.ppm):
            definitions.append(_build_deconvolution(result, index))
    if result.matches:
        definitions.append(_build_comparison(result, index))
    if result.region_integrals:
        definitions.append(_build_region_integrals(result, index))
```

Spectrum/fit sources store ppm and intensity columns. Peak annotations are capped at 16 by prominence/height. Comparison stores `experimental_ppm` and `computed_ppm`, uses one scatter object, and adds a diagonal line object with x1/y1/x2/y2 bounds. Region-integral and crystallinity sources use string labels plus float percentages.

- [ ] **Step 4: Add the engine handoff**

Before `NMREngine.plot()` add:

```python
def build_figure_definitions(self):
    from .nmr_engine.figure_provider import build_nmr_figure_definitions

    return build_nmr_figure_definitions(tuple(self._results))
```

- [ ] **Step 5: Run provider and legacy document regressions**

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave3_nmr_green tests/test_nmr_figure_provider.py tests/test_nmr_figure_document.py tests/test_nmr_engine.py -q
python -m ruff check polynexus/core/nmr_engine/figure_provider.py tests/test_nmr_figure_provider.py
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```powershell
git add polynexus/core/nmr_engine/figure_provider.py polynexus/core/nmr.py tests/test_nmr_figure_provider.py
git commit -m "feat: add NMR figure definition providers"
```

### Task 4: Prove Five-Technique Artifact Uniformity

**Files:**

- Create: `tests/test_five_technique_figure_pipeline.py`

- [ ] **Step 1: Write one run per technique**

Use minimal valid IR, SAXS, WAXS, DSC, and NMR definitions. For each technique run `FigurePipeline.run()` with a unique run ID and assert:

```python
assert manifest.output_profile == "paper_complete"
for entry in manifest.figures:
    assert entry.status == "ready", entry.error
    assert set(entry.assets) == {"preview", "svg", "png", "pdf"}
    assert entry.capability_report["editing_mode"] == "object"
    assert read_figure_asset_dimensions(run_root / entry.assets["png"])[2] == 600
    document = json.loads((run_root / entry.document).read_text("utf-8"))
    assert document["export"]["assets"] == entry.assets
```

Use one representative definition per technique in this smoke test to bound runtime; provider-specific tests cover the complete sets.

- [ ] **Step 2: Run the integration test**

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave3_five tests/test_five_technique_figure_pipeline.py -q
```

Expected: all five runs pass without technique-specific format exceptions.

- [ ] **Step 3: Commit**

```powershell
git add tests/test_five_technique_figure_pipeline.py
git commit -m "test: prove five-technique figure artifact uniformity"
```

### Task 5: Run Wave 3 Quality Gates

**Files:**

- No production file changes expected

- [ ] **Step 1: Run provider and lifecycle suites**

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave3_full tests/test_figure_contracts.py tests/test_figure_data_writer.py tests/test_figure_document_builder.py tests/test_figure_render_plan_core.py tests/test_figure_export_service.py tests/test_run_figure_manifest.py tests/test_figure_pipeline.py tests/test_ir_figure_provider.py tests/test_ir_complete_figure_provider.py tests/test_saxs_temperature_figure_provider.py tests/test_waxs_figure_provider.py tests/test_dsc_figure_provider.py tests/test_nmr_figure_provider.py tests/test_cross_technique_figure_pipeline.py tests/test_five_technique_figure_pipeline.py tests/test_quality_gate.py -q
```

Expected: zero failures.

- [ ] **Step 2: Run lint, purity, and whitespace checks**

```powershell
python -m ruff check polynexus/core/figures polynexus/core/ir_engine/figure_provider.py polynexus/core/saxs_engine/figure_provider.py polynexus/core/waxs_engine/figure_provider.py polynexus/core/dsc_engine/figure_provider.py polynexus/core/nmr_engine/figure_provider.py tests/test_waxs_figure_provider.py tests/test_dsc_figure_provider.py tests/test_nmr_figure_provider.py tests/test_five_technique_figure_pipeline.py
python -c "from pathlib import Path; from scripts.quality_gate import scan_figure_lifecycle_sources; failures=scan_figure_lifecycle_sources(Path('.')); print(failures); raise SystemExit(bool(failures))"
git diff --check
```

Expected: lint passes, purity scan prints `[]`, and diff check exits 0.

- [ ] **Step 3: Run the five-technique artifact smoke test fresh**

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave3_smoke tests/test_five_technique_figure_pipeline.py -vv
```

Expected: one test passes and confirms all five technique runs use the same artifact roles and 600-DPI publication PNG.

## Plan Self-Review

### Spec coverage

This plan completes the wave 3 provider boundary for WAXS, DSC, and NMR and adds the approved five-technique artifact gate. Specialized workflow figures, UI integration, and legacy cleanup remain assigned to later waves.

### Plan completeness

Every production change is preceded by an explicit failing test, followed by focused and legacy regressions and an independent commit. Stable IDs, categories, object semantics, data columns, engine handoffs, and verification commands are named directly.

### Type consistency

All providers return `tuple[FigureDefinition, ...]`; string categories use dtype `str`; numerical columns use float64; every engine exposes the same zero-argument `build_figure_definitions()` method; formal output still flows only through `FigurePipeline` and `paper_complete`.

## Execution Handoff

Execute inline in the current goal using `superpowers:executing-plans`. Multi-agent delegation remains disabled by collaboration policy unless the user explicitly requests it.
