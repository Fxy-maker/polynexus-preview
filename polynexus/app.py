"""PolyNexus GUI entry point."""

import sys
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from polynexus.gui.main_window import MainWindow
from polynexus.utils.logger import PolyNexusLogger


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PolyNexus")
    app.setOrganizationName("PolyNexus")
    app.setFont(QFont("Microsoft YaHei UI", 10))
    PolyNexusLogger.get()

    window = MainWindow()
    window.show()
    if hasattr(window, "setup_convergence_action"):
        window.setup_convergence_action()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
