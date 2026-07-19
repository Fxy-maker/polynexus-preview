"""Focused regression tests for the GUI startup boundary."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Import the scientific package before Qt in this test process.  This matches
# the supported import order and avoids the known Shiboken import hook issue
# while the application bootstrap is being migrated.
import polynexus.core  # noqa: F401,E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from polynexus.gui.main_window import MainWindow  # noqa: E402
from polynexus.gui.i18n import tr  # noqa: E402


@pytest.fixture
def qt_app():
    return QApplication.instance() or QApplication([])


def test_app_module_does_not_eagerly_import_main_window():
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import polynexus.app; "
                "assert 'polynexus.gui.main_window' not in sys.modules"
            ),
        ],
        cwd=os.getcwd(),
        capture_output=True,
        text=True,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_app_startup_probe_constructs_and_closes_the_deferred_window(tmp_path):
    env = {
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",
        "POLYNEXUS_RUNTIME_ROOT": str(tmp_path / "runtime"),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from polynexus.app import main; raise SystemExit(main(startup_probe=True))",
        ],
        cwd=os.getcwd(),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_deferred_window_is_interactive_before_optional_ui_finishes(qt_app):
    window = MainWindow(defer_optional_ui=True)
    window.show()
    qt_app.processEvents()

    assert window.windowTitle()
    assert window._path_input.isEnabled()
    assert window._btn_run.isVisible()
    assert window._tabs.count() >= 1
    assert window._startup_deferred is True
    assert window._deferred_startup_finished is False

    window.finish_deferred_startup()
    first_tab_count = window._tabs.count()
    first_chart_gallery = window._chart_gallery

    window.finish_deferred_startup()

    assert window._deferred_startup_finished is True
    assert window._tabs.count() == first_tab_count
    assert window._chart_gallery is first_chart_gallery
    assert window._gallery_title_label.text() == tr("CHART_GALLERY_TITLE")
    assert window._gallery_summary_label.text()
    assert window._btn_legacy_recovery.isHidden() is False

    window.close()
