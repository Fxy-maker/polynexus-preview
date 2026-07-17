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


def test_preferred_adapter_filters_the_chain(tmp_path):
    first = FakeAdapter("first", 100, True, ExportResult.success_result("first"))
    preferred = FakeAdapter("preferred", 10, True, ExportResult.success_result("preferred"))

    result = OriginExportService([first, preferred]).export(
        ExportRequest(
            document={},
            output_root=tmp_path,
            preferred_adapter="preferred",
        )
    )

    assert result.adapter_id == "preferred"
    assert first.calls == 0


def test_can_handle_exception_is_treated_as_unavailable(tmp_path):
    broken = FakeAdapter("broken", 100, True, ExportResult.success_result("broken"))
    broken.can_handle = lambda request: (_ for _ in ()).throw(RuntimeError("probe failed"))
    fallback = FakeAdapter("package", 10, True, ExportResult.success_result("package"))

    result = OriginExportService([broken, fallback]).export(
        ExportRequest(document={}, output_root=tmp_path)
    )

    assert result.adapter_id == "package"
