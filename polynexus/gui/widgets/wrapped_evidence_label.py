from __future__ import annotations

from PySide6.QtWidgets import QLabel


class WrappedEvidenceLabel(QLabel):
    """Keep evidence text exact while allowing long tokens to wrap visually."""

    def __init__(self, *args, **kwargs):
        self._source_text = ""
        super().__init__(*args, **kwargs)

    def setText(self, text):
        self._source_text = "" if text is None else str(text)
        super().setText("\u200b".join(self._source_text))

    def text(self):
        return self._source_text
