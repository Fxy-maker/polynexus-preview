import pytest

from polynexus.origin.contracts import ExportRequest
from polynexus.origin import originpro_adapter
from polynexus.origin.originpro_adapter import (
    OriginProAdapter,
    _OriginProFacade,
)
from polynexus.origin.originpro_adapter import _default_available
from polynexus.origin.capability_probe import OriginCapability


class FakeOriginPro:
    def __init__(self):
        self.events = []

    def new_book(self, kind="w"):
        self.events.append(("new_book", kind))
        return self

    def show(self):
        self.events.append(("show",))

    def activate(self):
        self.events.append(("activate",))

    def add_sheet(self, name):
        self.events.append(("add_sheet", name))
        return self

    def from_csv(self, path):
        self.events.append(("from_csv", str(path)))

    def add_plot(self, x_column, y_column, style, *, data_ref="", name=""):
        self.events.append(("add_plot", x_column, y_column, style, data_ref, name))

    def configure_axes(self, *, x_scale, y_scale):
        self.events.append(("configure_axes", x_scale, y_scale))

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
            "objects": [
                {
                    "type": "plot_series",
                    "data_ref": "data-1",
                    "x_column": "x",
                    "y_column": "y",
                }
            ],
        },
        output_root=tmp_path / "out",
        mode="editable_origin",
    )

    result = OriginProAdapter(originpro_factory=lambda: facade).export(request)

    assert result.success is True
    assert ("from_csv", str(source)) in facade.events
    assert any(event[0] == "add_plot" for event in facade.events)
    assert ("show",) in facade.events
    assert ("activate",) in facade.events
    assert any(event[0] == "save" for event in facade.events)


def test_originpro_adapter_binds_each_plot_to_its_source_and_name(tmp_path):
    facade = FakeOriginPro()
    source_a = tmp_path / "data-a.csv"
    source_b = tmp_path / "data-b.csv"
    source_a.write_text("x,y\n1,2\n", encoding="utf-8")
    source_b.write_text("x,y\n1,20\n", encoding="utf-8")
    request = ExportRequest(
        document={
            "figure_id": "fig-multi",
            "data_sources": [
                {"id": "source-a", "path": str(source_a)},
                {"id": "source-b", "path": str(source_b)},
            ],
            "objects": [
                {
                    "id": "plot-a",
                    "type": "plot_series",
                    "name": "Curve A",
                    "data_ref": "source-a",
                    "x_column": "x",
                    "y_column": "y",
                    "style": {"color": "#336699", "line_width": 1.5},
                },
                {
                    "id": "plot-b",
                    "type": "plot_series",
                    "name": "Curve B",
                    "data_ref": "source-b",
                    "x_column": "x",
                    "y_column": "y",
                    "style": {"color": "#E69F00", "line_width": 2.0},
                },
            ],
        },
        output_root=tmp_path / "out",
        mode="editable_origin",
    )

    result = OriginProAdapter(originpro_factory=lambda: facade).export(request)

    assert result.success is True
    assert [event for event in facade.events if event[0] == "add_plot"] == [
        (
            "add_plot",
            "x",
            "y",
            {"color": "#336699", "line_width": 1.5},
            "source-a",
            "Curve A",
        ),
        (
            "add_plot",
            "x",
            "y",
            {"color": "#E69F00", "line_width": 2.0},
            "source-b",
            "Curve B",
        ),
    ]


def test_originpro_facade_uses_source_sheet_and_applies_plot_style():
    class FakeSheet:
        def __init__(self, name):
            self.name = name
            self.labels = []

        def set_label(self, column, value):
            self.labels.append((column, value))

    class FakeFrame:
        def __init__(self):
            self.columns = type(
                "Columns",
                (),
                {
                    "__contains__": lambda _self, name: name in {"x", "y"},
                    "get_loc": lambda _self, name: {"x": 0, "y": 1}[name],
                },
            )()

    class FakePlot:
        def __init__(self):
            self.color = None
            self.commands = []

        def set_cmd(self, *args):
            self.commands.append(args)

    class FakeLayer:
        def __init__(self):
            self.events = []
            self.plot = FakePlot()

        def add_plot(self, sheet, *, colx, coly):
            self.events.append((sheet.name, colx, coly))
            return self.plot

        def rescale(self):
            return None

    class FakeGraph:
        def __init__(self, layer):
            self.layer = layer

        def __getitem__(self, index):
            assert index == 0
            return self.layer

    source_a = FakeSheet("source-a")
    source_b = FakeSheet("source-b")
    layer = FakeLayer()
    facade = _OriginProFacade(object())
    facade._sheets = {"source-a": source_a, "source-b": source_b}
    facade._dataframes = {"source-a": FakeFrame(), "source-b": FakeFrame()}
    facade._graphs = [FakeGraph(layer)]

    facade.add_plot(
        "x",
        "y",
        {"color": "#336699", "line_width": 1.5},
        data_ref="source-b",
        name="Curve B",
    )

    assert layer.events == [("source-b", 0, 1)]
    assert source_b.labels == [("y", "Curve B")]
    assert layer.plot.color == "#336699"
    assert layer.plot.commands == [("-w 750",)]


def test_originpro_plot_style_uses_balanced_minimum_display_width():
    class FakePlot:
        def __init__(self):
            self.commands = []

        def set_cmd(self, command):
            self.commands.append(command)

    plot = FakePlot()

    originpro_adapter._apply_plot_style(plot, {"line_width": 0.8})

    assert plot.commands == ["-w 600"]


def test_originpro_facade_rejects_unknown_source_reference():
    facade = _OriginProFacade(object())
    facade._sheets = {"source-a": object()}
    facade._dataframes = {"source-a": object()}

    with pytest.raises(KeyError, match="not loaded: source-missing"):
        facade.add_plot("x", "y", {}, data_ref="source-missing")


def test_originpro_facade_configures_graph_title_labels_and_scales():
    class FakeAxis:
        def __init__(self):
            self.title = ""

    class FakeLayer:
        def __init__(self):
            self.xscale = ""
            self.yscale = ""
            self.axes = {"x": FakeAxis(), "y": FakeAxis()}
            self.rescaled = False

        def axis(self, name):
            return self.axes[name]

        def rescale(self):
            self.rescaled = True

    class FakeGraph:
        def __init__(self, layer):
            self.layer = layer
            self.lname = ""

        def __getitem__(self, index):
            assert index == 0
            return self.layer

    layer = FakeLayer()
    graph = FakeGraph(layer)
    facade = _OriginProFacade(object())
    facade._graphs = [graph]

    facade.configure_figure(
        title="Full SAXS series waterfall",
        xlabel="$q$ (nm$^{-1}$)",
        ylabel="$I$ (a.u.)",
        x_scale="linear",
        y_scale="log",
    )

    assert graph.lname == "Full SAXS series waterfall"
    assert layer.axes["x"].title == "q (nm⁻¹)"
    assert layer.axes["y"].title == "I (a.u.)"
    assert layer.xscale == "linear"
    assert layer.yscale == "log10"
    assert layer.rescaled is True


def test_originpro_facade_applies_balanced_axis_frame_thickness():
    class FakeLayer:
        def __init__(self):
            self.properties = []

        def set_float(self, prop, value):
            self.properties.append((prop, value))

        def rescale(self):
            return None

    class FakeGraph:
        def __init__(self, layer):
            self.layer = layer

        def __getitem__(self, index):
            assert index == 0
            return self.layer

    layer = FakeLayer()
    facade = _OriginProFacade(object())
    facade._graphs = [FakeGraph(layer)]

    facade.configure_figure(x_scale="linear", y_scale="linear")

    assert layer.properties == [
        ("x.thickness", 0.8),
        ("x2.thickness", 0.8),
        ("y.thickness", 0.8),
        ("y2.thickness", 0.8),
    ]


def test_origin_display_label_converts_mathtext_to_origin_safe_unicode():
    assert originpro_adapter._origin_display_label("$I$ (a.u.)") == "I (a.u.)"
    assert originpro_adapter._origin_display_label("$q$ (nm$^{-1}$)") == "q (nm⁻¹)"
    assert originpro_adapter._origin_display_label(r"$\mu$m") == "μm"


def test_originpro_adapter_applies_source_axis_scales(tmp_path):
    facade = FakeOriginPro()
    source = tmp_path / "data.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    request = ExportRequest(
        document={
            "figure_id": "fig-log",
            "layout": {
                "panels": [
                    {
                        "x_axis": {"scale": "linear"},
                        "y_axis": {"scale": "log"},
                    }
                ]
            },
            "data_sources": [{"id": "data-1", "path": str(source)}],
            "objects": [
                {
                    "type": "plot_series",
                    "data_ref": "data-1",
                    "x_column": "x",
                    "y_column": "y",
                }
            ],
        },
        output_root=tmp_path / "out",
        mode="editable_origin",
    )

    result = OriginProAdapter(originpro_factory=lambda: facade).export(request)

    assert result.success is True
    assert ("configure_axes", "linear", "log") in facade.events


def test_originpro_facade_rescales_graph_after_adding_plot():
    class FakeLayer:
        def __init__(self):
            self.events = []

        def add_plot(self, sheet, *, colx, coly):
            self.events.append(("add_plot", sheet, colx, coly))

        def rescale(self):
            self.events.append(("rescale",))

    class FakeGraph:
        def __init__(self, layer):
            self.layer = layer

        def __getitem__(self, index):
            assert index == 0
            return self.layer

    class FakeModule:
        def __init__(self, layer):
            self.layer = layer

        def new_graph(self, *, template):
            assert template == "Line"
            return FakeGraph(self.layer)

    layer = FakeLayer()
    facade = _OriginProFacade(FakeModule(layer))
    facade._sheet = object()
    columns = type(
        "Columns",
        (),
        {
            "__contains__": lambda _self, name: name in {"x", "y"},
            "get_loc": lambda _self, name: {"x": 0, "y": 1}[name],
        },
    )()
    facade._dataframes = [type("Frame", (), {"columns": columns})()]

    facade.add_plot("x", "y", {})

    assert [event[0] for event in layer.events] == ["add_plot", "rescale"]


def test_originpro_facade_reuses_one_graph_for_multiple_plots():
    class FakeLayer:
        def add_plot(self, sheet, *, colx, coly):
            return None

        def rescale(self):
            return None

    class FakeGraph:
        def __init__(self, layer):
            self.layer = layer

        def __getitem__(self, index):
            assert index == 0
            return self.layer

    class FakeModule:
        def __init__(self):
            self.graph_count = 0
            self.layer = FakeLayer()

        def new_graph(self, *, template):
            assert template == "Line"
            self.graph_count += 1
            return FakeGraph(self.layer)

    columns = type(
        "Columns",
        (),
        {
            "__contains__": lambda _self, name: name in {"x", "y"},
            "get_loc": lambda _self, name: {"x": 0, "y": 1}[name],
        },
    )()
    module = FakeModule()
    facade = _OriginProFacade(module)
    facade._sheet = object()
    facade._dataframes = [type("Frame", (), {"columns": columns})()]

    facade.add_plot("x", "y", {})
    facade.add_plot("x", "y", {})

    assert module.graph_count == 1


def test_originpro_facade_maps_log_axis_to_origin_scale():
    class FakeLayer:
        def __init__(self):
            self.xscale = None
            self.yscale = None
            self.rescaled = False

        def rescale(self):
            self.rescaled = True

    class FakeGraph:
        def __init__(self, layer):
            self.layer = layer

        def __getitem__(self, index):
            assert index == 0
            return self.layer

    layer = FakeLayer()
    facade = _OriginProFacade(object())
    facade._graphs = [FakeGraph(layer)]

    facade.configure_axes(x_scale="linear", y_scale="log")

    assert layer.xscale == "linear"
    assert layer.yscale == "log10"
    assert layer.rescaled is True


def test_originpro_adapter_resolves_run_relative_source_from_source_root(tmp_path):
    run_root = tmp_path / "run-1"
    relative_source = "figures/fig-1/data/source.csv"
    source = run_root / relative_source
    source.parent.mkdir(parents=True)
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    facade = FakeOriginPro()
    request = ExportRequest(
        document={
            "figure_id": "fig-1",
            "data_sources": [
                {"id": "data-1", "path": relative_source, "path_kind": "run_relative"}
            ],
            "objects": [],
        },
        figure_path=run_root / "figures/fig-1/figure.svg",
        source_root=run_root,
        output_root=tmp_path / "out",
        mode="editable_origin",
    )

    result = OriginProAdapter(originpro_factory=lambda: facade).export(request)

    assert result.success is True
    assert ("from_csv", str(source)) in facade.events


def test_originpro_adapter_is_unavailable_for_visual_only_mode(tmp_path):
    adapter = OriginProAdapter(originpro_factory=FakeOriginPro)

    result = adapter.export(
        ExportRequest(document={}, output_root=tmp_path, mode="visual_fidelity")
    )

    assert result.status == "unavailable"


def test_default_originpro_capability_requires_origin_installation(monkeypatch):
    monkeypatch.setattr(
        "polynexus.origin.originpro_adapter.OriginCapabilityProbe.probe",
        lambda _self: OriginCapability(
            installed=False,
            originpro_available=True,
            com_available=False,
            reason="Origin installation was not detected",
        ),
    )

    assert _default_available() is False


def test_originpro_factory_failure_before_book_creation_is_unavailable(tmp_path):
    class BrokenOriginPro:
        def new_book(self, kind):
            raise RuntimeError("Origin session unavailable")

    adapter = OriginProAdapter(
        originpro_factory=BrokenOriginPro,
    )

    result = adapter.export(
        ExportRequest(document={}, output_root=tmp_path, mode="editable_origin")
    )

    assert result.status == "unavailable"
