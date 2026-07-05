"""PolyNexus GUI widgets package."""

from __future__ import annotations

__all__ = [
    "ChartGallery",
    "FigureFilePreview",
    "ChartViewer",
    "ChartEditor",
    "SettingsDialog",
]


def __getattr__(name: str):
    if name in {"ChartGallery", "FigureFilePreview", "ChartViewer"}:
        from .chart_viewer import ChartGallery, FigureFilePreview, ChartViewer

        exports = {
            "ChartGallery": ChartGallery,
            "FigureFilePreview": FigureFilePreview,
            "ChartViewer": ChartViewer,
        }
    elif name == "ChartEditor":
        from .chart_editor import ChartEditor

        exports = {"ChartEditor": ChartEditor}
    elif name == "SettingsDialog":
        from .settings_dialog import SettingsDialog

        exports = {"SettingsDialog": SettingsDialog}
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    globals().update(exports)
    return globals()[name]
