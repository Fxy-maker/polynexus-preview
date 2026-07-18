from polynexus.origin.com_labtalk_adapter import ComLabTalkAdapter
from polynexus.origin.com_labtalk_adapter import _default_com_available
from polynexus.origin.contracts import ExportRequest
from polynexus.origin.capability_probe import OriginCapability


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
    adapter = ComLabTalkAdapter(app_factory=lambda: app, com_available=lambda: True)

    result = adapter.export(request)

    assert result.success is True
    assert any("data.csv" in command for command in app.commands)
    assert any("plotxy" in command for command in app.commands)
    assert app.saved


def test_com_adapter_resolves_run_relative_source_from_source_root(tmp_path):
    run_root = tmp_path / "run-1"
    relative_source = "figures/fig-1/data/source.csv"
    source = run_root / relative_source
    source.parent.mkdir(parents=True)
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    app = FakeOriginApplication()
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

    result = ComLabTalkAdapter(
        app_factory=lambda: app,
        com_available=lambda: True,
    ).export(request)

    assert result.success is True
    assert any(str(source) in command for command in app.commands)


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


def test_com_adapter_is_unavailable_for_visual_only_mode(tmp_path):
    adapter = ComLabTalkAdapter(app_factory=lambda: FakeOriginApplication(), com_available=lambda: True)

    result = adapter.export(
        ExportRequest(document={}, output_root=tmp_path, mode="visual_fidelity")
    )

    assert result.status == "unavailable"


def test_default_com_capability_requires_a_registered_origin_server(monkeypatch):
    monkeypatch.setattr(
        "polynexus.origin.com_labtalk_adapter.OriginCapabilityProbe.probe",
        lambda _self: OriginCapability(
            installed=True,
            originpro_available=False,
            com_available=False,
            reason="COM server unavailable",
        ),
    )

    assert _default_com_available() is False


def test_com_object_without_labtalk_is_unavailable_before_external_state(tmp_path):
    class IncompleteOriginApplication:
        pass

    adapter = ComLabTalkAdapter(
        app_factory=IncompleteOriginApplication,
        com_available=lambda: True,
    )

    result = adapter.export(
        ExportRequest(document={}, output_root=tmp_path, mode="editable_origin")
    )

    assert result.status == "unavailable"
