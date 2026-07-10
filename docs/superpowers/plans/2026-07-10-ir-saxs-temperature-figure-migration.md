# IR And SAXS Temperature Figure Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the IR FigureDefinition provider set and migrate the SAXS temperature workflow far enough to prove per-frame, series, multi-panel, bar, legend, and heatmap figures through the same portable manifest-backed pipeline.

**Architecture:** Scientific providers remain pure: they convert existing result objects into immutable FigureDefinitions and never choose paths, formats, DPI, or save behavior. The shared renderer gains only the technique-neutral object semantics needed by both techniques, after which the existing FigurePipeline produces one `paper_complete` artifact group and one authoritative manifest for every ready definition.

**Tech Stack:** Python 3.10+, dataclasses, NumPy, Matplotlib Figure API, CSV/JSON, pytest, Ruff.

---

## Scope Boundary

Included in this wave:

- panel titles and panel-owned legends
- line, scatter, bar, and regular-grid heatmap rendering through `plot_series`/`heatmap` objects
- full IR provider set for spectrum, peak fit, computed comparison, and crystallinity overview
- SAXS temperature per-frame scattering figures
- SAXS temperature waterfall, parameter dashboard, and heatmap figures
- `IREngine` and `SAXSEngine` definition handoff methods
- cross-technique `paper_complete` integration tests
- provider purity gates for both migrated provider modules

Deferred to later waves:

- WAXS, DSC, and NMR providers
- non-temperature SAXS routes
- manifest-only production gallery
- ChartEditor save/publish lifecycle
- legacy recovery and removal of legacy output writers

Existing `plot()` methods remain available during strangler migration. They are not the source used by the new lifecycle tests, and wave 5 removes their direct formal-output behavior after all production callers have switched.

## File Structure

### Create

- `polynexus/core/saxs_engine/figure_provider.py` — pure SAXS temperature FigureDefinitions
- `tests/test_ir_complete_figure_provider.py` — complete IR provider contracts
- `tests/test_saxs_temperature_figure_provider.py` — SAXS per-frame and series contracts
- `tests/test_cross_technique_figure_pipeline.py` — IR/SAXS run-level artifact consistency

### Modify

- `polynexus/core/figures/contracts.py` — optional panel title and legend flags
- `polynexus/core/figures/render_plan.py` — resolved panel title/legend fields
- `polynexus/core/figures/renderer.py` — line/scatter/bar/heatmap and legend rendering
- `polynexus/core/figures/validation.py` — chart-kind and heatmap references
- `polynexus/core/figures/capabilities.py` — heatmap object editing support
- `polynexus/core/ir_engine/figure_provider.py` — full IR provider set
- `polynexus/core/ir.py` — return the complete IR definitions
- `polynexus/core/saxs.py` — expose SAXS temperature definitions
- `scripts/quality_gate.py` — discover every migrated `figure_provider.py`
- `tests/test_figure_contracts.py`
- `tests/test_figure_render_plan_core.py`
- `tests/test_quality_gate.py`

## Implementation Order

### Task 1: Extend The Shared Render Contract Without Technique Branches

**Files:**

- Modify: `polynexus/core/figures/contracts.py`
- Modify: `polynexus/core/figures/render_plan.py`
- Modify: `polynexus/core/figures/renderer.py`
- Modify: `polynexus/core/figures/validation.py`
- Modify: `polynexus/core/figures/capabilities.py`
- Modify: `tests/test_figure_contracts.py`
- Modify: `tests/test_figure_render_plan_core.py`

- [ ] **Step 1: Write failing panel, bar, and heatmap tests**

Add a contract test:

```python
def test_panel_contract_preserves_title_and_legend(ir_definition):
    panel = replace(
        ir_definition.layout.panels[0],
        title="Spectrum",
        show_legend=True,
    )

    payload = panel.to_payload()

    assert payload["title"] == "Spectrum"
    assert payload["show_legend"] is True
```

Add renderer tests using `dataclasses.replace(render_plan, ...)`:

```python
def test_renderer_supports_bar_series_and_panel_legend(render_plan):
    panel = replace(render_plan.panels[0], title="Metrics", show_legend=True)
    plan = replace(
        render_plan,
        panels=(panel,),
        objects=(
            {
                "id": "bars",
                "type": "plot_series",
                "panel_id": "main",
                "data_ref": "spectrum-data",
                "x_column": "wavenumber_cm1",
                "y_column": "absorbance",
                "name": "Absorbance",
                "chart_kind": "bar",
                "style": {"color": "#4477AA"},
            },
        ),
    )

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)
    axis = figure.axes[0]

    assert axis.get_title() == "Metrics"
    assert len(axis.patches) == 2
    assert axis.get_legend() is not None
```

Create a long-form heatmap table and test:

```python
def test_renderer_supports_regular_grid_heatmap(render_plan):
    plan = replace(
        render_plan,
        objects=(
            {
                "id": "map",
                "type": "heatmap",
                "panel_id": "main",
                "data_ref": "grid",
                "x_column": "q_nm1",
                "y_column": "temperature_C",
                "z_column": "intensity",
                "style": {"cmap": "viridis", "colorbar_label": "I(q)"},
            },
        ),
        data_tables={
            "grid": {
                "q_nm1": [0.1, 0.2, 0.1, 0.2],
                "temperature_C": [30.0, 30.0, 80.0, 80.0],
                "intensity": [10.0, 5.0, 8.0, 4.0],
            }
        },
    )

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)

    assert len(figure.axes[0].collections) == 1
    assert len(figure.axes) == 2
    assert figure.axes[1].get_ylabel() == "I(q)"
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task1_red tests/test_figure_contracts.py tests/test_figure_render_plan_core.py -q
```

Expected: `PanelDefinition`/`RenderPanel` reject the new fields and the renderer does not implement bar or heatmap semantics.

- [ ] **Step 3: Add optional panel presentation fields**

Extend the frozen types without changing existing call sites:

```python
@dataclass(frozen=True)
class PanelDefinition:
    panel_id: str
    row: int
    column: int
    x_axis: AxisDefinition
    y_axis: AxisDefinition
    title: str = ""
    show_legend: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "grid_position": {"row": self.row, "column": self.column},
            "x_axis": self.x_axis.to_payload(),
            "y_axis": self.y_axis.to_payload(),
            "title": self.title,
            "show_legend": self.show_legend,
        }
```

Mirror `title` and `show_legend` in `RenderPanel` and `_panel_from_payload()`.

- [ ] **Step 4: Implement chart kinds and heatmap rendering**

In `_render_plot_series`, dispatch on `chart_kind`:

```python
chart_kind = str(figure_object.get("chart_kind") or "line")
if chart_kind == "bar":
    axis.bar(
        table[x_column],
        table[y_column],
        color=style.get("color", "#4477AA"),
        alpha=float(style.get("alpha", 1.0)),
        label=name or None,
    )
elif chart_kind == "scatter":
    axis.scatter(
        table[x_column],
        table[y_column],
        color=style.get("color", "#222222"),
        s=float(style.get("marker_size", 12.0)),
        alpha=float(style.get("alpha", 1.0)),
        label=name or None,
    )
else:
    axis.plot(table[x_column], table[y_column], **kwargs)
```

Add `heatmap` dispatch and a helper that converts long-form values to a complete regular matrix:

```python
def _render_heatmap(self, figure, axis, plan, figure_object):
    table = plan.data_tables[str(figure_object["data_ref"])]
    x_values = np.asarray(table[str(figure_object["x_column"])], dtype=float)
    y_values = np.asarray(table[str(figure_object["y_column"])], dtype=float)
    z_values = np.asarray(table[str(figure_object["z_column"])], dtype=float)
    unique_x = np.unique(x_values)
    unique_y = np.unique(y_values)
    matrix = np.full((len(unique_y), len(unique_x)), np.nan, dtype=float)
    x_index = {value: index for index, value in enumerate(unique_x)}
    y_index = {value: index for index, value in enumerate(unique_y)}
    for x_value, y_value, z_value in zip(x_values, y_values, z_values):
        matrix[y_index[y_value], x_index[x_value]] = z_value
    if np.isnan(matrix).any():
        raise ValueError("heatmap data does not form a complete regular grid")
    style = self._style(figure_object)
    image = axis.pcolormesh(
        unique_x,
        unique_y,
        matrix,
        shading="auto",
        cmap=str(style.get("cmap") or "viridis"),
    )
    label = str(style.get("colorbar_label") or "")
    figure.colorbar(image, ax=axis, label=label)
```

Set panel titles before objects and call `axis.legend()` after objects only for panels whose `show_legend` is true and which have labeled artists.

- [ ] **Step 5: Validate the new object references and capabilities**

Validation must allow `chart_kind` in `{"line", "scatter", "bar"}` for plot-series objects. For heatmaps, require `data_ref`, `x_column`, `y_column`, and `z_column` to exist in the referenced source. Add `heatmap` to `_OBJECT_EDITABLE_TYPES` in `capabilities.py`.

- [ ] **Step 6: Run focused and foundation regression tests**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task1_green tests/test_figure_contracts.py tests/test_figure_data_writer.py tests/test_figure_render_plan_core.py tests/test_figure_export_service.py tests/test_figure_pipeline.py -q
```

Expected: all selected tests pass with no Matplotlib layout warnings.

- [ ] **Step 7: Commit**

```powershell
git add polynexus/core/figures/contracts.py polynexus/core/figures/render_plan.py polynexus/core/figures/renderer.py polynexus/core/figures/validation.py polynexus/core/figures/capabilities.py tests/test_figure_contracts.py tests/test_figure_render_plan_core.py
git commit -m "feat: extend shared figure render semantics"
```

### Task 2: Complete The IR Scientific Provider Set

**Files:**

- Modify: `polynexus/core/ir_engine/figure_provider.py`
- Modify: `polynexus/core/ir.py`
- Create: `tests/test_ir_complete_figure_provider.py`

- [ ] **Step 1: Write failing complete-provider tests**

Use one `IRResult` containing raw, fit, simulated, and peak data plus a second crystallinity result:

```python
def test_complete_ir_provider_emits_expected_semantic_figures(ir_complete_results):
    definitions = build_ir_figure_definitions(ir_complete_results)

    assert [item.figure_id for item in definitions] == [
        "ir.frame.spectrum.001",
        "ir.frame.peak-fit.001",
        "ir.frame.comparison.001",
        "ir.frame.spectrum.002",
        "ir.series.crystallinity",
    ]
    peak_fit = definitions[1]
    assert [obj["y_column"] for obj in peak_fit.objects if obj["type"] == "plot_series"] == [
        "absorbance",
        "absorbance_fit",
    ]
    crystallinity = definitions[-1]
    assert crystallinity.objects[0]["chart_kind"] == "bar"
    assert crystallinity.category == "series_overview"
```

Also prove each data-bound object has a matching source/column by calling `validate_figure_definition()` for every definition.

- [ ] **Step 2: Run the test and verify import failure**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task2_red tests/test_ir_complete_figure_provider.py -q
```

Expected: `build_ir_figure_definitions` is missing.

- [ ] **Step 3: Implement deterministic IR composition**

Keep `build_ir_spectrum_definitions()` unchanged and add:

```python
def build_ir_figure_definitions(
    results: Sequence[IRResult],
) -> tuple[FigureDefinition, ...]:
    definitions: list[FigureDefinition] = []
    spectrum_by_index = {
        int(item.recipe["parameters"]["frame_index"]): item
        for item in build_ir_spectrum_definitions(results)
    }
    for index, result in enumerate(results, start=1):
        spectrum = spectrum_by_index.get(index)
        if spectrum is not None:
            definitions.append(spectrum)
        if len(result.absorbance_fit) == len(result.wavenumber) and len(result.wavenumber):
            definitions.append(_build_peak_fit_definition(result, index))
        simulated = result.simulated_spectrum
        if simulated is not None and len(simulated.wavenumber) and len(simulated.absorbance):
            definitions.append(_build_comparison_definition(result, index))
    crystallinity = _build_crystallinity_definition(results)
    if crystallinity is not None:
        definitions.append(crystallinity)
    return tuple(definitions)
```

Peak-fit definitions use one CSV source with `wavenumber_cm1`, `absorbance`, and `absorbance_fit`, two named line series, and the same capped peak annotations as the spectrum provider. Comparison definitions use separate experimental and computed sources so unequal grids remain portable. The crystallinity definition filters finite `Xc_pct` values, stores `label` as dtype `str` and `crystallinity_pct` as float64, and uses one bar object.

- [ ] **Step 4: Switch the IR handoff method, not legacy publication**

Update only `IREngine.build_figure_definitions()`:

```python
def build_figure_definitions(self):
    from .ir_engine.figure_provider import build_ir_figure_definitions

    return build_ir_figure_definitions(tuple(self._results))
```

Do not alter `IREngine.plot()` in this wave.

- [ ] **Step 5: Run IR provider, pipeline, and legacy document regressions**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task2_green tests/test_ir_figure_provider.py tests/test_ir_complete_figure_provider.py tests/test_ir_figure_document.py tests/test_figure_pipeline.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```powershell
git add polynexus/core/ir_engine/figure_provider.py polynexus/core/ir.py tests/test_ir_complete_figure_provider.py
git commit -m "feat: complete IR figure definition providers"
```

### Task 3: Add SAXS Temperature Per-Frame And Waterfall Providers

**Files:**

- Create: `polynexus/core/saxs_engine/figure_provider.py`
- Create: `tests/test_saxs_temperature_figure_provider.py`

- [ ] **Step 1: Write failing stable-ID and data-contract tests**

Create two temperature frames with unequal q grids and a minimal `TempSeriesResult`, then assert:

```python
def test_saxs_temperature_provider_emits_per_frame_and_waterfall_definitions(
    saxs_temperature_inputs,
):
    result, q_values, intensities = saxs_temperature_inputs

    definitions = build_saxs_temperature_definitions(result, q_values, intensities)

    assert [item.figure_id for item in definitions[:3]] == [
        "saxs.frame.temperature.scattering.001",
        "saxs.frame.temperature.scattering.002",
        "saxs.series.temperature.waterfall",
    ]
    assert definitions[0].category == "per_frame"
    waterfall = definitions[2]
    assert waterfall.category == "series_overview"
    assert len(waterfall.data_sources) == 2
    assert all(obj["type"] == "plot_series" for obj in waterfall.objects)
    assert waterfall.layout.panels[0].show_legend is True
```

Add a mismatch test that expects `ValueError("temperature frame counts differ")` when result temperatures, q arrays, and intensity arrays have different lengths.

- [ ] **Step 2: Run tests and verify provider import failure**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task3_red tests/test_saxs_temperature_figure_provider.py -q
```

Expected: SAXS figure provider import fails.

- [ ] **Step 3: Implement the public SAXS provider entry point**

Use this signature:

```python
def build_saxs_temperature_definitions(
    result: TempSeriesResult,
    q_values: Sequence[np.ndarray],
    intensities: Sequence[np.ndarray],
) -> tuple[FigureDefinition, ...]:
    temperatures = np.asarray(result.temperatures, dtype=float)
    if len(temperatures) != len(q_values) or len(q_values) != len(intensities):
        raise ValueError("temperature frame counts differ")
    definitions: list[FigureDefinition] = []
    for index, (temperature, q, intensity) in enumerate(
        zip(temperatures, q_values, intensities),
        start=1,
    ):
        definitions.append(_build_temperature_frame(index, temperature, q, intensity))
    if definitions:
        definitions.append(_build_temperature_waterfall(temperatures, q_values, intensities))
    definitions.extend(_build_temperature_summary_definitions(result, q_values, intensities))
    return tuple(definitions)
```

Each frame source stores `q_nm1` and `intensity_au`. The waterfall stores one source per frame with `intensity_offset = log10(clip(intensity, tiny, None)) + frame_index * 1.2`; this numerical presentation transform is recorded in recipe parameters and does not affect scientific result values.

- [ ] **Step 4: Validate and run the focused tests**

Every returned definition must pass `validate_figure_definition()`. Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task3_green tests/test_saxs_temperature_figure_provider.py -k "per_frame or waterfall or counts" -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```powershell
git add polynexus/core/saxs_engine/figure_provider.py tests/test_saxs_temperature_figure_provider.py
git commit -m "feat: add SAXS temperature frame and waterfall providers"
```

### Task 4: Add SAXS Multi-Panel Parameters And Heatmap Definitions

**Files:**

- Modify: `polynexus/core/saxs_engine/figure_provider.py`
- Modify: `tests/test_saxs_temperature_figure_provider.py`

- [ ] **Step 1: Write failing summary-definition tests**

Extend the provider test:

```python
def test_saxs_temperature_provider_emits_multi_panel_and_heatmap(
    saxs_temperature_inputs,
):
    result, q_values, intensities = saxs_temperature_inputs

    definitions = build_saxs_temperature_definitions(result, q_values, intensities)
    by_id = {item.figure_id: item for item in definitions}

    parameters = by_id["saxs.series.temperature.parameters"]
    assert parameters.layout.rows == 2
    assert parameters.layout.columns == 2
    assert {obj["panel_id"] for obj in parameters.objects} == {
        "long-period",
        "thickness",
        "invariant",
        "crystallinity",
    }
    heatmap = by_id["saxs.series.temperature.heatmap"]
    assert heatmap.objects[0]["type"] == "heatmap"
    assert {column.name for column in heatmap.data_sources[0].columns} == {
        "q_nm1",
        "temperature_C",
        "intensity",
    }
```

- [ ] **Step 2: Run the new tests and verify missing definitions**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task4_red tests/test_saxs_temperature_figure_provider.py -k "multi_panel or heatmap" -q
```

Expected: requested IDs are absent.

- [ ] **Step 3: Implement the parameter dashboard**

Build one `saxs-temperature-parameters` source containing equal-length columns:

- `temperature_C`
- `L_nm`
- `lc_nm`, preferring finite `lc_effective_array` values over raw `lc_array`
- `la_nm = L_nm - lc_nm`
- `Q_star`
- `crystallinity_fraction`

Use a 2x2 layout with panel IDs `long-period`, `thickness`, `invariant`, and `crystallinity`. Add one line series for L, two named line series for lc/la with a legend, one line series for Q, and one line series for crystallinity. The definition category is `series_overview`.

- [ ] **Step 4: Implement deterministic regular-grid heatmap data**

Create a common q grid from the finite overlap of all frames:

```python
q_min = max(float(np.nanmin(q)) for q in q_values)
q_max = min(float(np.nanmax(q)) for q in q_values)
if not q_min < q_max:
    raise ValueError("temperature q ranges do not overlap")
point_count = max(2, min(512, max(len(q) for q in q_values)))
common_q = np.linspace(q_min, q_max, point_count)
rows = [
    (float(q_value), float(temperature), float(intensity_value))
    for temperature, q, intensity in zip(temperatures, q_values, intensities)
    for q_value, intensity_value in zip(
        common_q,
        np.interp(common_q, np.asarray(q, dtype=float), np.asarray(intensity, dtype=float)),
    )
]
```

Sort each source q array before interpolation. Flatten rows into equal-length `q_nm1`, `temperature_C`, and `intensity` columns. Create one heatmap object with `cmap="viridis"` and `colorbar_label="I(q)"`.

- [ ] **Step 5: Run provider, renderer, and pipeline tests**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task4_green tests/test_saxs_temperature_figure_provider.py tests/test_figure_render_plan_core.py tests/test_figure_pipeline.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```powershell
git add polynexus/core/saxs_engine/figure_provider.py tests/test_saxs_temperature_figure_provider.py
git commit -m "feat: add SAXS temperature summary providers"
```

### Task 5: Expose SAXS Definitions From The Existing Engine

**Files:**

- Modify: `polynexus/core/saxs.py`
- Modify: `tests/test_saxs_temperature_figure_provider.py`

- [ ] **Step 1: Write a failing engine handoff test**

Populate an engine's analyzed temperature fields and assert:

```python
def test_saxs_engine_exposes_temperature_figure_definitions(saxs_temperature_inputs):
    result, q_values, intensities = saxs_temperature_inputs
    engine = SAXSEngine(config=SAXSConfig(experiment_type="temperature"))
    engine._temperature_result = result
    engine._q_list = list(q_values)
    engine._I_list = list(intensities)

    definitions = engine.build_figure_definitions()

    assert definitions
    assert all(item.technique == "saxs" for item in definitions)
    assert "saxs.series.temperature.heatmap" in {item.figure_id for item in definitions}
```

- [ ] **Step 2: Run the handoff test and verify the method is missing**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task5_red tests/test_saxs_temperature_figure_provider.py -k engine_exposes -q
```

Expected: `SAXSEngine` has no `build_figure_definitions` method.

- [ ] **Step 3: Implement the non-publishing handoff**

Add before `plot()`:

```python
def build_figure_definitions(self):
    if self._temperature_result is None:
        return ()
    from .saxs_engine.figure_provider import build_saxs_temperature_definitions

    return build_saxs_temperature_definitions(
        self._temperature_result,
        tuple(self._q_list),
        tuple(self._I_list),
    )
```

Do not change `SAXSEngine.plot()` yet.

- [ ] **Step 4: Run handoff and existing SAXS temperature regressions**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task5_green tests/test_saxs_temperature_figure_provider.py tests/test_saxs_temperature_status.py tests/test_saxs_figure_document.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```powershell
git add polynexus/core/saxs.py tests/test_saxs_temperature_figure_provider.py
git commit -m "feat: expose SAXS temperature figure definitions"
```

### Task 6: Prove Cross-Technique Artifact Uniformity

**Files:**

- Create: `tests/test_cross_technique_figure_pipeline.py`

- [ ] **Step 1: Write IR/SAXS run integration tests**

Run one IR definition set and one SAXS temperature definition set into separate run IDs under the same output root. Assert for every ready entry:

```python
def _assert_paper_complete(run_root, entry):
    assert entry.status == "ready"
    assert set(entry.assets) == {"preview", "svg", "png", "pdf"}
    assert entry.document.endswith("figure.pnfig.json")
    assert all((run_root / path).is_file() for path in entry.assets.values())
    document = json.loads((run_root / entry.document).read_text("utf-8"))
    assert document["export"]["profile"] == "paper_complete"
    assert document["export"]["published_revision"] == entry.published_revision
    assert document["export"]["assets"] == entry.assets
```

Also assert that the SAXS run contains at least one `per_frame` entry, one multi-panel document, and one heatmap document, all with `editing_mode="object"`.

- [ ] **Step 2: Run the integration test**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task6_red tests/test_cross_technique_figure_pipeline.py -q
```

Expected: all integration assertions pass; a failure blocks the wave and must be diagnosed with `superpowers:systematic-debugging` before this plan continues.

- [ ] **Step 3: Run the cross-technique and foundation suites**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task6_green tests/test_cross_technique_figure_pipeline.py tests/test_figure_contracts.py tests/test_figure_data_writer.py tests/test_figure_document_builder.py tests/test_figure_render_plan_core.py tests/test_figure_export_service.py tests/test_run_figure_manifest.py tests/test_figure_pipeline.py -q
```

Expected: all selected tests pass.

- [ ] **Step 4: Commit**

```powershell
git add tests/test_cross_technique_figure_pipeline.py polynexus/core/figures polynexus/core/ir_engine/figure_provider.py polynexus/core/saxs_engine/figure_provider.py
git commit -m "test: prove cross-technique figure artifact uniformity"
```

### Task 7: Extend Provider Purity Enforcement

**Files:**

- Modify: `scripts/quality_gate.py`
- Modify: `tests/test_quality_gate.py`

- [ ] **Step 1: Write a failing provider-discovery test**

```python
def test_lifecycle_gate_scans_all_migrated_figure_providers(tmp_path):
    ir_provider = tmp_path / "polynexus/core/ir_engine/figure_provider.py"
    saxs_provider = tmp_path / "polynexus/core/saxs_engine/figure_provider.py"
    ir_provider.parent.mkdir(parents=True)
    saxs_provider.parent.mkdir(parents=True)
    ir_provider.write_text("DEFINITION = 1\n", encoding="utf-8")
    saxs_provider.write_text("figure.savefig('bad.pdf')\n", encoding="utf-8")

    failures = scan_figure_lifecycle_sources(tmp_path)

    assert failures == [
        "figure_provider.py: migrated figure providers must not call savefig"
    ]
```

- [ ] **Step 2: Run the test and verify SAXS is not yet scanned**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task7_red tests/test_quality_gate.py -k migrated_figure_providers -q
```

Expected: no failure is returned for the bad SAXS provider.

- [ ] **Step 3: Discover provider modules instead of hard-coding IR**

Replace the single provider path with:

```python
for provider in sorted((root / "polynexus" / "core").glob("*_engine/figure_provider.py")):
    failures.extend(scan_migrated_figure_provider(provider))
```

Keep legacy `ir_output.py` and `saxs_output.py` outside the scan until wave 5 removes their publication role.

- [ ] **Step 4: Run quality-gate tests and scan the real tree**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_task7_green tests/test_quality_gate.py -q
python -c "from pathlib import Path; from scripts.quality_gate import scan_figure_lifecycle_sources; failures=scan_figure_lifecycle_sources(Path('.')); print(failures); raise SystemExit(bool(failures))"
```

Expected: tests pass and the real scan prints `[]`.

- [ ] **Step 5: Commit**

```powershell
git add scripts/quality_gate.py tests/test_quality_gate.py
git commit -m "test: enforce all migrated figure providers"
```

### Task 8: Run The Wave 2 Quality Gates

**Files:**

- No production file changes expected

- [ ] **Step 1: Run the complete wave 1 and wave 2 test selection**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_full tests/test_figure_contracts.py tests/test_figure_data_writer.py tests/test_figure_document.py tests/test_figure_document_builder.py tests/test_figure_render_plan_core.py tests/test_figure_assets.py tests/test_figure_export_service.py tests/test_run_figure_manifest.py tests/test_figure_pipeline.py tests/test_ir_figure_provider.py tests/test_ir_complete_figure_provider.py tests/test_ir_figure_document.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_temperature_status.py tests/test_saxs_figure_document.py tests/test_cross_technique_figure_pipeline.py tests/test_quality_gate.py -q
```

Expected: zero failures.

- [ ] **Step 2: Run lint and whitespace checks**

Run:

```powershell
python -m ruff check polynexus/core/figures polynexus/core/ir_engine/figure_provider.py polynexus/core/saxs_engine/figure_provider.py tests/test_ir_complete_figure_provider.py tests/test_saxs_temperature_figure_provider.py tests/test_cross_technique_figure_pipeline.py
git diff --check
```

Expected: both commands exit 0.

- [ ] **Step 3: Run one multi-panel and heatmap artifact smoke test**

Run:

```powershell
python -m pytest -o addopts= --basetemp=.pytest_tmp_wave2_smoke tests/test_cross_technique_figure_pipeline.py -vv
```

Expected: every SAXS ready entry has preview, SVG, 600-DPI PNG, and PDF paths in the run manifest, including the multi-panel and heatmap figures.

- [ ] **Step 4: Record the wave boundary**

No empty marker commit is needed. Record the verified command counts in the execution handoff and proceed to the WAXS/DSC/NMR migration plan.

## Plan Self-Review

### Spec coverage

This plan covers implementation wave 2 from the approved umbrella design:

- full IR semantic provider handoff
- SAXS temperature series and frame definitions
- heatmap and multi-panel rendering through formal contracts
- shared complete artifact groups
- provider purity enforcement

WAXS, DSC, NMR, gallery/editor, legacy recovery, and legacy writer removal remain explicitly assigned to waves 3–5.

### Placeholder scan

Every implementation step includes a concrete behavior, command, and expected result. Deferred subsystems are named in the scope boundary and assigned to waves 3–5.

### Type consistency

- `PanelDefinition.title` and `RenderPanel.title` are strings.
- `PanelDefinition.show_legend` and `RenderPanel.show_legend` are booleans.
- Heatmaps use one long-form `FigureDataSourceDefinition` and one `heatmap` object with x/y/z columns.
- Both engines return `tuple[FigureDefinition, ...]` through `build_figure_definitions()`.
- Every ready run continues to use the existing `paper_complete` profile and manifest schema.

## Execution Handoff

Execute inline in the current goal using `superpowers:executing-plans`. Multi-agent delegation is intentionally not used because the collaboration policy permits subagents only when explicitly requested by the user.
