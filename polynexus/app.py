"""PolyNexus GUI entry point."""

from __future__ import annotations

import json
from typing import Any


def _prepare_gui_imports() -> None:
    """Load the scientific registry before Qt installs its import hook."""
    import polynexus.core  # noqa: F401


def main(
    argv=None,
    *,
    startup_probe: bool = False,
    automation_port: int | None = None,
    automation_secret: str | None = None,
):
    _prepare_gui_imports()

    import sys
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication
    from polynexus.gui.main_window import MainWindow
    from polynexus.utils.logger import PolyNexusLogger

    app_args = list(sys.argv if argv is None else argv)
    app = QApplication.instance() or QApplication(app_args)
    app.setApplicationName("PolyNexus")
    app.setOrganizationName("PolyNexus")
    app.setFont(QFont("Microsoft YaHei UI", 10))
    PolyNexusLogger.get()

    window = MainWindow(defer_optional_ui=True)
    window.show()
    window.schedule_deferred_startup()
    if hasattr(window, "setup_convergence_action"):
        window.setup_convergence_action()

    bridge: Any | None = None
    if automation_port is not None:
        if not automation_secret:
            raise ValueError("automation_secret is required when automation_port is set")
        from polynexus.gui.automation_bridge import GuiAutomationBridge

        bridge = GuiAutomationBridge(window, secret=automation_secret)
        ready = bridge.start(automation_port)
        print(json.dumps({"automation_ready": True, **ready}), flush=True)

    if startup_probe:
        app.processEvents()
        window.close()
        app.processEvents()
        if bridge is not None:
            bridge.close()
        return 0

    try:
        return int(app.exec())
    finally:
        if bridge is not None:
            bridge.close()


if __name__ == "__main__":
    raise SystemExit(main())
