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
