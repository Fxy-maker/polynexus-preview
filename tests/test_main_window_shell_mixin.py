from __future__ import annotations

import importlib
import importlib.util
from types import SimpleNamespace

from polynexus.gui.main_window import MainWindow


def test_main_window_reuses_shell_helpers_from_shell_mixin() -> None:
    spec = importlib.util.find_spec("polynexus.gui.main_window_shell_mixin")
    assert spec is not None

    module = importlib.import_module("polynexus.gui.main_window_shell_mixin")
    mixin = module.MainWindowShellMixin

    assert MainWindow._build_menubar is mixin._build_menubar
    assert MainWindow._build_statusbar is mixin._build_statusbar
    assert MainWindow._toggle_theme is mixin._toggle_theme
    assert MainWindow._toggle_sidebar is mixin._toggle_sidebar
    assert MainWindow._on_settings is mixin._on_settings
    assert MainWindow._on_help is mixin._on_help
    assert MainWindow._on_quit is mixin._on_quit


def test_main_window_shell_mixin_toggle_theme_updates_button_and_status() -> None:
    module = importlib.import_module("polynexus.gui.main_window_shell_mixin")

    class _ThemeEngine:
        def __init__(self):
            self.is_dark = False

        def toggle(self):
            self.is_dark = not self.is_dark

    class _Button:
        def __init__(self):
            self.text = ""

        def setText(self, text):
            self.text = text

    class _StatusBar:
        def __init__(self):
            self.messages = []

        def showMessage(self, message):
            self.messages.append(message)

    class _Window(module.MainWindowShellMixin):
        def __init__(self):
            self._theme_engine = _ThemeEngine()
            self._btn_theme = _Button()
            self._statusbar = _StatusBar()
            self.applied = 0
            self.logs = []

        def _apply_theme(self):
            self.applied += 1

        def log(self, message):
            self.logs.append(message)

    window = _Window()

    window._toggle_theme()

    assert window._theme_engine.is_dark is True
    assert window.applied == 1
    assert window._btn_theme.text == "\u263e"
    assert len(window.logs) == 1
    assert window.logs[0]
    assert len(window._statusbar.messages) == 1
    assert window._statusbar.messages[0]


def test_main_window_shell_mixin_build_statusbar_sets_indicator_and_ready_message() -> None:
    module = importlib.import_module("polynexus.gui.main_window_shell_mixin")

    class _StatusBar:
        def __init__(self):
            self.object_name = ""
            self.widgets = []
            self.messages = []

        def setObjectName(self, name):
            self.object_name = name

        def addWidget(self, widget, stretch=0):
            self.widgets.append((widget, stretch))

        def showMessage(self, message):
            self.messages.append(message)

    class _Label:
        def __init__(self, text):
            self.text = text
            self.object_name = ""

        def setObjectName(self, name):
            self.object_name = name

    class _Widget:
        def __init__(self):
            self.size_policy = None

        def setSizePolicy(self, horizontal, vertical):
            self.size_policy = (horizontal, vertical)

    class _Window(module.MainWindowShellMixin):
        def __init__(self):
            self._fake_statusbar = _StatusBar()

        @staticmethod
        def _main_window_module():
            return SimpleNamespace(
                QLabel=_Label,
                QWidget=_Widget,
                QSizePolicy=SimpleNamespace(Expanding="expanding", Preferred="preferred"),
            )

        def statusBar(self):
            return self._fake_statusbar

    window = _Window()

    window._build_statusbar()

    assert window._statusbar is window._fake_statusbar
    assert window._statusbar.object_name == "statusbar"
    assert window._status_tech_label.text.strip()
    assert window._status_tech_label.object_name == "status_tech"
    assert len(window._statusbar.widgets) == 2
    spacer = window._statusbar.widgets[1][0]
    assert spacer.size_policy == ("expanding", "preferred")
    assert len(window._statusbar.messages) == 1
    assert window._statusbar.messages[0]


def test_main_window_shell_mixin_build_menubar_wires_core_actions() -> None:
    module = importlib.import_module("polynexus.gui.main_window_shell_mixin")

    class _Signal:
        def __init__(self):
            self.callbacks = []

        def connect(self, callback):
            self.callbacks.append(callback)

    class _Action:
        def __init__(self, text, parent=None):
            self.text = text
            self.parent = parent
            self.object_name = ""
            self.triggered = _Signal()

        def setObjectName(self, name):
            self.object_name = name

    class _Menu:
        def __init__(self, title):
            self.title = title
            self.actions = []
            self.separator_count = 0

        def addAction(self, action_or_text):
            action = action_or_text if isinstance(action_or_text, _Action) else _Action(action_or_text)
            self.actions.append(action)
            return action

        def addSeparator(self):
            self.separator_count += 1

    class _MenuBar:
        def __init__(self):
            self.menus = []

        def addMenu(self, title):
            menu = _Menu(title)
            self.menus.append(menu)
            return menu

    class _Window(module.MainWindowShellMixin):
        def __init__(self):
            self._menubar = _MenuBar()

        @staticmethod
        def _main_window_module():
            return SimpleNamespace(QAction=_Action)

        def menuBar(self):
            return self._menubar

        def close(self):
            pass

        def _browse_file(self):
            pass

        def _export_results(self):
            pass

        def _on_settings(self):
            pass

        def _toggle_sidebar(self):
            pass

        def _toggle_theme(self):
            pass

        def _toggle_language(self):
            pass

        def _open_convergence_viewer(self):
            pass

        def _on_help(self):
            pass

    window = _Window()

    window._build_menubar()

    assert [menu.title for menu in window._menubar.menus] == [
        module.tr("MENU_FILE"),
        module.tr("MENU_EDIT"),
        module.tr("MENU_VIEW"),
        module.tr("MENU_HELP"),
    ]
    assert window._menu_file.separator_count == 1
    assert window._act_open.triggered.callbacks == [window._browse_file]
    assert window._act_export.triggered.callbacks == [window._export_results]
    assert window._act_quit.triggered.callbacks == [window.close]
    assert window._act_settings.triggered.callbacks == [window._on_settings]
    assert window._act_toggle_sidebar.triggered.callbacks == [window._toggle_sidebar]
    assert window._act_toggle_theme.triggered.callbacks == [window._toggle_theme]
    assert window._act_toggle_lang.triggered.callbacks == [window._toggle_language]
    assert window.action_convergence_viewer.object_name == "action_convergence_viewer"
    assert window.action_convergence_viewer.triggered.callbacks == [window._open_convergence_viewer]
    assert window._act_about.triggered.callbacks == [window._on_help]


def test_main_window_shell_mixin_toggle_sidebar_expands_hidden_sidebar() -> None:
    module = importlib.import_module("polynexus.gui.main_window_shell_mixin")
    widths = []

    class _Sidebar:
        def __init__(self):
            self._visible = False
            self.minimum_width = None
            self.maximum_width = None

        def isVisible(self):
            return self._visible

        def setVisible(self, value):
            self._visible = value

        def setMinimumWidth(self, value):
            self.minimum_width = value

        def setMaximumWidth(self, value):
            self.maximum_width = value

    class _Window(module.MainWindowShellMixin):
        def __init__(self, sidebar):
            self._sidebar = sidebar
            self._sidebar_expanded_width = 240

        @staticmethod
        def _main_window_module():
            return SimpleNamespace(
                QWidget=object,
                animate_width=lambda sidebar, width: widths.append((sidebar, width)),
            )

        def findChild(self, cls, name):
            raise AssertionError("findChild should not be used when _sidebar is present")

    sidebar = _Sidebar()
    window = _Window(sidebar)

    window._toggle_sidebar()

    assert sidebar.isVisible() is True
    assert sidebar.minimum_width == 0
    assert sidebar.maximum_width == 0
    assert widths == [(sidebar, 240)]


def test_main_window_shell_mixin_on_settings_opens_dialog() -> None:
    module = importlib.import_module("polynexus.gui.main_window_shell_mixin")
    calls = []

    class _Dialog:
        def __init__(self, parent):
            calls.append(("init", parent))

        def exec(self):
            calls.append(("exec", None))

    class _Window(module.MainWindowShellMixin):
        @staticmethod
        def _main_window_module():
            return SimpleNamespace(SettingsDialog=_Dialog)

    window = _Window()

    window._on_settings()

    assert calls == [("init", window), ("exec", None)]


def test_main_window_shell_mixin_on_help_uses_about_dialog() -> None:
    module = importlib.import_module("polynexus.gui.main_window_shell_mixin")
    calls = []

    class _MessageBox:
        @staticmethod
        def about(parent, title, text):
            calls.append((parent, title, text))

    class _Window(module.MainWindowShellMixin):
        @staticmethod
        def _main_window_module():
            return SimpleNamespace(QMessageBox=_MessageBox)

    window = _Window()

    window._on_help()

    assert len(calls) == 1
    assert calls[0][0] is window
    assert calls[0][1]
    assert calls[0][2]


def test_main_window_shell_mixin_on_quit_calls_close() -> None:
    module = importlib.import_module("polynexus.gui.main_window_shell_mixin")

    class _Window(module.MainWindowShellMixin):
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    window = _Window()

    window._on_quit()

    assert window.closed is True
