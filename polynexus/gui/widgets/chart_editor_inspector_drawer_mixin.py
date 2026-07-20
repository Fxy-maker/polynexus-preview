from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget


class ChartEditorInspectorDrawerMixin:
    """Own the ChartEditor Inspector drawer without changing editor state."""

    _inspector_minimum_width = 280

    def _build_inspector_drawer(self, inspector_tabs):
        panel = QWidget()
        panel.setObjectName("editor_inspector_panel")
        panel.setMinimumWidth(self._inspector_minimum_width)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(inspector_tabs)
        self._inspector_panel = panel
        self._inspector_last_width = 320
        self._inspector_closed_manually = False
        return panel

    def _set_inspector_collapsed(self, collapsed: bool, *, manual: bool = False) -> None:
        splitter = getattr(self, "_editor_splitter", None)
        panel = getattr(self, "_inspector_panel", None)
        if splitter is None or panel is None:
            return
        if manual:
            self._inspector_closed_manually = bool(collapsed)
        if collapsed:
            self._inspector_last_width = max(
                self._inspector_minimum_width,
                int(splitter.sizes()[1]),
            )
            panel.hide()
            splitter.setSizes([max(1, splitter.width()), 0])
            self._sync_inspector_toggle()
            return
        panel.show()
        total_width = max(1, sum(splitter.sizes()))
        inspector_width = min(
            max(self._inspector_minimum_width, int(self._inspector_last_width)),
            max(self._inspector_minimum_width, total_width - 1),
        )
        splitter.setSizes([max(1, total_width - inspector_width), inspector_width])
        self._sync_inspector_toggle()

    def _inspector_is_collapsed(self) -> bool:
        panel = getattr(self, "_inspector_panel", None)
        return bool(panel is not None and panel.isHidden())

    def _reveal_inspector_for_selection(self) -> None:
        """Keep the Inspector visibility under explicit user control."""

    def _toggle_inspector_drawer(self) -> None:
        self._set_inspector_collapsed(
            not self._inspector_is_collapsed(),
            manual=True,
        )

    def _sync_inspector_toggle(self) -> None:
        button = getattr(self, "_btn_header_inspector", None)
        if button is None:
            return
        collapsed = self._inspector_is_collapsed()
        button.blockSignals(True)
        button.setChecked(not collapsed)
        button.blockSignals(False)
