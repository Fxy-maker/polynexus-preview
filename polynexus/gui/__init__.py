"""PolyNexus GUI package.

Qt modules are imported lazily so command-line tools can run in headless
environments and the PyQt6 convergence viewer stays isolated from PySide6.
"""

__all__ = [
    "MainWindow",
    "AnalysisWorker",
    "BatchWorker",
    "ChartGallery",
    "ChartViewer",
    "ThemeEngine",
    "DARK_TOKENS",
    "LIGHT_TOKENS",
    "build_qss",
    "AppState",
    "bind_shortcuts",
]


def __getattr__(name):
    if name in {"MainWindow", "AnalysisWorker", "BatchWorker"}:
        from .main_window import AnalysisWorker, BatchWorker, MainWindow

        return {"MainWindow": MainWindow, "AnalysisWorker": AnalysisWorker, "BatchWorker": BatchWorker}[name]
    if name in {"ChartGallery", "ChartViewer"}:
        from .widgets.chart_viewer import ChartGallery, ChartViewer

        return {"ChartGallery": ChartGallery, "ChartViewer": ChartViewer}[name]
    if name in {"ThemeEngine", "DARK_TOKENS", "LIGHT_TOKENS", "build_qss"}:
        from .theme import DARK_TOKENS, LIGHT_TOKENS, ThemeEngine, build_qss

        return {
            "ThemeEngine": ThemeEngine,
            "DARK_TOKENS": DARK_TOKENS,
            "LIGHT_TOKENS": LIGHT_TOKENS,
            "build_qss": build_qss,
        }[name]
    if name == "AppState":
        from .state import AppState

        return AppState
    if name == "bind_shortcuts":
        from .shortcuts import bind_shortcuts

        return bind_shortcuts
    raise AttributeError(name)
