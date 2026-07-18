# OriginLab Optional Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional, Windows-only OriginLab export path that preserves standalone PolyNexus operation, supports newer Python integration and older COM/LabTalk automation, and always falls back to an Origin-compatible package.

**Architecture:** Introduce a structural `OriginAdapter` Protocol and immutable export contracts. `OriginExportService` will iterate an injected priority-ordered adapter registry and will not contain Origin-version conditionals. A pure package exporter remains the final adapter, while direct adapters are lazily imported and executed outside the Qt event loop.

**Tech Stack:** Python 3.10+, PySide6, existing JSON figure documents, CSV/JSON/PNG/SVG/PDF assets, optional `pywin32`, optional `originpro`, pytest, and existing application logging/i18n.

---

## Files and responsibilities

### New production files

- Create: `polynexus/origin/__init__.py` — public exports for the integration boundary.
- Create: `polynexus/origin/adapter_base.py` — structural `OriginAdapter` Protocol only.
- Create: `polynexus/origin/contracts.py` — request, capability, status, warning, and result dataclasses.
- Create: `polynexus/origin/capability_probe.py` — injectable, non-invasive Origin and optional-dependency detection.
- Create: `polynexus/origin/registry.py` — default adapter construction and priority ordering; no dispatch branches.
- Create: `polynexus/origin/mapping.py` — pure mapping from the normalized PolyNexus figure document to supported Origin data/plot/annotation specifications.
- Create: `polynexus/origin/package_exporter.py` — no-Origin bundle generation with containment and atomic staging.
- Create: `polynexus/origin/com_labtalk_adapter.py` — lazy COM connection, safe LabTalk generation, and compatibility-mode export.
- Create: `polynexus/origin/originpro_adapter.py` — lazy high-level Python integration and editable Origin export.
- Create: `polynexus/origin/service.py` — responsibility-chain orchestration and result normalization.
- Create: `polynexus/gui/origin_export_worker.py` — `QThread` worker that keeps direct Origin calls off the Qt event loop.
- Create: `polynexus/gui/widgets/chart_editor_origin_mixin.py` — Export Inspector action, request construction, worker lifecycle, and result presentation.

### Modified production files

- Modify: `polynexus/gui/widgets/chart_editor.py` — include the Origin export mixin, expose the button in the existing Export Inspector, and keep current editor export behavior unchanged.
- Modify: `polynexus/gui/i18n.py` — add Chinese and English labels/status text for Origin export and downgrade messages.
- Modify: `pyproject.toml` — add only the optional `origin` extra for `pywin32`; keep `originpro` lazy and out of base dependencies because its availability is controlled by the Origin installation.
- Modify: `README.md` — document optional Windows setup, capability-based behavior, and the no-Origin package fallback.

### New tests

- Create: `tests/test_origin_contracts.py`
- Create: `tests/test_origin_capability_probe.py`
- Create: `tests/test_origin_registry.py`
- Create: `tests/test_origin_mapping.py`
- Create: `tests/test_origin_package_exporter.py`
- Create: `tests/test_origin_service.py`
- Create: `tests/test_origin_com_adapter.py`
- Create: `tests/test_originpro_adapter.py`
- Create: `tests/test_chart_editor_origin_export.py`

### Existing regression coverage to preserve

- Preserve: `tests/test_chart_editor.py`
- Preserve: `tests/test_chart_editor_save_mixin.py`
- Preserve: `tests/test_figure_document.py`
- Preserve: `tests/test_figure_data_writer.py`
- Preserve: `tests/test_main_window_figure_mixin.py`

## Task 1: Define the adapter contracts and Protocol

**Files:**

- Create: `polynexus/origin/__init__.py`
- Create: `polynexus/origin/adapter_base.py`
- Create: `polynexus/origin/contracts.py`
- Create: `tests/test_origin_contracts.py`

- [ ] **Step 1: Write failing contract tests**

Add tests for immutable requests/results, mode values, status values, and a
fake adapter that conforms structurally without inheriting from a PolyNexus
class:

```python
from pathlib import Path

import pytest

from polynexus.origin.adapter_base import OriginAdapter
from polynexus.origin.contracts import ExportRequest, ExportResult


def test_export_request_normalizes_paths_and_is_immutable(tmp_path):
    request = ExportRequest(
        document={"figure_id": "fig-1"},
        figure_path=tmp_path / "figure.svg",
        output_root=tmp_path / "out",
        mode="editable_origin",
    )

    assert request.figure_path == (tmp_path / "figure.svg").resolve()
    assert request.output_root == (tmp_path / "out").resolve()
    with pytest.raises(AttributeError):
        request.mode = "package"


def test_export_result_exposes_success_and_recoverability(tmp_path):
    result = ExportResult(
        status="success",
        adapter_id="package",
        artifacts=(tmp_path / "Origin_Export",),
    )

    assert result.success is True
    assert result.recoverable is False


def test_protocol_accepts_structural_fake_adapter():
    class FakeAdapter:
        adapter_id = "fake"
        priority = 1

        def can_handle(self, request):
            return True

        def export(self, request):
            return ExportResult.success_result(self.adapter_id)

    adapter: OriginAdapter = FakeAdapter()
    assert adapter.can_handle(ExportRequest(document={}, output_root=Path(".")))


def test_invalid_mode_is_rejected():
    with pytest.raises(ValueError):
        ExportRequest(document={}, output_root=Path("."), mode="unknown")
```

- [ ] **Step 2: Run the tests and verify the contract is missing**

Run:

```powershell
pytest tests/test_origin_contracts.py -q
```

Expected: FAIL with an import error because `polynexus.origin` does not exist.

- [ ] **Step 3: Implement the minimal contracts**

Use frozen dataclasses and `Literal` aliases. The central shape must be:

```python
# polynexus/origin/contracts.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

ExportMode = Literal["editable_origin", "visual_fidelity", "package"]
ExportStatus = Literal["success", "unavailable", "failed", "partial"]


@dataclass(frozen=True)
class ExportRequest:
    document: Mapping[str, Any]
    output_root: Path
    figure_path: Path | None = None
    mode: ExportMode = "editable_origin"
    allow_open_origin: bool = True
    preferred_adapter: str | None = None

    def __post_init__(self):
        if self.mode not in {"editable_origin", "visual_fidelity", "package"}:
            raise ValueError(f"unsupported Origin export mode: {self.mode}")
        object.__setattr__(self, "output_root", Path(self.output_root).resolve())
        if self.figure_path is not None:
            object.__setattr__(self, "figure_path", Path(self.figure_path).resolve())


@dataclass(frozen=True)
class CapabilityReport:
    adapter_id: str
    available: bool
    reason: str = ""
    origin_version: str = ""
    supported_modes: tuple[str, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExportResult:
    status: ExportStatus
    adapter_id: str
    artifacts: tuple[Path, ...] = ()
    warnings: tuple[str, ...] = ()
    message: str = ""
    capability: CapabilityReport | None = None
    recoverable: bool = False

    @property
    def success(self) -> bool:
        return self.status == "success"

    @classmethod
    def success_result(cls, adapter_id: str, *artifacts: Path, **kwargs):
        return cls(status="success", adapter_id=adapter_id, artifacts=tuple(artifacts), **kwargs)
```

Add `OriginAdapter` as a `Protocol` with `adapter_id`, `priority`,
`can_handle(request) -> bool`, and `export(request) -> ExportResult`.

- [ ] **Step 4: Run the contract tests**

Run:

```powershell
pytest tests/test_origin_contracts.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the contract boundary**

```powershell
git add polynexus/origin tests/test_origin_contracts.py
git commit -m "feat: define Origin export adapter contracts"
```

## Task 2: Add capability probing and adapter registration

**Files:**

- Create: `polynexus/origin/capability_probe.py`
- Create: `polynexus/origin/registry.py`
- Create: `tests/test_origin_capability_probe.py`
- Create: `tests/test_origin_registry.py`

- [ ] **Step 1: Write failing capability and registry tests**

Cover non-Windows fallback, missing optional modules, available high-level
integration, available COM, and descending priority without importing optional
modules during registry construction:

```python
from polynexus.origin.capability_probe import OriginCapabilityProbe
from polynexus.origin.registry import order_adapters


def test_probe_is_unavailable_without_windows(monkeypatch):
    monkeypatch.setattr("polynexus.origin.capability_probe.platform.system", lambda: "Linux")
    report = OriginCapabilityProbe().probe()
    assert report.installed is False
    assert report.com_available is False
    assert "Windows" in report.reason


def test_probe_reports_optional_integrations_independently(monkeypatch):
    monkeypatch.setattr("polynexus.origin.capability_probe.platform.system", lambda: "Windows")
    monkeypatch.setattr(
        "polynexus.origin.capability_probe.importlib.util.find_spec",
        lambda name: object() if name == "originpro" else None,
    )
    report = OriginCapabilityProbe(
        installation_finder=lambda: (True, "2026.1"),
        com_server_finder=lambda: True,
    ).probe()
    assert report.installed is True
    assert report.originpro_available is True
    assert report.com_available is True


def test_registry_orders_injected_adapters_without_importing_concrete_modules():
    class FakeAdapter:
        def __init__(self, adapter_id, priority):
            self.adapter_id = adapter_id
            self.priority = priority

    adapters = order_adapters([
        FakeAdapter("package", 10),
        FakeAdapter("originpro", 100),
        FakeAdapter("com_labtalk", 80),
    ])
    assert [adapter.adapter_id for adapter in adapters] == [
        "originpro",
        "com_labtalk",
        "package",
    ]
```

- [ ] **Step 2: Run the tests and verify the probe/registry are missing**

Run:

```powershell
pytest tests/test_origin_capability_probe.py tests/test_origin_registry.py -q
```

Expected: FAIL because the probe and registry modules do not exist.

- [ ] **Step 3: Implement the injectable probe**

Implement `OriginCapability` as a frozen dataclass with `installed`, `version`,
`originpro_available`, `com_available`, and `reason`. `OriginCapabilityProbe`
must inject `installation_finder`, `com_server_finder`, and `module_finder` for
tests. The default finder may use `platform`, `importlib.util.find_spec`, and
Windows registry/known executable discovery, but it must never launch Origin.

The public behavior must follow this shape:

```python
class OriginCapabilityProbe:
    def __init__(self, *, installation_finder=None, com_server_finder=None, module_finder=None):
        self._installation_finder = installation_finder or _find_installation
        self._com_server_finder = com_server_finder or _find_com_server
        self._module_finder = module_finder or _module_available

    def probe(self) -> OriginCapability:
        if platform.system() != "Windows":
            return OriginCapability(False, reason="Origin automation requires Windows")
        installed, version = self._installation_finder()
        originpro_available = self._module_finder("originpro")
        com_available = self._module_finder("win32com.client") and self._com_server_finder()
        reason = "" if installed else "Origin installation was not detected"
        return OriginCapability(
            installed=bool(installed),
            version=str(version or ""),
            originpro_available=bool(originpro_available),
            com_available=bool(com_available),
            reason=reason,
        )
```

All OS/import/registry exceptions become a negative capability, not a raised
startup exception.

- [ ] **Step 4: Implement the registry without dispatch logic**

Construct adapters in priority order and keep all version/capability checks in
the adapters or probe. The registry must not call `if adapter_id == ...`:

```python
def order_adapters(adapters):
    return tuple(sorted(adapters, key=lambda adapter: adapter.priority, reverse=True))


def build_default_adapters():
    from .com_labtalk_adapter import ComLabTalkAdapter
    from .originpro_adapter import OriginProAdapter
    from .package_exporter import PackageExporter

    return order_adapters(
        (OriginProAdapter(), ComLabTalkAdapter(), PackageExporter()),
    )
```

The module-level construction must not import `originpro` or `win32com`; those
imports remain inside adapter methods. The default factory is exercised only
after the concrete adapter modules exist; Task 2 tests use `order_adapters()`
with fakes so this task remains independently runnable.

- [ ] **Step 5: Run probe and registry tests**

Run:

```powershell
pytest tests/test_origin_capability_probe.py tests/test_origin_registry.py -q
```

Expected: PASS on Windows and non-Windows hosts.

- [ ] **Step 6: Commit capability detection**

```powershell
git add polynexus/origin tests/test_origin_capability_probe.py tests/test_origin_registry.py
git commit -m "feat: add Origin capability probe and adapter registry"
```

## Task 3: Normalize figure mappings and build the no-Origin package exporter

**Files:**

- Create: `polynexus/origin/mapping.py`
- Create: `polynexus/origin/package_exporter.py`
- Create: `tests/test_origin_mapping.py`
- Create: `tests/test_origin_package_exporter.py`

- [ ] **Step 1: Write mapping tests for supported and unsupported objects**

Use the existing JSON-friendly document shape (`data_sources`, `objects`,
`style`, `recipe`) and assert that series references, axis labels, titles, and
simple annotations map correctly while heatmap/background transforms create
warnings:

```python
from polynexus.origin.mapping import map_figure_document


def test_mapping_preserves_series_columns_and_basic_style():
    document = {
        "figure_id": "saxs-1",
        "style": {"title": "Intensity", "xlabel": "q", "ylabel": "I(q)"},
        "data_sources": [{"id": "source-1", "path": "data/source-1.csv"}],
        "objects": [{
            "id": "series-1",
            "type": "plot_series",
            "name": "sample",
            "data_ref": "source-1",
            "x_column": "q",
            "y_column": "intensity",
            "style": {"color": "#336699", "line_width": 1.5},
        }],
    }

    mapped = map_figure_document(document)
    assert mapped.title == "Intensity"
    assert mapped.sources[0].source_id == "source-1"
    assert mapped.plots[0].x_column == "q"
    assert mapped.plots[0].y_column == "intensity"
    assert mapped.plots[0].style["color"] == "#336699"
    assert mapped.warnings == ()


def test_mapping_reports_unsupported_objects_without_dropping_the_document():
    mapped = map_figure_document({"objects": [{"type": "image_background"}]})
    assert mapped.warnings
    assert "image_background" in mapped.warnings[0]
```

- [ ] **Step 2: Run mapping tests and confirm they fail**

Run:

```powershell
pytest tests/test_origin_mapping.py -q
```

Expected: FAIL because the mapping module is missing.

- [ ] **Step 3: Implement the pure mapping model**

Define frozen `OriginSourceSpec`, `OriginPlotSpec`, `OriginAnnotationSpec`, and
`OriginFigureModel` dataclasses. `map_figure_document()` must call the existing
`normalize_figure_document()` first, map `plot_series`, `line`, `arrow`,
`rectangle`, and `text`, and append one explicit warning per unsupported object
type. It must preserve `data_ref`, `x_column`, `y_column`, `lower_y_column`,
`upper_y_column`, style fields, title, and axis labels without mutating the
input dictionary.

- [ ] **Step 4: Write package exporter tests**

Cover package contents, source copying, metadata warnings, visual assets, and
output-root containment:

```python
import json

from polynexus.origin.contracts import ExportRequest
from polynexus.origin.package_exporter import PackageExporter


def test_package_exporter_writes_self_contained_bundle(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("q,intensity\n0.1,2.0\n", encoding="utf-8")
    preview = tmp_path / "figure.png"
    preview.write_bytes(b"png")
    request = ExportRequest(
        document={
            "figure_id": "fig-1",
            "data_sources": [{"id": "data-1", "path": str(source)}],
            "objects": [],
        },
        figure_path=preview,
        output_root=tmp_path / "out",
        mode="package",
    )

    result = PackageExporter().export(request)
    root = tmp_path / "out" / "Origin_Export"
    assert result.success is True
    assert (root / "data" / "data-1.csv").exists()
    assert (root / "figure_document.json").exists()
    assert (root / "metadata.json").exists()
    assert (root / "preview.png").read_bytes() == b"png"
    assert json.loads((root / "metadata.json").read_text(encoding="utf-8"))["adapter_id"] == "package"


def test_package_exporter_rejects_source_outside_output_policy(tmp_path):
    request = ExportRequest(
        document={"data_sources": [{"id": "bad", "path": "../../outside.csv"}]},
        output_root=tmp_path / "out",
        mode="package",
    )
    result = PackageExporter().export(request)
    assert result.status in {"failed", "partial"}
```

- [ ] **Step 5: Run package tests and confirm they fail**

Run:

```powershell
pytest tests/test_origin_package_exporter.py -q
```

Expected: FAIL because `PackageExporter` is missing.

- [ ] **Step 6: Implement staging, copying, and metadata**

`PackageExporter` must have `adapter_id = "package"`, the lowest priority, and
`can_handle()` returning `True` for every mode. An editable request may still
fall back to a package, but the result message must identify that downgrade.
It must create a unique staging directory below `output_root`, write:

```text
Origin_Export/data/*.csv
Origin_Export/figure_document.json
Origin_Export/metadata.json
Origin_Export/preview.png|svg|pdf when present
Origin_Export/import.ogs for data imports
```

Use the existing normalized document and JSON serialization conventions. Resolve
every source path, reject paths that do not exist or escape the approved source
root, and copy only into staging. Rename staging to the final directory only
after all required writes complete. Return `PARTIAL` with artifacts and a
warning when an optional preview is missing; return `FAILED` when data or
metadata cannot be written.

- [ ] **Step 7: Run mapping and package tests**

Run:

```powershell
pytest tests/test_origin_mapping.py tests/test_origin_package_exporter.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit the fallback exporter**

```powershell
git add polynexus/origin tests/test_origin_mapping.py tests/test_origin_package_exporter.py
git commit -m "feat: add Origin-compatible package exporter"
```

## Task 4: Implement the responsibility-chain service

**Files:**

- Create: `polynexus/origin/service.py`
- Modify: `polynexus/origin/__init__.py`
- Create: `tests/test_origin_service.py`

- [ ] **Step 1: Write chain behavior tests**

Use fake adapters with explicit results to test priority selection, unavailable
fallback, terminal failure, partial-result propagation, and preferred adapter
selection:

```python
from polynexus.origin.contracts import ExportRequest, ExportResult
from polynexus.origin.service import OriginExportService


class FakeAdapter:
    def __init__(self, adapter_id, priority, can_handle, result):
        self.adapter_id = adapter_id
        self.priority = priority
        self._can_handle = can_handle
        self._result = result
        self.calls = 0

    def can_handle(self, request):
        return self._can_handle

    def export(self, request):
        self.calls += 1
        return self._result


def test_unavailable_adapter_yields_to_next_priority(tmp_path):
    first = FakeAdapter("first", 100, True, ExportResult("unavailable", "first"))
    second = FakeAdapter("second", 10, True, ExportResult.success_result("second"))
    result = OriginExportService([first, second]).export(
        ExportRequest(document={}, output_root=tmp_path)
    )
    assert result.adapter_id == "second"
    assert first.calls == 1
    assert second.calls == 1


def test_terminal_failure_does_not_hide_partial_external_work(tmp_path):
    failed = FakeAdapter("com", 100, True, ExportResult("partial", "com"))
    fallback = FakeAdapter("package", 10, True, ExportResult.success_result("package"))
    result = OriginExportService([failed, fallback]).export(
        ExportRequest(document={}, output_root=tmp_path)
    )
    assert result.status == "partial"
    assert fallback.calls == 0
```

- [ ] **Step 2: Run the service tests and confirm they fail**

Run:

```powershell
pytest tests/test_origin_service.py -q
```

Expected: FAIL because `OriginExportService` is missing.

- [ ] **Step 3: Implement normalization and dispatch**

The service constructor accepts `adapters: Sequence[OriginAdapter]`. It sorts
copies by descending `priority`, normalizes the request output root, and runs:

```python
for adapter in self._adapters:
    if request.preferred_adapter and adapter.adapter_id != request.preferred_adapter:
        continue
    if not adapter.can_handle(request):
        continue
    result = adapter.export(request)
    if result.status == "success":
        return result
    if result.status == "unavailable":
        continue
    return result
return ExportResult(
    status="failed",
    adapter_id="service",
    message="No Origin export adapter can handle this request",
    recoverable=True,
)
```

The service must not import or name `originpro`, `win32com`, or any concrete
adapter. Exported helper `default_origin_export_service()` may construct the
registry, but tests must be able to inject fakes.

- [ ] **Step 4: Run service tests**

Run:

```powershell
pytest tests/test_origin_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the chain service**

```powershell
git add polynexus/origin tests/test_origin_service.py
git commit -m "feat: add Origin adapter responsibility chain"
```

## Task 5: Add the COM/LabTalk compatibility adapter

**Files:**

- Create: `polynexus/origin/com_labtalk_adapter.py`
- Create: `tests/test_origin_com_adapter.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write fake-COM tests before implementation**

Test capability gating, CSV import, generated plot commands, safe escaping,
successful save, and a COM error returning a recoverable result before any
fallback is attempted:

```python
from polynexus.origin.com_labtalk_adapter import ComLabTalkAdapter
from polynexus.origin.contracts import ExportRequest


class FakeOriginApplication:
    def __init__(self):
        self.commands = []
        self.saved = []

    def LTExec(self, command):
        self.commands.append(command)

    def Save(self, path):
        self.saved.append(path)


def test_com_adapter_imports_data_and_saves_project(tmp_path):
    app = FakeOriginApplication()
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("x,y\n1,2\n", encoding="utf-8")
    request = ExportRequest(
        document={
            "figure_id": "fig-1",
            "data_sources": [{"id": "data-1", "path": str(csv_path)}],
            "objects": [{"type": "plot_series", "data_ref": "data-1", "x_column": "x", "y_column": "y"}],
        },
        output_root=tmp_path / "out",
        mode="editable_origin",
    )
    adapter = ComLabTalkAdapter(app_factory=lambda: app, com_available=lambda: True)
    result = adapter.export(request)
    assert result.success is True
    assert any("data.csv" in command for command in app.commands)
    assert app.saved


def test_labtalk_values_are_escaped(tmp_path):
    app = FakeOriginApplication()
    adapter = ComLabTalkAdapter(app_factory=lambda: app, com_available=lambda: True)
    request = ExportRequest(
        document={"figure_id": 'bad";pause(1);//'},
        output_root=tmp_path / "out",
        mode="editable_origin",
    )
    result = adapter.export(request)
    assert result.status in {"success", "partial"}
    assert "pause(1)" not in "\n".join(app.commands)
```

- [ ] **Step 2: Run COM tests and confirm they fail**

Run:

```powershell
pytest tests/test_origin_com_adapter.py -q
```

Expected: FAIL because `ComLabTalkAdapter` is missing.

- [ ] **Step 3: Add the optional dependency without changing base install**

Extend `pyproject.toml` with:

```toml
[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0", "ruff>=0.6.0"]
origin = ["pywin32>=306"]
```

Do not add `pywin32` to `project.dependencies`. Do not add `originpro` to the
base install or import it from package initialization.

- [ ] **Step 4: Implement the lazy COM adapter**

Use `adapter_id = "com_labtalk"`, `priority = 80`, and `can_handle()` that
returns false unless the request mode is `editable_origin`, Windows is active,
and the injected/default COM capability check succeeds. Import
`win32com.client` only inside the default app factory. Try the supported Origin
automation ProgIDs in a fixed tuple and return `UNAVAILABLE` if none connects.

Generate only bounded commands from mapped data and style fields. Escape text
and paths before inserting them into LabTalk. Import CSV snapshots rather than
embedding numeric arrays in commands. Call `Save()` only after workbook/graph
creation completes. Catch COM/import errors, include a concise warning, and
return `FAILED` or `PARTIAL` according to whether an Origin application object
was created or a project was saved.

- [ ] **Step 5: Run COM tests and dependency-free import checks**

Run:

```powershell
pytest tests/test_origin_com_adapter.py -q
python -c "import polynexus.origin.com_labtalk_adapter; print('ok')"
```

Expected: PASS without `pywin32` installed because the module import is lazy.

- [ ] **Step 6: Commit COM compatibility**

```powershell
git add polynexus/origin/com_labtalk_adapter.py tests/test_origin_com_adapter.py pyproject.toml
git commit -m "feat: add COM LabTalk Origin compatibility adapter"
```

## Task 6: Add the newer high-level Python adapter

**Files:**

- Create: `polynexus/origin/originpro_adapter.py`
- Create: `tests/test_originpro_adapter.py`

- [ ] **Step 1: Write fake-originpro tests**

Inject a fake `originpro` facade and verify that the adapter creates worksheets,
transfers columns, creates editable plots, applies supported styles, and saves
through the Origin facade. Verify that unsupported mappings are returned as
warnings instead of raising:

```python
from polynexus.origin.contracts import ExportRequest
from polynexus.origin.originpro_adapter import OriginProAdapter


class FakeOriginPro:
    def __init__(self):
        self.events = []

    def new_book(self, kind="w"):
        self.events.append(("new_book", kind))
        return self

    def add_sheet(self, name):
        self.events.append(("add_sheet", name))
        return self

    def from_csv(self, path):
        self.events.append(("from_csv", str(path)))

    def add_plot(self, x_column, y_column, style):
        self.events.append(("add_plot", x_column, y_column, style))

    def save(self, path):
        self.events.append(("save", str(path)))


def test_originpro_adapter_builds_editable_graph(tmp_path):
    facade = FakeOriginPro()
    source = tmp_path / "data.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    request = ExportRequest(
        document={
            "figure_id": "fig-1",
            "data_sources": [{"id": "data-1", "path": str(source)}],
            "objects": [{"type": "plot_series", "data_ref": "data-1", "x_column": "x", "y_column": "y"}],
        },
        output_root=tmp_path / "out",
        mode="editable_origin",
    )
    result = OriginProAdapter(originpro_factory=lambda: facade).export(request)
    assert result.success is True
    assert ("from_csv", str(source)) in facade.events
    assert any(event[0] == "add_plot" for event in facade.events)
```

- [ ] **Step 2: Run the high-level adapter tests and confirm they fail**

Run:

```powershell
pytest tests/test_originpro_adapter.py -q
```

Expected: FAIL because `OriginProAdapter` is missing.

- [ ] **Step 3: Implement lazy high-level integration**

Use `adapter_id = "originpro"`, `priority = 100`, and gate the adapter on
`editable_origin` plus a successful capability check for both the module and a
usable Origin session. The default factory imports `originpro` inside the
method only. Keep the adapter facade calls isolated so the tests do not need a
real Origin installation.

Transfer data by source, then create only plot/axis/style features represented
by the mapping model. Return warnings for unsupported objects and return a
native project artifact path only after Origin confirms the save. Do not write
or modify `.opju` bytes directly.

- [ ] **Step 4: Run high-level adapter and all origin-core tests**

Run:

```powershell
pytest tests/test_originpro_adapter.py tests/test_origin_contracts.py tests/test_origin_mapping.py tests/test_origin_service.py -q
```

Expected: PASS without `originpro` installed.

- [ ] **Step 5: Commit the high-level adapter**

```powershell
git add polynexus/origin/originpro_adapter.py tests/test_originpro_adapter.py
git commit -m "feat: add high-level Origin Python adapter"
```

## Task 7: Connect the service to the Chart Editor safely

**Files:**

- Create: `polynexus/gui/origin_export_worker.py`
- Create: `polynexus/gui/widgets/chart_editor_origin_mixin.py`
- Create: `tests/test_chart_editor_origin_export.py`
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/i18n.py`

- [ ] **Step 1: Write GUI action tests with an injected fake service**

Use the existing offscreen Qt fixture style. Assert that the Export Inspector
contains one Origin action, that a request contains the current normalized
figure document and output directory, and that success/warning/fallback results
reach the existing status label:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from polynexus.gui.widgets.chart_editor import ChartEditor
from polynexus.origin.contracts import ExportResult


def _app():
    return QApplication.instance() or QApplication([])


class FakeOriginService:
    def __init__(self, result):
        self.result = result
        self.requests = []

    def export(self, request):
        self.requests.append(request)
        return self.result


def test_chart_editor_origin_action_builds_request(monkeypatch, tmp_path):
    _app()
    editor = ChartEditor()
    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))
    service = FakeOriginService(ExportResult.success_result("package", tmp_path / "Origin_Export"))
    editor._origin_export_service = service

    request = editor._build_origin_export_request(tmp_path)

    assert request.output_root == tmp_path.resolve()
    assert request.document["mode"] == "object"
    editor._show_origin_export_result(service.result)
    assert editor._status_label.text()
    editor.deleteLater()
    _app().processEvents()
```

- [ ] **Step 2: Run GUI tests and confirm the action is missing**

Run:

```powershell
pytest tests/test_chart_editor_origin_export.py -q
```

Expected: FAIL because the mixin, button, and handler do not exist.

- [ ] **Step 3: Add the Origin export mixin and button**

Add `ChartEditorOriginMixin` to the `ChartEditor` base list. The mixin must
create `_btn_origin_export` in the existing Export Inspector form and connect
it to `_export_to_origin()`. It must use `QFileDialog.getExistingDirectory`
through `_choose_origin_output_root()` so tests can inject the directory.

Request construction must copy the current document and use the current source
path without exposing Qt objects to the service:

```python
def _build_origin_export_request(self, output_root):
    return ExportRequest(
        document=deepcopy(normalize_figure_document(self._figure_document)),
        figure_path=Path(self._source_path) if self._source_path else None,
        output_root=Path(output_root),
        mode="editable_origin" if self._generated_document_mode else "visual_fidelity",
        allow_open_origin=True,
    )


def _export_to_origin(self):
    output_root = self._choose_origin_output_root()
    if output_root:
        self._start_origin_export(self._build_origin_export_request(output_root))
```

Add a dedicated `QThread` worker so COM/Origin calls never run on the GUI
thread. The worker file must contain this exact signal/lifecycle boundary:

```python
class OriginExportWorker(QObject):
    finished = Signal(object)

    def __init__(self, service, request):
        super().__init__()
        self._service = service
        self._request = request

    @Slot()
    def run(self):
        try:
            result = self._service.export(self._request)
        except Exception as exc:
            result = ExportResult(
                status="failed",
                adapter_id="worker",
                message=str(exc),
                recoverable=True,
            )
        self.finished.emit(result)
```

`ChartEditorOriginMixin` must create a `QThread`, move one
`OriginExportWorker` into it, connect `thread.started` to `worker.run`, connect
`worker.finished` to the result handler and `thread.quit`, connect
`worker.finished` to `worker.deleteLater`, and connect `thread.finished` to
`thread.deleteLater`. Disable the Origin button while the thread is active and
clear the stored thread reference after it finishes. The service injection point
must be overridable in tests and default to `default_origin_export_service()`
only when the action is invoked.

- [ ] **Step 4: Add result messages and translations**

Add Chinese/English keys for:

```python
EDITOR_EXPORT_ORIGIN
EDITOR_EXPORT_ORIGIN_SELECT_DIR
EDITOR_EXPORT_ORIGIN_PYTHON_DONE
EDITOR_EXPORT_ORIGIN_COM_DONE
EDITOR_EXPORT_ORIGIN_PACKAGE_DONE
EDITOR_EXPORT_ORIGIN_UNAVAILABLE
EDITOR_EXPORT_ORIGIN_FAILED
EDITOR_EXPORT_ORIGIN_PARTIAL
```

Map result adapter IDs and statuses to these keys in the mixin. Warnings must
remain visible in the status label or log; a package fallback must explicitly
say that an Origin-compatible package was created rather than implying that an
`.opju` file was produced.

- [ ] **Step 5: Run GUI action tests and chart-editor regressions**

Run:

```powershell
pytest tests/test_chart_editor_origin_export.py tests/test_chart_editor_save_mixin.py tests/test_chart_editor.py -q
```

Expected: PASS. Existing native Save, Save As, Publish, and static-editor
behavior must remain unchanged.

- [ ] **Step 6: Commit GUI integration**

```powershell
git add polynexus/gui/origin_export_worker.py polynexus/gui/widgets/chart_editor_origin_mixin.py polynexus/gui/widgets/chart_editor.py polynexus/gui/i18n.py tests/test_chart_editor_origin_export.py
git commit -m "feat: add Chart Editor Origin export action"
```

## Task 8: Document optional setup and perform full verification

**Files:**

- Modify: `README.md`
- Modify: `pyproject.toml` only if the optional extra was not committed in Task 5.

- [ ] **Step 1: Add user-facing setup documentation**

Add a short section that states:

```text
OriginLab integration is optional and Windows-only.
The native editor works without Origin.
Install the optional COM bridge with `pip install -e ".[origin]"` when using
the COM compatibility path. The high-level Python path is selected only when
the installed Origin environment exposes `originpro`.
If no direct adapter is available, Export to Origin creates an
`Origin_Export` package containing data, metadata, and visual assets.
```

Document that editable Origin output is loss-aware and that SVG/PDF/PNG is the
visual-fidelity route for unsupported artists or annotations.

- [ ] **Step 2: Run all Origin tests**

Run:

```powershell
pytest tests/test_origin_contracts.py tests/test_origin_capability_probe.py tests/test_origin_registry.py tests/test_origin_mapping.py tests/test_origin_package_exporter.py tests/test_origin_service.py tests/test_origin_com_adapter.py tests/test_originpro_adapter.py tests/test_chart_editor_origin_export.py -q
```

Expected: PASS without Origin, `originpro`, or `pywin32` installed.

- [ ] **Step 3: Run the existing figure/editor regression set**

Run:

```powershell
pytest tests/test_figure_document.py tests/test_figure_data_writer.py tests/test_figure_export_service.py tests/test_chart_editor.py tests/test_chart_editor_save_mixin.py tests/test_main_window_figure_mixin.py -q
```

Expected: PASS with no changes to native figure persistence or export semantics.

- [ ] **Step 4: Run static checks and verify optional imports remain lazy**

Run:

```powershell
python -m compileall polynexus/origin polynexus/gui/widgets/chart_editor_origin_mixin.py
python -c "import polynexus; import polynexus.origin; print('standalone import ok')"
git diff --check
```

Expected: compilation succeeds, standalone imports succeed, and `git diff --check`
produces no output.

- [ ] **Step 5: Run manual capability checks where installations exist**

On a Windows machine without Origin, verify that the button creates the package
fallback. On a machine with a newer supported Origin environment, verify the
high-level adapter creates a worksheet, plot, and saved project. On a machine
with an older COM-compatible Origin environment, verify the COM adapter imports
the CSV, creates a basic graph, and saves through Origin. Record adapter ID,
Origin version, warnings, and generated artifact paths in the acceptance notes.

- [ ] **Step 6: Review invariants and commit the documentation**

Confirm the diff contains no base dependency on Origin, no direct `.opju` byte
generation, no arbitrary LabTalk input path, no GUI-thread COM call, and no
`if/elif` version dispatch in `service.py`. Then run:

```powershell
git add README.md pyproject.toml polynexus tests
git commit -m "docs: document optional Origin integration"
```

## Self-review checklist

- Spec coverage: contracts and Protocol are covered by Task 1; capability and
  registry behavior by Task 2; visual/data mapping and package fallback by Task
  3; chain semantics by Task 4; COM/LabTalk by Task 5; high-level Python
  integration by Task 6; GUI action and user-facing messages by Task 7; setup,
  regressions, and manual acceptance by Task 8.
- Placeholder scan: search this plan for common unfinished-work markers; the
  search must return no matches.
- Type consistency: all tasks use the same `ExportRequest`, `ExportResult`,
  `ExportStatus`, `CapabilityReport`, `OriginAdapter`, `OriginExportService`,
  and adapter IDs (`originpro`, `com_labtalk`, `package`).
- Scope consistency: no task adds Origin to base dependencies, edits `.opju`
  bytes directly, or makes the native editor depend on Origin.
