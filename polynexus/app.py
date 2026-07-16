"""PolyNexus GUI entry point."""


def _prepare_gui_imports() -> None:
    """Load the scientific registry before Qt installs its import hook."""
    import polynexus.core  # noqa: F401


def main(argv=None, *, startup_probe: bool = False):
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

    if startup_probe:
        app.processEvents()
        window.close()
        app.processEvents()
        return 0

    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
