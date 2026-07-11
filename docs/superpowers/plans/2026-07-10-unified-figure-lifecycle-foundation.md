# Unified Figure Lifecycle Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared figure-lifecycle foundation and prove it with one IR spectrum vertical slice that produces a portable FigureDocument, data snapshot, preview, SVG, 600-DPI PNG, PDF, capability report, and run manifest.

**Architecture:** Technique providers return immutable `FigureDefinition` values and never choose paths or formats. A core-only pipeline validates definitions, snapshots data, builds a portable FigureDocument, creates one render plan, exports the `paper_complete` asset group, inspects it, resolves capabilities, and atomically commits a run manifest. This first plan proves the contract without switching the existing production gallery or replacing all legacy technique output paths.

**Tech Stack:** Python 3.10+, dataclasses, NumPy, Matplotlib Figure API, CSV/JSON, pathlib, hashlib, pytest.

---

## Scope Boundary

This is implementation wave 1 from the approved umbrella design:

- `docs/superpowers/specs/2026-07-10-unified-figure-artifact-lifecycle-design.md`

Included:

- contracts and validation
- global output profiles
- portable data snapshots
- FigureDocument builder
- single-panel render-plan baseline
- line/text/plot-series Matplotlib renderer
- initial full asset-group export and inspection
- capability report
- run manifest and active-run pointer
- core pipeline
- IR spectrum provider vertical slice
- focused quality gates

Deferred to later plans:

- production switch of `IREngine.plot()`
- all remaining IR figures
- SAXS/WAXS/DSC/NMR migration
- multi-panel/twin-axis rendering
- gallery manifest-only switch
- ChartEditor shared render-plan integration
- republish replacement of an existing asset group
- legacy recovery UI

## File Structure

### Create

- `polynexus/core/figures/__init__.py` — public lifecycle API
- `polynexus/core/figures/contracts.py` — immutable definition and layout contracts
- `polynexus/core/figures/profiles.py` — global output profiles
- `polynexus/core/figures/validation.py` — cross-reference and schema validation
- `polynexus/core/figures/data_writer.py` — portable CSV/schema snapshots
- `polynexus/core/figures/document_builder.py` — normalized FigureDocument construction
- `polynexus/core/figures/render_plan.py` — data resolution and render-plan model
- `polynexus/core/figures/renderer.py` — core Matplotlib renderer
- `polynexus/core/figures/inspector.py` — artifact metadata and consistency inspection
- `polynexus/core/figures/export_service.py` — initial atomic asset-group export
- `polynexus/core/figures/capabilities.py` — editing/publication capability resolution
- `polynexus/core/figures/manifest.py` — run manifest models and atomic repository
- `polynexus/core/figures/pipeline.py` — per-run orchestration
- `polynexus/core/ir_engine/figure_provider.py` — IR spectrum FigureDefinition provider
- `tests/test_figure_contracts.py`
- `tests/conftest.py` — shared lifecycle fixtures with deferred imports
- `tests/test_figure_data_writer.py`
- `tests/test_figure_document_builder.py`
- `tests/test_figure_render_plan_core.py`
- `tests/test_figure_export_service.py`
- `tests/test_run_figure_manifest.py`
- `tests/test_figure_pipeline.py`
- `tests/test_ir_figure_provider.py`

### Modify

- `polynexus/core/figure_document.py` — preserve explicitly run-relative data paths
- `polynexus/core/figure_assets.py` — expose public dimension inspection
- `polynexus/core/ir.py` — expose FigureDefinitions without switching production output
- `scripts/quality_gate.py` — prohibit output behavior in migrated provider modules
- `tests/test_figure_document.py`
- `tests/test_figure_assets.py`
- `tests/test_quality_gate.py`

## Implementation Order

### Task 1: Add Figure Contracts And Global Profiles

**Files:**

- Create: `polynexus/core/figures/__init__.py`
- Create: `polynexus/core/figures/contracts.py`
- Create: `polynexus/core/figures/profiles.py`
- Create: `tests/test_figure_contracts.py`

- [ ] **Step 1: Write failing contract and profile tests**

Add:

```python
from polynexus.core.figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)
from polynexus.core.figures.profiles import get_figure_output_profile


def test_paper_complete_profile_has_fixed_roles():
    profile = get_figure_output_profile("paper_complete")

    assert profile.profile_id == "paper_complete"
    assert profile.preview_filename == "preview.png"
    assert profile.formal_assets == {
        "svg": "figure.svg",
        "png": "figure.png",
        "pdf": "figure.pdf",
    }
    assert profile.preview_dpi == 150
    assert profile.publication_png_dpi == 600


def test_figure_definition_serializes_stable_layout_and_data_contract():
    source = FigureDataSourceDefinition(
        source_id="spectrum-data",
        columns=(
            DataColumnDefinition("wavenumber_cm1", "cm^-1"),
            DataColumnDefinition("absorbance", "a.u."),
        ),
        values={
            "wavenumber_cm1": (1800.0, 1700.0),
            "absorbance": (0.1, 0.4),
        },
    )
    definition = FigureDefinition(
        figure_id="ir.frame.spectrum.001",
        technique="ir",
        scope="frame",
        category="per_frame",
        title="IR Spectrum",
        layout=FigureLayoutDefinition(
            width_in=7.5,
            height_in=3.8,
            rows=1,
            columns=1,
            panels=(
                PanelDefinition(
                    panel_id="main",
                    row=0,
                    column=0,
                    x_axis=AxisDefinition(
                        axis_id="x",
                        label="Wavenumber",
                        unit="cm^-1",
                        reversed=True,
                    ),
                    y_axis=AxisDefinition(
                        axis_id="y",
                        label="Absorbance",
                        unit="a.u.",
                    ),
                ),
            ),
        ),
        data_sources=(source,),
        objects=(
            {
                "id": "series-spectrum",
                "type": "plot_series",
                "panel_id": "main",
                "data_ref": "spectrum-data",
                "x_column": "wavenumber_cm1",
                "y_column": "absorbance",
                "style": {"color": "#222222", "line_width": 0.8},
            },
        ),
        recipe={
            "module": "polynexus.core.ir_engine.figure_provider",
            "function": "build_ir_spectrum_definitions",
            "inputs": {"result_label": "sample"},
            "parameters": {},
        },
        style_profile="sci_default",
    )

    payload = definition.to_payload()

    assert payload["figure_id"] == "ir.frame.spectrum.001"
    assert payload["layout"]["panels"][0]["x_axis"]["reversed"] is True
    assert payload["data_sources"][0]["columns"][0]["unit"] == "cm^-1"
```

- [ ] **Step 2: Run tests and verify import failure**

Run:

    pytest tests/test_figure_contracts.py -q

Expected: collection fails because `polynexus.core.figures` does not exist.

- [ ] **Step 3: Implement contracts and profiles**

`contracts.py` must define frozen dataclasses with these public signatures:

```python
from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class DataColumnDefinition:
    name: str
    unit: str
    dtype: str = "float64"

    def to_payload(self) -> dict[str, str]:
        return {"name": self.name, "unit": self.unit, "dtype": self.dtype}


@dataclass(frozen=True)
class FigureDataSourceDefinition:
    source_id: str
    columns: tuple[DataColumnDefinition, ...]
    values: Mapping[str, Sequence[Any]] = field(repr=False, compare=False)
    role: str = "plot_data"

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.source_id,
            "kind": "memory",
            "role": self.role,
            "columns": [column.to_payload() for column in self.columns],
        }


@dataclass(frozen=True)
class AxisDefinition:
    axis_id: str
    label: str
    unit: str = ""
    scale: str = "linear"
    reversed: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "axis_id": self.axis_id,
            "label": self.label,
            "unit": self.unit,
            "scale": self.scale,
            "reversed": self.reversed,
        }


@dataclass(frozen=True)
class PanelDefinition:
    panel_id: str
    row: int
    column: int
    x_axis: AxisDefinition
    y_axis: AxisDefinition

    def to_payload(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "grid_position": {"row": self.row, "column": self.column},
            "x_axis": self.x_axis.to_payload(),
            "y_axis": self.y_axis.to_payload(),
        }


@dataclass(frozen=True)
class FigureLayoutDefinition:
    width_in: float
    height_in: float
    rows: int
    columns: int
    panels: tuple[PanelDefinition, ...]
    horizontal_spacing: float = 0.25
    vertical_spacing: float = 0.25

    def to_payload(self) -> dict[str, Any]:
        return {
            "canvas": {
                "width": self.width_in,
                "height": self.height_in,
                "unit": "inch",
            },
            "grid": {
                "rows": self.rows,
                "columns": self.columns,
                "horizontal_spacing": self.horizontal_spacing,
                "vertical_spacing": self.vertical_spacing,
            },
            "panels": [panel.to_payload() for panel in self.panels],
        }


@dataclass(frozen=True)
class FigureDefinition:
    figure_id: str
    technique: str
    scope: str
    category: str
    title: str
    layout: FigureLayoutDefinition
    data_sources: tuple[FigureDataSourceDefinition, ...]
    objects: tuple[dict[str, Any], ...]
    recipe: Mapping[str, Any]
    style_profile: str

    def with_objects(
        self,
        objects: Sequence[Mapping[str, Any]],
    ) -> "FigureDefinition":
        return replace(
            self,
            objects=tuple(dict(item) for item in objects),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "figure_id": self.figure_id,
            "technique": self.technique,
            "scope": self.scope,
            "category": self.category,
            "title": self.title,
            "layout": self.layout.to_payload(),
            "data_sources": [source.to_payload() for source in self.data_sources],
            "objects": [dict(item) for item in self.objects],
            "recipe": dict(self.recipe),
            "style_profile": self.style_profile,
        }
```

`profiles.py` must define:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class FigureOutputProfile:
    profile_id: str
    preview_filename: str
    preview_dpi: int
    publication_png_dpi: int
    formal_assets: dict[str, str]
    background: str = "white"
    svg_font_policy: str = "editable_text"
    pdf_font_policy: str = "embedded"


_PROFILES = {
    "paper_complete": FigureOutputProfile(
        profile_id="paper_complete",
        preview_filename="preview.png",
        preview_dpi=150,
        publication_png_dpi=600,
        formal_assets={
            "svg": "figure.svg",
            "png": "figure.png",
            "pdf": "figure.pdf",
        },
    ),
}


def get_figure_output_profile(profile_id: str) -> FigureOutputProfile:
    try:
        return _PROFILES[str(profile_id)]
    except KeyError as exc:
        raise ValueError(f"Unknown figure output profile: {profile_id}") from exc
```

Export these types from `polynexus/core/figures/__init__.py`.

- [ ] **Step 4: Run tests and verify pass**

Run:

    pytest tests/test_figure_contracts.py -q

Expected: 2 passed.

- [ ] **Step 5: Commit**

Run:

    git add polynexus/core/figures/__init__.py polynexus/core/figures/contracts.py polynexus/core/figures/profiles.py tests/test_figure_contracts.py
    git commit -m "feat: add figure lifecycle contracts and profiles"

### Task 2: Validate Definitions And Write Portable Data Snapshots

**Files:**

- Create: `polynexus/core/figures/validation.py`
- Create: `polynexus/core/figures/data_writer.py`
- Create: `tests/conftest.py`
- Create: `tests/test_figure_data_writer.py`

- [ ] **Step 1: Write failing validator and writer tests**

Add tests that use the definition fixture from Task 1:

```python
import json
from pathlib import Path

import pytest

from polynexus.core.figures.data_writer import FigureDataSnapshotWriter
from polynexus.core.figures.validation import (
    FigureDefinitionValidationError,
    validate_figure_definition,
)


def test_validator_rejects_unknown_panel(ir_definition):
    broken = ir_definition.with_objects(
        (
            {
                **ir_definition.objects[0],
                "panel_id": "missing-panel",
            },
        )
    )

    with pytest.raises(FigureDefinitionValidationError, match="missing-panel"):
        validate_figure_definition(broken)


def test_data_writer_uses_run_relative_paths_and_schema(ir_definition, tmp_path):
    run_root = tmp_path / "runs" / "run-1"
    figure_dir = run_root / "figures" / ir_definition.figure_id
    writer = FigureDataSnapshotWriter(run_root)

    records = writer.write(ir_definition, figure_dir)

    assert records[0]["path_kind"] == "run_relative"
    assert records[0]["path"].startswith("figures/")
    assert not Path(records[0]["path"]).is_absolute()
    csv_path = run_root / records[0]["path"]
    assert csv_path.read_text(encoding="utf-8").splitlines()[0] == (
        "wavenumber_cm1,absorbance"
    )
    schema = json.loads((figure_dir / "data" / "data_schema.json").read_text("utf-8"))
    assert schema["sources"][0]["columns"][0]["unit"] == "cm^-1"
    assert len(records[0]["sha256"]) == 64
```

Add a `with_objects` helper to `FigureDefinition` using `dataclasses.replace` so tests and later adapters can create immutable variants.

Create shared fixtures in `tests/conftest.py`. Keep imports for modules created in later tasks inside fixture bodies so earlier task tests still collect:

```python
from dataclasses import replace

import pytest

from polynexus.core.figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)


@pytest.fixture
def ir_definition():
    return FigureDefinition(
        figure_id="ir.frame.spectrum.001",
        technique="ir",
        scope="frame",
        category="per_frame",
        title="IR Spectrum",
        layout=FigureLayoutDefinition(
            width_in=2.0,
            height_in=1.0,
            rows=1,
            columns=1,
            panels=(
                PanelDefinition(
                    panel_id="main",
                    row=0,
                    column=0,
                    x_axis=AxisDefinition(
                        axis_id="x",
                        label="Wavenumber",
                        unit="cm^-1",
                        reversed=True,
                    ),
                    y_axis=AxisDefinition(
                        axis_id="y",
                        label="Absorbance",
                        unit="a.u.",
                    ),
                ),
            ),
        ),
        data_sources=(
            FigureDataSourceDefinition(
                source_id="spectrum-data",
                columns=(
                    DataColumnDefinition("wavenumber_cm1", "cm^-1"),
                    DataColumnDefinition("absorbance", "a.u."),
                ),
                values={
                    "wavenumber_cm1": (1800.0, 1700.0),
                    "absorbance": (0.1, 0.4),
                },
            ),
        ),
        objects=(
            {
                "id": "series-spectrum",
                "type": "plot_series",
                "panel_id": "main",
                "data_ref": "spectrum-data",
                "x_column": "wavenumber_cm1",
                "y_column": "absorbance",
                "style": {"color": "#222222", "line_width": 0.8},
            },
        ),
        recipe={
            "module": "tests.conftest",
            "function": "ir_definition",
            "inputs": {"result_label": "sample"},
            "parameters": {},
        },
        style_profile="sci_default",
    )


@pytest.fixture
def invalid_ir_definition(ir_definition):
    return replace(
        ir_definition,
        objects=(
            {
                **ir_definition.objects[0],
                "panel_id": "missing-panel",
            },
        ),
    )


@pytest.fixture
def built_ir_document(ir_definition, tmp_path):
    from polynexus.core.figures.data_writer import FigureDataSnapshotWriter
    from polynexus.core.figures.document_builder import FigureDocumentBuilder

    run_root = tmp_path / "runs" / "run-1"
    figure_dir = run_root / "figures" / ir_definition.figure_id
    records = FigureDataSnapshotWriter(run_root).write(ir_definition, figure_dir)
    document_path, document = FigureDocumentBuilder().write(
        definition=ir_definition,
        run_id="run-1",
        revision=1,
        figure_dir=figure_dir,
        data_sources=records,
    )
    return run_root, document_path, document


@pytest.fixture
def render_plan(built_ir_document):
    from polynexus.core.figures.render_plan import FigureRenderPlanBuilder

    run_root, document_path, document = built_ir_document
    return FigureRenderPlanBuilder(run_root).build(document_path, document)


@pytest.fixture
def complete_inspection():
    from polynexus.core.figures.inspector import FigureArtifactInspection

    return FigureArtifactInspection(
        complete=True,
        errors=(),
        warnings=(),
        dimensions={
            "preview": (300, 150, 150),
            "svg": (144, 72, 96),
            "png": (1200, 600, 600),
            "pdf": (144, 72, 72),
        },
        png_dpi=600,
    )


@pytest.fixture
def three_format_paths(tmp_path):
    from matplotlib.figure import Figure

    paths = {
        "png": tmp_path / "figure.png",
        "svg": tmp_path / "figure.svg",
        "pdf": tmp_path / "figure.pdf",
    }
    for file_format, path in paths.items():
        dpi = 600 if file_format == "png" else 72
        figure = Figure(figsize=(2.0, 1.0), dpi=dpi)
        axis = figure.add_subplot(111)
        axis.plot([0.0, 1.0], [0.0, 1.0])
        figure.savefig(path, format=file_format, dpi=dpi)
    return paths
```

- [ ] **Step 2: Run tests and verify failure**

Run:

    pytest tests/test_figure_data_writer.py -q

Expected: import failures for validation and data writer.

- [ ] **Step 3: Implement validation**

`validation.py` must:

- accept IDs matching `^[a-z0-9]+(?:[._-][a-z0-9]+)*$`
- restrict scope to `frame` or `series` in this slice
- restrict category to `series_overview`, `per_frame`, `diagnostic`, or `supplementary`
- require unique panel, data-source, object, and column IDs
- validate grid positions
- validate equal column lengths
- validate every object `panel_id`
- validate every plot-series `data_ref`, `x_column`, and `y_column`
- raise one `FigureDefinitionValidationError` containing all detected messages

Use this public API:

```python
class FigureDefinitionValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


def validate_figure_definition(definition: FigureDefinition) -> None:
    errors: list[str] = []
    panel_ids = {panel.panel_id for panel in definition.layout.panels}
    source_map = {source.source_id: source for source in definition.data_sources}
    object_ids: set[str] = set()

    if not _FIGURE_ID_PATTERN.fullmatch(definition.figure_id):
        errors.append(f"invalid figure_id: {definition.figure_id}")
    if definition.scope not in {"frame", "series"}:
        errors.append(f"invalid scope: {definition.scope}")
    if definition.category not in _CATEGORIES:
        errors.append(f"invalid category: {definition.category}")

    for panel in definition.layout.panels:
        if panel.row < 0 or panel.row >= definition.layout.rows:
            errors.append(f"panel row out of range: {panel.panel_id}")
        if panel.column < 0 or panel.column >= definition.layout.columns:
            errors.append(f"panel column out of range: {panel.panel_id}")

    for source in definition.data_sources:
        column_names = [column.name for column in source.columns]
        if len(column_names) != len(set(column_names)):
            errors.append(f"duplicate columns in data source: {source.source_id}")
        lengths = {len(source.values.get(name, ())) for name in column_names}
        if set(source.values) != set(column_names):
            errors.append(f"data columns do not match schema: {source.source_id}")
        if len(lengths) > 1:
            errors.append(f"data column lengths differ: {source.source_id}")

    for figure_object in definition.objects:
        object_id = str(figure_object.get("id") or "")
        if not object_id or object_id in object_ids:
            errors.append(f"invalid or duplicate object id: {object_id}")
        object_ids.add(object_id)
        panel_id = str(figure_object.get("panel_id") or "")
        if panel_id not in panel_ids:
            errors.append(f"unknown panel_id: {panel_id}")
        if figure_object.get("type") == "plot_series":
            data_ref = str(figure_object.get("data_ref") or "")
            source = source_map.get(data_ref)
            if source is None:
                errors.append(f"unknown data_ref: {data_ref}")
                continue
            column_names = {column.name for column in source.columns}
            for key in ("x_column", "y_column"):
                column = str(figure_object.get(key) or "")
                if column not in column_names:
                    errors.append(f"unknown {key}: {column}")

    if errors:
        raise FigureDefinitionValidationError(errors)
```

- [ ] **Step 4: Implement the data writer**

`data_writer.py` must write deterministic UTF-8 CSV files and one schema file:

```python
class FigureDataSnapshotWriter:
    def __init__(self, run_root: Path):
        self.run_root = Path(run_root).resolve()

    def write(
        self,
        definition: FigureDefinition,
        figure_dir: Path,
    ) -> list[dict[str, object]]:
        data_dir = Path(figure_dir) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        records: list[dict[str, object]] = []
        schemas: list[dict[str, object]] = []
        for source in definition.data_sources:
            path = data_dir / f"{source.source_id}.csv"
            column_names = [column.name for column in source.columns]
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(column_names)
                writer.writerows(zip(*(source.values[name] for name in column_names)))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            relative = path.resolve().relative_to(self.run_root).as_posix()
            column_payload = [column.to_payload() for column in source.columns]
            records.append(
                {
                    "id": source.source_id,
                    "kind": "csv",
                    "role": source.role,
                    "path": relative,
                    "path_kind": "run_relative",
                    "columns": column_payload,
                    "sha256": digest,
                }
            )
            schemas.append({"id": source.source_id, "columns": column_payload})
        schema_path = data_dir / "data_schema.json"
        schema_path.write_text(
            json.dumps({"sources": schemas}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return records
```

- [ ] **Step 5: Run focused tests**

Run:

    pytest tests/test_figure_contracts.py tests/test_figure_data_writer.py -q

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

    git add polynexus/core/figures/contracts.py polynexus/core/figures/validation.py polynexus/core/figures/data_writer.py tests/conftest.py tests/test_figure_contracts.py tests/test_figure_data_writer.py
    git commit -m "feat: validate figures and snapshot portable data"

### Task 3: Build Portable FigureDocuments

**Files:**

- Modify: `polynexus/core/figure_document.py:239-247`
- Create: `polynexus/core/figures/document_builder.py`
- Create: `tests/test_figure_document_builder.py`
- Modify: `tests/test_figure_document.py`

- [ ] **Step 1: Add failing relative-path compatibility tests**

```python
from polynexus.core.figure_document import normalize_figure_document
from polynexus.core.figures.document_builder import FigureDocumentBuilder


def test_normalize_document_preserves_explicit_run_relative_data_path():
    document = normalize_figure_document(
        {
            "figure_id": "ir.frame.spectrum.001",
            "mode": "object",
            "data_sources": [
                {
                    "id": "spectrum-data",
                    "kind": "csv",
                    "path": "figures/ir.frame.spectrum.001/data/spectrum-data.csv",
                    "path_kind": "run_relative",
                }
            ],
        }
    )

    assert document["data_sources"][0]["path"] == (
        "figures/ir.frame.spectrum.001/data/spectrum-data.csv"
    )


def test_document_builder_writes_layout_revision_and_relative_sources(
    ir_definition,
    tmp_path,
):
    run_root = tmp_path / "runs" / "run-1"
    figure_dir = run_root / "figures" / ir_definition.figure_id
    records = FigureDataSnapshotWriter(run_root).write(ir_definition, figure_dir)

    document_path, document = FigureDocumentBuilder().write(
        definition=ir_definition,
        run_id="run-1",
        revision=1,
        figure_dir=figure_dir,
        data_sources=records,
    )

    assert document_path.name == "figure.pnfig.json"
    assert document["run_id"] == "run-1"
    assert document["revision"] == 1
    assert document["layout"]["panels"][0]["panel_id"] == "main"
    assert document["data_sources"][0]["path_kind"] == "run_relative"
    assert document["objects"][0]["panel_id"] == "main"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

    pytest tests/test_figure_document.py::test_normalize_document_preserves_explicit_run_relative_data_path tests/test_figure_document_builder.py -q

Expected: the current normalizer turns the relative path into an absolute path and the builder import fails.

- [ ] **Step 3: Preserve explicit portable paths**

Update `_normalize_data_source`:

```python
def _normalize_data_source(source: dict) -> dict:
    normalized = deepcopy(source) if isinstance(source, dict) else {}
    normalized.setdefault("id", f"data-{uuid4().hex[:12]}")
    normalized.setdefault("kind", "")
    normalized.setdefault("role", "")
    path = str(normalized.get("path") or "").strip()
    path_kind = str(normalized.get("path_kind") or "").strip().lower()
    if path and path_kind == "run_relative":
        normalized["path"] = Path(path).as_posix()
    elif path:
        normalized["path"] = str(Path(path).resolve())
    return normalized
```

This retains existing absolute-path behavior for legacy documents.

- [ ] **Step 4: Implement FigureDocumentBuilder**

`document_builder.py` must:

- create version 2 object documents
- preserve layout and relative sources
- normalize figure objects through existing `normalize_figure_object`
- write JSON directly to `figure.pnfig.json` with UTF-8
- record empty formal assets until export succeeds

Use:

```python
class FigureDocumentBuilder:
    def write(
        self,
        *,
        definition: FigureDefinition,
        run_id: str,
        revision: int,
        figure_dir: Path,
        data_sources: list[dict[str, object]],
    ) -> tuple[Path, dict[str, object]]:
        now = datetime.now().isoformat(timespec="seconds")
        objects = [
            normalize_figure_object(dict(figure_object))
            for figure_object in definition.objects
        ]
        document = normalize_figure_document(
            {
                "version": 2,
                "run_id": run_id,
                "figure_id": definition.figure_id,
                "revision": int(revision),
                "mode": "object",
                "technique": definition.technique,
                "scope": definition.scope,
                "category": definition.category,
                "title": definition.title,
                "created_at": now,
                "updated_at": now,
                "layout": definition.layout.to_payload(),
                "canvas": definition.layout.to_payload()["canvas"],
                "style": {"profile": definition.style_profile},
                "layers": [
                    {
                        "id": "layer-1",
                        "name": "Layer 1",
                        "visible": True,
                        "locked": False,
                        "object_ids": [item["id"] for item in objects],
                    }
                ],
                "objects": objects,
                "data_sources": data_sources,
                "recipe": dict(definition.recipe),
                "export": {
                    "profile": "",
                    "published_revision": 0,
                    "assets": {},
                },
            }
        )
        path = Path(figure_dir) / "figure.pnfig.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path, document
```

- [ ] **Step 5: Run focused document tests**

Run:

    pytest tests/test_figure_document.py tests/test_figure_document_builder.py -q

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

    git add polynexus/core/figure_document.py polynexus/core/figures/document_builder.py tests/test_figure_document.py tests/test_figure_document_builder.py
    git commit -m "feat: build portable figure lifecycle documents"

### Task 4: Build One Core Render Plan And Renderer

**Files:**

- Create: `polynexus/core/figures/render_plan.py`
- Create: `polynexus/core/figures/renderer.py`
- Create: `tests/test_figure_render_plan_core.py`

- [ ] **Step 1: Write failing render-plan tests**

```python
from matplotlib.figure import Figure

from polynexus.core.figures.render_plan import FigureRenderPlanBuilder
from polynexus.core.figures.renderer import MatplotlibFigureRenderer


def test_render_plan_resolves_relative_csv_and_reversed_axis(
    built_ir_document,
):
    run_root, document_path, document = built_ir_document

    plan = FigureRenderPlanBuilder(run_root).build(document_path, document)

    assert plan.figure_id == "ir.frame.spectrum.001"
    assert plan.revision == 1
    assert plan.panels[0].x_axis.reversed is True
    assert plan.data_tables["spectrum-data"]["absorbance"] == [0.1, 0.4]


def test_renderer_uses_one_plan_for_series_lines_and_text(built_ir_document):
    run_root, document_path, document = built_ir_document
    plan = FigureRenderPlanBuilder(run_root).build(document_path, document)

    figure = MatplotlibFigureRenderer().render(plan, dpi=150)

    assert isinstance(figure, Figure)
    assert len(figure.axes) == 1
    axis = figure.axes[0]
    assert axis.xaxis_inverted()
    assert len(axis.lines) >= 1
```

- [ ] **Step 2: Run tests and verify import failure**

Run:

    pytest tests/test_figure_render_plan_core.py -q

Expected: render-plan and renderer modules are missing.

- [ ] **Step 3: Implement render-plan data resolution**

Define frozen render-plan dataclasses:

```python
@dataclass(frozen=True)
class RenderAxis:
    label: str
    unit: str
    scale: str
    reversed: bool


@dataclass(frozen=True)
class RenderPanel:
    panel_id: str
    row: int
    column: int
    x_axis: RenderAxis
    y_axis: RenderAxis


@dataclass(frozen=True)
class FigureRenderPlan:
    run_id: str
    figure_id: str
    revision: int
    width_in: float
    height_in: float
    rows: int
    columns: int
    panels: tuple[RenderPanel, ...]
    objects: tuple[dict[str, object], ...]
    data_tables: dict[str, dict[str, list[object]]]
    background: str
```

`FigureRenderPlanBuilder` must:

- resolve `run_relative` paths under the supplied run root
- reject paths that escape the run root
- verify stored SHA-256 when present
- read CSV using `csv.DictReader`
- convert values using schema dtype
- build panel and axis objects from the document layout
- reject duplicate panel positions

- [ ] **Step 4: Implement the core Matplotlib renderer**

The first slice supports:

- `plot_series`
- vertical or horizontal `line`
- data-coordinate `text`
- one or more grid panels with independent axes

Use the Figure API without importing `matplotlib.pyplot`:

```python
class MatplotlibFigureRenderer:
    def render(self, plan: FigureRenderPlan, *, dpi: int) -> Figure:
        figure = Figure(
            figsize=(plan.width_in, plan.height_in),
            dpi=dpi,
            facecolor=plan.background,
        )
        grid = figure.add_gridspec(plan.rows, plan.columns)
        axes: dict[str, object] = {}
        for panel in plan.panels:
            axis = figure.add_subplot(grid[panel.row, panel.column])
            axis.set_xlabel(self._axis_label(panel.x_axis))
            axis.set_ylabel(self._axis_label(panel.y_axis))
            axis.set_xscale(panel.x_axis.scale)
            axis.set_yscale(panel.y_axis.scale)
            if panel.x_axis.reversed:
                axis.invert_xaxis()
            if panel.y_axis.reversed:
                axis.invert_yaxis()
            axes[panel.panel_id] = axis

        for figure_object in sorted(
            plan.objects,
            key=lambda item: int(item.get("z_index", 0) or 0),
        ):
            if figure_object.get("visible") is False:
                continue
            axis = axes[str(figure_object["panel_id"])]
            object_type = str(figure_object.get("type") or "")
            if object_type == "plot_series":
                self._render_plot_series(axis, plan, figure_object)
            elif object_type == "line":
                self._render_line(axis, figure_object)
            elif object_type == "text":
                self._render_text(axis, figure_object)
            else:
                raise ValueError(f"Unsupported render object type: {object_type}")

        figure.tight_layout()
        return figure
```

Style mapping must include `color`, `line_width`, `line_style`, `alpha`, `marker`, `marker_size`, and `font_size` with deterministic defaults.

- [ ] **Step 5: Run render tests**

Run:

    pytest tests/test_figure_render_plan_core.py -q

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

    git add polynexus/core/figures/render_plan.py polynexus/core/figures/renderer.py tests/test_figure_render_plan_core.py
    git commit -m "feat: add shared figure render plan"

### Task 5: Export And Inspect The Paper-Complete Asset Group

**Files:**

- Modify: `polynexus/core/figure_assets.py`
- Create: `polynexus/core/figures/inspector.py`
- Create: `polynexus/core/figures/export_service.py`
- Modify: `tests/test_figure_assets.py`
- Create: `tests/test_figure_export_service.py`

- [ ] **Step 1: Write failing dimension and export tests**

```python
from pathlib import Path

import pytest

from polynexus.core.figure_assets import read_figure_asset_dimensions
from polynexus.core.figures.export_service import FigureArtifactExportService
from polynexus.core.figures.profiles import get_figure_output_profile


def test_public_dimension_reader_reports_png_svg_and_pdf(three_format_paths):
    assert read_figure_asset_dimensions(three_format_paths["png"])[0:2] == (
        1200,
        600,
    )
    assert read_figure_asset_dimensions(three_format_paths["svg"])[0:2] == (
        192,
        96,
    )
    assert read_figure_asset_dimensions(three_format_paths["pdf"])[0:2] == (
        144,
        72,
    )


def test_export_service_creates_complete_paper_asset_group(render_plan, tmp_path):
    profile = get_figure_output_profile("paper_complete")

    result = FigureArtifactExportService().export_initial(
        plan=render_plan,
        figure_dir=tmp_path / "figure",
        profile=profile,
    )

    assert set(result.assets) == {"preview", "svg", "png", "pdf"}
    assert all(Path(path).exists() for path in result.assets.values())
    assert result.inspection.complete is True
    assert result.inspection.png_dpi == 600


def test_export_failure_does_not_commit_partial_assets(
    render_plan,
    tmp_path,
    monkeypatch,
):
    service = FigureArtifactExportService()
    monkeypatch.setattr(service, "_save_pdf", lambda *args: (_ for _ in ()).throw(
        RuntimeError("pdf failed")
    ))
    figure_dir = tmp_path / "figure"

    with pytest.raises(RuntimeError, match="pdf failed"):
        service.export_initial(
            plan=render_plan,
            figure_dir=figure_dir,
            profile=get_figure_output_profile("paper_complete"),
        )

    assert not (figure_dir / "assets").exists()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

    pytest tests/test_figure_assets.py tests/test_figure_export_service.py -q

Expected: public reader and export modules are missing.

- [ ] **Step 3: Expose the dimension reader**

Add:

```python
def read_figure_asset_dimensions(path: str | Path) -> tuple[int, int, int]:
    return _read_dimensions_for_path(Path(path).resolve())
```

Keep existing discovery behavior unchanged.

- [ ] **Step 4: Implement artifact inspection**

Define:

```python
@dataclass(frozen=True)
class FigureArtifactInspection:
    complete: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    dimensions: dict[str, tuple[int, int, int]]
    png_dpi: int


class FigureArtifactInspector:
    def inspect(
        self,
        *,
        plan: FigureRenderPlan,
        assets: dict[str, Path],
        profile: FigureOutputProfile,
    ) -> FigureArtifactInspection:
        errors: list[str] = []
        dimensions: dict[str, tuple[int, int, int]] = {}
        required = {"preview", *profile.formal_assets}
        for role in required:
            path = assets.get(role)
            if path is None or not path.is_file() or path.stat().st_size <= 0:
                errors.append(f"missing or empty asset: {role}")
                continue
            dimensions[role] = read_figure_asset_dimensions(path)
        png_dpi = dimensions.get("png", (0, 0, 0))[2]
        if png_dpi != profile.publication_png_dpi:
            errors.append(
                f"publication PNG DPI is {png_dpi}, "
                f"expected {profile.publication_png_dpi}"
            )
        return FigureArtifactInspection(
            complete=not errors,
            errors=tuple(errors),
            warnings=(),
            dimensions=dimensions,
            png_dpi=png_dpi,
        )
```

Also compare SVG/PDF aspect ratios with the plan to a tolerance of 1 percent.

- [ ] **Step 5: Implement initial atomic export**

`FigureArtifactExportService.export_initial` must:

1. reject an existing final `assets` directory
2. create a sibling temporary directory
3. render preview, SVG, 600-DPI PNG, and PDF from the same plan
4. inspect the temporary group
5. remove the temporary group on failure
6. rename it to `assets` only after inspection succeeds

Do not use `bbox_inches="tight"` because it changes physical geometry per format.

Use Matplotlib PDF font type 42 and SVG text mode:

```python
with matplotlib.rc_context(
    {
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
):
    preview = self._renderer.render(plan, dpi=profile.preview_dpi)
    preview.savefig(
        staging / profile.preview_filename,
        format="png",
        dpi=profile.preview_dpi,
        facecolor=profile.background,
    )
    svg = self._renderer.render(plan, dpi=profile.preview_dpi)
    svg.savefig(staging / "figure.svg", format="svg", facecolor=profile.background)
    png = self._renderer.render(plan, dpi=profile.publication_png_dpi)
    png.savefig(
        staging / "figure.png",
        format="png",
        dpi=profile.publication_png_dpi,
        facecolor=profile.background,
    )
    pdf = self._renderer.render(plan, dpi=profile.preview_dpi)
    pdf.savefig(staging / "figure.pdf", format="pdf", facecolor=profile.background)
```

Return asset paths and inspection in a frozen `FigureArtifactExportResult`.

- [ ] **Step 6: Run export tests**

Run:

    pytest tests/test_figure_assets.py tests/test_figure_export_service.py -q

Expected: all tests pass.

- [ ] **Step 7: Commit**

Run:

    git add polynexus/core/figure_assets.py polynexus/core/figures/inspector.py polynexus/core/figures/export_service.py tests/test_figure_assets.py tests/test_figure_export_service.py
    git commit -m "feat: export complete figure asset groups"

### Task 6: Add Capability Reports And Run Manifests

**Files:**

- Create: `polynexus/core/figures/capabilities.py`
- Create: `polynexus/core/figures/manifest.py`
- Create: `tests/test_run_figure_manifest.py`

- [ ] **Step 1: Write failing capability and manifest tests**

```python
import json

from polynexus.core.figures.capabilities import resolve_figure_capabilities
from polynexus.core.figures.manifest import (
    FigureManifestEntry,
    RunFigureManifest,
    RunFigureManifestRepository,
)


def test_capability_report_separates_editing_from_publication(
    render_plan,
    complete_inspection,
):
    report = resolve_figure_capabilities(
        plan=render_plan,
        inspection=complete_inspection,
        working_revision=2,
        published_revision=1,
    )

    assert report.editing_mode == "object"
    assert report.object_editing is True
    assert report.publication_status == "unpublished_changes"


def test_manifest_repository_commits_relative_paths_and_active_pointer(tmp_path):
    repository = RunFigureManifestRepository(tmp_path)
    manifest = RunFigureManifest(
        schema_version=1,
        run_id="run-1",
        technique="ir",
        output_profile="paper_complete",
        figures=(
            FigureManifestEntry(
                figure_id="ir.frame.spectrum.001",
                title="IR Spectrum",
                category="per_frame",
                status="ready",
                document="figures/ir.frame.spectrum.001/figure.pnfig.json",
                data_sources=(
                    "figures/ir.frame.spectrum.001/data/spectrum-data.csv",
                ),
                assets={
                    "preview": "figures/ir.frame.spectrum.001/assets/preview.png",
                    "svg": "figures/ir.frame.spectrum.001/assets/figure.svg",
                    "png": "figures/ir.frame.spectrum.001/assets/figure.png",
                    "pdf": "figures/ir.frame.spectrum.001/assets/figure.pdf",
                },
                capability_report={
                    "editing_mode": "object",
                    "object_editing": True,
                    "static_annotation": True,
                    "reason_code": "",
                    "publication_status": "complete",
                },
                working_revision=1,
                published_revision=1,
                error="",
            ),
        ),
    )

    repository.write_manifest(tmp_path / "runs" / "run-1", manifest)
    repository.activate("run-1")

    payload = json.loads(
        (tmp_path / "runs" / "run-1" / "figure_manifest.json").read_text("utf-8")
    )
    active = json.loads((tmp_path / "active_run.json").read_text("utf-8"))
    assert payload["figures"][0]["document"].startswith("figures/")
    assert active == {"run_id": "run-1"}
```

- [ ] **Step 2: Run tests and verify failure**

Run:

    pytest tests/test_run_figure_manifest.py -q

Expected: capability and manifest imports fail.

- [ ] **Step 3: Implement separate capability axes**

Define `FigureCapabilityReport` with:

- `editing_mode`
- `object_editing`
- `static_annotation`
- `reason_code`
- `publication_status`

The first renderer supports object editing only when:

- every object type is in `{"plot_series", "line", "text"}`
- at least one panel exists
- render plan construction succeeded

Publication status follows:

```python
def _publication_status(
    inspection: FigureArtifactInspection,
    working_revision: int,
    published_revision: int,
) -> str:
    if published_revision <= 0:
        return "not_published"
    if not inspection.complete:
        return "needs_repair"
    if working_revision > published_revision:
        return "unpublished_changes"
    return "complete"
```

- [ ] **Step 4: Implement manifest models and atomic writes**

Use frozen dataclasses with `to_payload()`. `RunFigureManifestRepository` must:

- write JSON to a temporary sibling
- flush and close it
- use `os.replace` for the final manifest
- write `active_run.json` with the same atomic helper
- reject absolute paths in ready entries

- [ ] **Step 5: Run manifest tests**

Run:

    pytest tests/test_run_figure_manifest.py -q

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

    git add polynexus/core/figures/capabilities.py polynexus/core/figures/manifest.py tests/test_run_figure_manifest.py
    git commit -m "feat: add figure capability and run manifests"

### Task 7: Orchestrate One Complete Run

**Files:**

- Create: `polynexus/core/figures/pipeline.py`
- Create: `tests/test_figure_pipeline.py`
- Modify: `polynexus/core/figures/__init__.py`

- [ ] **Step 1: Write failing end-to-end pipeline tests**

```python
import json
from pathlib import Path

from polynexus.core.figures.pipeline import FigurePipeline


def test_pipeline_commits_complete_run_and_active_pointer(
    ir_definition,
    tmp_path,
):
    result = FigurePipeline().run(
        output_root=tmp_path,
        run_id="run-1",
        technique="ir",
        definitions=(ir_definition,),
        profile_id="paper_complete",
    )

    assert result.run_id == "run-1"
    assert result.figures[0].status == "ready"
    run_root = tmp_path / "runs" / "run-1"
    assert (run_root / result.figures[0].document).is_file()
    assert all(
        (run_root / path).is_file()
        for path in result.figures[0].assets.values()
    )
    assert json.loads((tmp_path / "active_run.json").read_text("utf-8")) == {
        "run_id": "run-1"
    }


def test_pipeline_records_failed_definition_without_silent_omission(
    invalid_ir_definition,
    tmp_path,
):
    result = FigurePipeline().run(
        output_root=tmp_path,
        run_id="run-failed",
        technique="ir",
        definitions=(invalid_ir_definition,),
        profile_id="paper_complete",
    )

    assert len(result.figures) == 1
    assert result.figures[0].status == "generation_failed"
    assert result.figures[0].error
    assert result.figures[0].assets == {}
```

- [ ] **Step 2: Run tests and verify failure**

Run:

    pytest tests/test_figure_pipeline.py -q

Expected: pipeline import fails.

- [ ] **Step 3: Implement FigurePipeline**

`FigurePipeline.run` must:

1. reject an empty or already committed run ID
2. create `runs/.<run_id>.staging`
3. process definitions independently
4. record one ready or failed entry per input definition
5. write `run_metadata.json` and `figure_manifest.json` in staging
6. rename staging to `runs/<run_id>`
7. atomically activate the run
8. clean staging on a run-level failure

For each valid definition:

```python
validate_figure_definition(definition)
figure_dir = staging / "figures" / definition.figure_id
data_sources = FigureDataSnapshotWriter(staging).write(definition, figure_dir)
document_path, document = FigureDocumentBuilder().write(
    definition=definition,
    run_id=run_id,
    revision=1,
    figure_dir=figure_dir,
    data_sources=data_sources,
)
plan = FigureRenderPlanBuilder(staging).build(document_path, document)
export = self._exporter.export_initial(
    plan=plan,
    figure_dir=figure_dir,
    profile=profile,
)
capability = resolve_figure_capabilities(
    plan=plan,
    inspection=export.inspection,
    working_revision=1,
    published_revision=1,
)
```

Convert all ready paths to staging-root-relative POSIX paths before creating the entry.

The pipeline must not scan the output directory or reuse historical assets.

- [ ] **Step 4: Export the public pipeline API**

Export `FigurePipeline`, `FigureDefinition`, and `get_figure_output_profile` from `polynexus.core.figures`.

- [ ] **Step 5: Run pipeline tests**

Run:

    pytest tests/test_figure_pipeline.py -q

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

    git add polynexus/core/figures/__init__.py polynexus/core/figures/pipeline.py tests/test_figure_pipeline.py
    git commit -m "feat: orchestrate manifest-backed figure runs"

### Task 8: Add The IR Spectrum Vertical Slice

**Files:**

- Create: `polynexus/core/ir_engine/figure_provider.py`
- Modify: `polynexus/core/ir.py:211-228`
- Create: `tests/test_ir_figure_provider.py`

- [ ] **Step 1: Write failing IR provider tests**

```python
import numpy as np

from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.ir_engine.core import IRResult
from polynexus.core.ir_engine.figure_provider import (
    build_ir_spectrum_definitions,
)


def test_ir_provider_builds_stable_spectrum_definition():
    result = IRResult(
        label="sample-ir",
        wavenumber=np.array([1800.0, 1700.0, 1600.0]),
        absorbance=np.array([0.1, 0.4, 0.2]),
        peaks=[
            {
                "wavenumber": 1700.0,
                "height": 0.4,
                "prominence": 0.3,
                "assignment": "amide I",
            }
        ],
    )

    definitions = build_ir_spectrum_definitions((result,))

    assert len(definitions) == 1
    definition = definitions[0]
    assert definition.figure_id == "ir.frame.spectrum.001"
    assert definition.category == "per_frame"
    assert definition.layout.panels[0].x_axis.reversed is True
    assert definition.objects[0]["type"] == "plot_series"
    assert {item["type"] for item in definition.objects} == {
        "plot_series",
        "line",
        "text",
    }


def test_ir_spectrum_vertical_slice_produces_complete_manifest(tmp_path):
    result = IRResult(
        label="sample-ir",
        wavenumber=np.array([1800.0, 1700.0, 1600.0]),
        absorbance=np.array([0.1, 0.4, 0.2]),
    )

    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="ir-run-1",
        technique="ir",
        definitions=build_ir_spectrum_definitions((result,)),
        profile_id="paper_complete",
    )

    entry = manifest.figures[0]
    assert entry.status == "ready"
    assert entry.capability_report["editing_mode"] == "object"
    assert set(entry.assets) == {"preview", "svg", "png", "pdf"}
```

- [ ] **Step 2: Run tests and verify provider failure**

Run:

    pytest tests/test_ir_figure_provider.py -q

Expected: provider import fails.

- [ ] **Step 3: Implement the IR spectrum provider**

`build_ir_spectrum_definitions` must:

- skip results with empty wavenumber or absorbance arrays
- use stable frame-order IDs
- snapshot wavenumber and absorbance
- build one reversed-x single panel
- add one plot series
- add at most 16 peak lines and labels, ranked by prominence
- include result label in recipe inputs and display metadata
- never import `savefig`, `FigurePipeline`, or output-path helpers

Use:

```python
def build_ir_spectrum_definitions(
    results: Sequence[IRResult],
) -> tuple[FigureDefinition, ...]:
    definitions: list[FigureDefinition] = []
    for index, result in enumerate(results, start=1):
        if len(result.wavenumber) == 0 or len(result.absorbance) == 0:
            continue
        figure_id = f"ir.frame.spectrum.{index:03d}"
        source_id = "spectrum-data"
        objects: list[dict[str, object]] = [
            {
                "id": "series-spectrum",
                "type": "plot_series",
                "panel_id": "main",
                "name": "Absorbance",
                "data_ref": source_id,
                "x_column": "wavenumber_cm1",
                "y_column": "absorbance",
                "style": {"color": "#222222", "line_width": 0.8},
            }
        ]
        ranked_peaks = sorted(
            result.peaks,
            key=lambda item: float(
                item.get("prominence", item.get("height", 0.0)) or 0.0
            ),
            reverse=True,
        )[:16]
        for peak_index, peak in enumerate(ranked_peaks, start=1):
            wavenumber = float(peak["wavenumber"])
            height = float(peak["height"])
            assignment = str(peak.get("assignment") or "")
            label = f"{wavenumber:.0f}"
            if assignment and assignment != "unknown":
                label = f"{label}\n{assignment[:15]}"
            objects.extend(
                [
                    {
                        "id": f"line-peak-{peak_index}",
                        "type": "line",
                        "panel_id": "main",
                        "orientation": "vertical",
                        "x": wavenumber,
                        "style": {
                            "color": "#D55E00",
                            "line_width": 0.5,
                            "line_style": ":",
                            "alpha": 0.5,
                        },
                    },
                    {
                        "id": f"text-peak-{peak_index}",
                        "type": "text",
                        "panel_id": "main",
                        "text": label,
                        "x": wavenumber,
                        "y": height,
                        "rotation": 90.0,
                        "style": {"color": "#D55E00", "font_size": 5},
                    },
                ]
            )
        definitions.append(
            FigureDefinition(
                figure_id=figure_id,
                technique="ir",
                scope="frame",
                category="per_frame",
                title=f"IR Spectrum - {result.label}",
                layout=_ir_spectrum_layout(),
                data_sources=(
                    FigureDataSourceDefinition(
                        source_id=source_id,
                        columns=(
                            DataColumnDefinition("wavenumber_cm1", "cm^-1"),
                            DataColumnDefinition("absorbance", "a.u."),
                        ),
                        values={
                            "wavenumber_cm1": tuple(
                                float(value) for value in result.wavenumber
                            ),
                            "absorbance": tuple(
                                float(value) for value in result.absorbance
                            ),
                        },
                    ),
                ),
                objects=tuple(objects),
                recipe={
                    "module": "polynexus.core.ir_engine.figure_provider",
                    "function": "build_ir_spectrum_definitions",
                    "inputs": {"result_label": result.label},
                    "parameters": {"frame_index": index},
                },
                style_profile="sci_default",
            )
        )
    return tuple(definitions)
```

- [ ] **Step 4: Expose definitions from IREngine**

Add a non-publishing method without changing `plot()` yet:

```python
def build_figure_definitions(self):
    from .ir_engine.figure_provider import build_ir_spectrum_definitions

    return build_ir_spectrum_definitions(tuple(self._results))
```

This is the explicit handoff point for the future orchestrator migration. Existing production output remains unchanged until the complete IR provider set is available.

- [ ] **Step 5: Run IR vertical-slice tests**

Run:

    pytest tests/test_ir_figure_provider.py tests/test_ir_figure_document.py -q

Expected: all tests pass and legacy IR document tests remain green.

- [ ] **Step 6: Commit**

Run:

    git add polynexus/core/ir_engine/figure_provider.py polynexus/core/ir.py tests/test_ir_figure_provider.py
    git commit -m "feat: add IR figure lifecycle provider"

### Task 9: Add Foundation Quality Gates And Run The Full Verification

**Files:**

- Modify: `scripts/quality_gate.py`
- Modify: `tests/test_quality_gate.py`

- [ ] **Step 1: Write failing quality-gate tests**

Add tests for a pure helper that scans migrated provider sources:

```python
def test_figure_provider_gate_rejects_direct_savefig(tmp_path):
    provider = tmp_path / "figure_provider.py"
    provider.write_text("figure.savefig('figure.pdf')\n", encoding="utf-8")

    failures = scan_migrated_figure_provider(provider)

    assert failures == [
        "figure_provider.py: migrated figure providers must not call savefig"
    ]


def test_figure_provider_gate_rejects_hard_coded_output_extensions(tmp_path):
    provider = tmp_path / "figure_provider.py"
    provider.write_text("path = 'result.svg'\n", encoding="utf-8")

    failures = scan_migrated_figure_provider(provider)

    assert failures == [
        "figure_provider.py: migrated figure providers must not choose output formats"
    ]


def test_real_ir_provider_passes_figure_provider_gate():
    failures = scan_migrated_figure_provider(
        Path("polynexus/core/ir_engine/figure_provider.py")
    )

    assert failures == []
```

- [ ] **Step 2: Run focused tests and verify failure**

Run:

    pytest tests/test_quality_gate.py -k "figure_provider_gate or real_ir_provider" -q

Expected: helper import or assertions fail.

- [ ] **Step 3: Implement provider-source checks**

Use Python tokenization or AST for `savefig` call detection and string-literal scanning for `.pdf`, `.svg`, `.png`, `.jpg`, `.jpeg`, and `.tiff`.

The gate applies initially to:

- `polynexus/core/ir_engine/figure_provider.py`
- files under `polynexus/core/figures/` except `renderer.py` and `export_service.py`

It must not scan legacy `ir_output.py` until that module is formally migrated.

- [ ] **Step 4: Run the foundation suite**

Run:

    pytest tests/test_figure_contracts.py tests/test_figure_data_writer.py tests/test_figure_document.py tests/test_figure_document_builder.py tests/test_figure_render_plan_core.py tests/test_figure_assets.py tests/test_figure_export_service.py tests/test_run_figure_manifest.py tests/test_figure_pipeline.py tests/test_ir_figure_provider.py tests/test_ir_figure_document.py tests/test_quality_gate.py -q

Expected: all selected tests pass.

- [ ] **Step 5: Run lint and diff checks**

Run:

    python -m ruff check polynexus/core/figures polynexus/core/ir_engine/figure_provider.py tests/test_figure_contracts.py tests/test_figure_data_writer.py tests/test_figure_document_builder.py tests/test_figure_render_plan_core.py tests/test_figure_export_service.py tests/test_run_figure_manifest.py tests/test_figure_pipeline.py tests/test_ir_figure_provider.py
    git diff --check

Expected: both commands exit 0.

- [ ] **Step 6: Run one real artifact smoke test**

Run:

    pytest tests/test_ir_figure_provider.py::test_ir_spectrum_vertical_slice_produces_complete_manifest -vv

Expected: 1 passed. Inspect the temporary-test assertions to confirm the manifest points to preview, SVG, 600-DPI PNG, and PDF from one run.

- [ ] **Step 7: Commit**

Run:

    git add scripts/quality_gate.py tests/test_quality_gate.py
    git commit -m "test: enforce figure lifecycle provider boundaries"

## Plan Self-Review

### Spec coverage

This plan covers the first approved implementation boundary:

- contract and stable identity
- `paper_complete` roles
- portable relative data paths
- document, data, render plan, assets, capability, and manifest
- initial atomic generation
- explicit failed entries
- IR spectrum proof
- provider boundary enforcement

The following umbrella requirements have deliberate follow-up plans and are not silently omitted:

- all remaining technique providers
- production gallery switch
- editor integration
- existing asset-group republish
- multi-panel renderer expansion
- legacy recovery

### Placeholder scan

The plan contains no TBD, TODO, “implement later,” or unspecified error-handling steps. Deferred features are named in the scope boundary and mapped to later implementation waves.

### Type consistency

Public names used throughout the plan are:

- `FigureDefinition`
- `FigureDataSourceDefinition`
- `FigureLayoutDefinition`
- `FigureRenderPlan`
- `FigureOutputProfile`
- `FigureArtifactInspection`
- `FigureCapabilityReport`
- `FigureManifestEntry`
- `RunFigureManifest`
- `FigurePipeline`

`paper_complete` consistently requires `preview`, `svg`, `png`, and `pdf` roles. `working_revision` and `published_revision` are integers in documents, capability resolution, and manifests.

## Execution Handoff

Execute inline in this goal using `superpowers:executing-plans`. Multi-agent delegation is intentionally not used because the current collaboration policy permits subagents only when the user explicitly requests them.
