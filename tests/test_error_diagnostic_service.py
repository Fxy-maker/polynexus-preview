from polynexus.gui.error_diagnostic_service import build_error_diagnostic


def test_diagnostic_payload_contains_operation_message_and_recovery():
    payload = build_error_diagnostic(
        operation="analysis",
        message="bad input",
        detail="traceback line",
        recovery="retry",
    )

    assert payload.copy_text.startswith("analysis: bad input")
    assert "traceback line" in payload.copy_text
    assert payload.recovery == "retry"


def test_diagnostic_payload_normalizes_empty_fields():
    payload = build_error_diagnostic(
        operation="",
        message=None,
        detail="",
        recovery=None,
    )

    assert payload.title == "Unknown error"
    assert payload.copy_text == "operation: Unknown error"
    assert payload.recovery == ""
