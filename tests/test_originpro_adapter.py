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


def test_originpro_adapter_is_unavailable_for_visual_only_mode(tmp_path):
    adapter = OriginProAdapter(originpro_factory=FakeOriginPro)

    result = adapter.export(
        ExportRequest(document={}, output_root=tmp_path, mode="visual_fidelity")
    )

    assert result.status == "unavailable"
