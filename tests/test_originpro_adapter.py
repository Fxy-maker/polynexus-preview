from polynexus.origin.contracts import ExportRequest
from polynexus.origin.originpro_adapter import OriginProAdapter
from polynexus.origin.originpro_adapter import _default_available
from polynexus.origin.capability_probe import OriginCapability


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
    assert any(event[0] == "save" for event in facade.events)


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
