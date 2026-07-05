"""PolyNexus keyboard shortcuts — declarative binding table.

Usage:
    from polynexus.gui.shortcuts import bind_shortcuts
    bind_shortcuts(self)  # in MainWindow.__init__
"""

from PySide6.QtGui import QShortcut, QKeySequence

SHORTCUTS = [
    ("Ctrl+R",        "_on_run",           "Run Analysis"),
    ("Ctrl+Shift+R",  "_on_replot",        "Re-plot Only"),
    ("Ctrl+E",        "_on_export",        "Export Results"),
    ("Ctrl+T",        "_toggle_theme",     "Toggle Theme"),
    ("Ctrl+L",        "_toggle_language",  "Toggle Language"),
    ("Ctrl+B",        "_toggle_sidebar",   "Toggle Sidebar"),
    ("Ctrl+O",        "_on_browse",        "Open File"),
    ("Ctrl+,",        "_on_settings",      "Settings"),
    ("Ctrl+Q",        "_on_quit",          "Quit"),
    ("Ctrl+1",        "_on_tech_saxs",     "SAXS"),
    ("Ctrl+2",        "_on_tech_waxs",     "WAXS"),
    ("Ctrl+3",        "_on_tech_dsc",      "DSC"),
    ("Ctrl+4",        "_on_tech_ir",       "IR"),
    ("Ctrl+5",        "_on_tech_nmr",      "NMR"),
    ("F1",            "_on_help",          "Help"),
]


def bind_shortcuts(main_window):
    """Create QShortcut objects for all registered shortcuts.

    Any shortcut whose method_name does not exist on main_window
    is silently skipped, so this is safe to call before all
    methods are implemented.
    """
    shortcuts = []
    for keys, method_name, _desc in SHORTCUTS:
        if not hasattr(main_window, method_name):
            continue
        shortcut = QShortcut(QKeySequence(keys), main_window)
        callback = getattr(main_window, method_name)
        shortcut.activated.connect(lambda cb=callback: cb())
        shortcuts.append(shortcut)
    return shortcuts


def get_shortcut_list() -> list:
    """Return a list of (keys, description) tuples for help display."""
    return [(keys, desc) for keys, _, desc in SHORTCUTS]
