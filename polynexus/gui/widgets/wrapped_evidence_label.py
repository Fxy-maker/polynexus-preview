from __future__ import annotations

from PySide6.QtWidgets import QLabel, QSizePolicy


class WrappedEvidenceLabel(QLabel):
    """Keep evidence text exact while allowing long tokens to wrap visually."""

    def __init__(self, *args, **kwargs):
        self._source_text = ""
        super().__init__(*args, **kwargs)

    def setText(self, text):
        self._source_text = "" if text is None else str(text)
        super().setText("\u200b".join(self._source_text))

    def setSizePolicy(self, *args):
        """Keep Qt's height-for-width contract when callers shrink the label."""
        if len(args) == 1 and isinstance(args[0], QSizePolicy):
            policy = args[0]
        elif len(args) == 2:
            policy = QSizePolicy(args[0], args[1])
        else:
            super().setSizePolicy(*args)
            return
        policy.setHeightForWidth(True)
        super().setSizePolicy(policy)

    def text(self):
        return self._source_text
