from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from .i18n import tr


class MainWindowGuidancePanelsMixin:
    def _build_context_suggestion_panel(self, slot: str):

        panel = QFrame()
        panel.setObjectName("context_suggestion_box")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 8, 12, 8)
        panel_layout.setSpacing(4)

        title = QLabel(tr("CONTEXT_HINT_TITLE"))
        title.setObjectName("context_suggestion_title")
        panel_layout.addWidget(title)

        detail = QLabel(tr("CONTEXT_HINT_DEFAULT_DETAIL"))
        detail.setObjectName("context_suggestion_detail")
        detail.setWordWrap(True)
        panel_layout.addWidget(detail)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 2, 0, 0)
        button_row.setSpacing(8)
        button_row.addStretch(1)

        buttons = []
        for _ in range(2):
            btn = QPushButton()
            btn.setObjectName("secondary_btn")
            btn.setVisible(False)
            btn.clicked.connect(self._invoke_context_suggestion_action)
            buttons.append(btn)
            button_row.addWidget(btn)

        panel_layout.addLayout(button_row)
        self._context_suggestion_panels[slot] = {
            "widget": panel,
            "title": title,
            "detail": detail,
            "buttons": buttons,
        }
        return panel

    def _build_work_memory_panel(self):

        panel = QFrame()
        panel.setObjectName("work_memory_box")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 8, 12, 8)
        panel_layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QLabel(tr("WORK_MEMORY_TITLE"))
        title.setObjectName("work_memory_title")
        header.addWidget(title, 1)

        refresh_btn = QPushButton(tr("WORK_MEMORY_REFRESH"))
        refresh_btn.setObjectName("secondary_btn")
        refresh_btn.clicked.connect(self._update_work_memory_panel)
        header.addWidget(refresh_btn)
        panel_layout.addLayout(header)

        detail = QLabel(tr("WORK_MEMORY_DEFAULT_DETAIL"))
        detail.setObjectName("work_memory_detail")
        detail.setWordWrap(True)
        panel_layout.addWidget(detail)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        buttons = []
        for _ in range(6):
            btn = QPushButton()
            btn.setObjectName("secondary_btn")
            btn.setVisible(False)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(self._invoke_work_memory_action)
            buttons.append(btn)
        for idx, btn in enumerate(buttons):
            grid.addWidget(btn, idx // 3, idx % 3)
        panel_layout.addLayout(grid)

        self._work_memory_panels = {
            "widget": panel,
            "title": title,
            "detail": detail,
            "buttons": buttons,
            "refresh": refresh_btn,
        }
        return panel

    def _invoke_context_suggestion_action(self):
        button = self.sender()
        if button is None:
            return
        action_key = str(button.property("context_action_key") or "").strip()
        action = self._context_suggestion_action_map.get(action_key)
        if callable(action):
            action()

    def _invoke_work_memory_action(self):

        button = self.sender()
        if button is None:
            return
        action_key = str(button.property("work_memory_action_key") or "").strip()
        action = self._work_memory_action_map.get(action_key)
        if callable(action):
            action()
