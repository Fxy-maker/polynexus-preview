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
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["adapter_id"] == "package"
    assert (root / "import.ogs").exists()


def test_package_exporter_writes_inline_source_values(tmp_path):
    request = ExportRequest(
        document={
            "data_sources": [
                {
                    "id": "inline",
                    "columns": [{"name": "x"}, {"name": "y"}],
                    "values": {"x": [1, 2], "y": [3, 4]},
                }
            ]
        },
        output_root=tmp_path / "out",
        mode="package",
    )

    result = PackageExporter().export(request)
    data = (tmp_path / "out" / "Origin_Export" / "data" / "inline.csv").read_text(
        encoding="utf-8"
    )

    assert result.success is True
    assert data.splitlines() == ["x,y", "1,3", "2,4"]


def test_package_exporter_reports_missing_source_without_corrupting_output(tmp_path):
    request = ExportRequest(
        document={"data_sources": [{"id": "bad", "path": "../../outside.csv"}]},
        output_root=tmp_path / "out",
        mode="package",
    )

    result = PackageExporter().export(request)

    assert result.status in {"failed", "partial"}
    assert not list((tmp_path / "out").glob(".origin-export-*"))


def test_repeated_package_export_uses_a_new_target(tmp_path):
    request = ExportRequest(document={}, output_root=tmp_path / "out", mode="package")

    first = PackageExporter().export(request)
    second = PackageExporter().export(request)

    assert first.success is True
    assert second.success is True
    assert first.artifacts[0] != second.artifacts[0]
