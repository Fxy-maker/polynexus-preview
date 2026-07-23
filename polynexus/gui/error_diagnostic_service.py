"""Small, Qt-independent error payloads for recoverable GUI failures."""

from __future__ import annotations

from dataclasses import dataclass


def _clean(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class ErrorDiagnostic:
    """User-facing error details with a clipboard-safe representation."""

    title: str
    copy_text: str
    recovery: str


def build_error_diagnostic(
    *,
    operation: object,
    message: object,
    detail: object = "",
    recovery: object = "",
) -> ErrorDiagnostic:
    """Build a stable diagnostic payload without leaking empty placeholder lines."""
    operation_text = _clean(operation) or "operation"
    message_text = _clean(message) or "Unknown error"
    detail_text = _clean(detail)
    recovery_text = _clean(recovery)
    lines = [f"{operation_text}: {message_text}"]
    if detail_text:
        lines.append(detail_text)
    if recovery_text:
        lines.append(f"Recovery: {recovery_text}")
    return ErrorDiagnostic(
        title=message_text,
        copy_text="\n".join(lines),
        recovery=recovery_text,
    )


__all__ = ["ErrorDiagnostic", "build_error_diagnostic"]
