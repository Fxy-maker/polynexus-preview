"""PolyNexus Theme Engine — Dark/Light dual theme with live switching.

Design tokens are stored as frozen dataclasses.  ThemeEngine is a
QObject singleton that emits theme_changed when the user switches.

Usage:
    from polynexus.gui.theme import ThemeEngine, DARK_TOKENS, LIGHT_TOKENS

    engine = ThemeEngine.instance()
    engine.switch("light")

    # Connect to signal
    engine.theme_changed.connect(my_widget.on_theme_changed)
"""

from dataclasses import dataclass
from typing import Optional
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings


# ============================================================================
# Design Tokens
# ============================================================================

@dataclass(frozen=True)
class ThemeTokens:
    """All visual design tokens for one theme.

    Background hierarchy: deep (root) → panel (sidebar) → surface (alt rows) →
                          card (widgets) → hover → input
    Text hierarchy:       primary → secondary → muted → on_accent
    Border hierarchy:     border → border_light → border_focus
    """
    name: str

    # ── Background hierarchy (6 levels) ──
    bg_deep: str        # Root / main window background
    bg_panel: str       # Sidebar, group boxes
    bg_surface: str     # Table alternate rows, subtle elevation
    bg_card: str        # Cards, buttons, inputs
    bg_hover: str       # Hover state
    bg_input: str       # Focused inputs, editable areas

    # ── Borders ──
    border: str
    border_light: str
    border_focus: str

    # ── Text ──
    text_primary: str
    text_secondary: str
    text_muted: str
    text_on_accent: str

    # ── Accents (per-technique) ──
    accent_saxs: str
    accent_waxs: str
    accent_dsc: str
    accent_ir: str
    accent_nmr: str
    accent_joint: str   # Joint / multi-technique analysis

    # ── Functional ──
    success: str
    warning: str
    danger: str
    info: str           # Informational / neutral highlight

    # ── Special ──
    topbar_start: str
    topbar_end: str
    scrollbar_bg: str
    scrollbar_handle: str
    shadow: str         # Card / modal shadow colour

    # ── Spacing (8dp rhythm) ──
    spacing_xs: int = 4
    spacing_sm: int = 8
    spacing_md: int = 12
    spacing_lg: int = 16
    spacing_xl: int = 24
    spacing_xxl: int = 32
    spacing_xxxl: int = 48

    # ── Typography ──
    font_family: str = (
        '"Microsoft YaHei UI", "Microsoft YaHei", '
        '"Noto Sans CJK SC", "Source Han Sans SC", '
        '"Segoe UI Variable Text", "Segoe UI", '
        'sans-serif'
    )
    font_mono: str = (
        '"Cascadia Code", "Cascadia Mono", '
        '"Consolas", "SF Mono", monospace'
    )
    font_size_sm2: int = 10   # Captions, fine print
    font_size_sm: int = 11    # Secondary labels
    font_size_base: int = 13  # Body
    font_size_lg: int = 15    # Sub-headings
    font_size_xl: int = 18    # Section titles
    font_size_xxl: int = 24   # Page titles / hero

    # ── Radii ──
    radius_sm: int = 4
    radius_md: int = 6
    radius_lg: int = 8
    radius_xl: int = 12

    # ── Chart colours (comma-separated hex, 8 colours) ──
    chart_series: str = (
        "#4f8ef7,#00c8d4,#e69f00,#00b87c,#9b72cf,"
        "#f06292,#a1887f,#ffb74d"
    )


# ============================================================================
# Dark Theme (default)
# ============================================================================

DARK_TOKENS = ThemeTokens(
    name="dark",
    # Backgrounds — cool deep navy palette
    bg_deep="#111418",
    bg_panel="#181b20",
    bg_surface="#15191e",
    bg_card="#20252b",
    bg_hover="#282f36",
    bg_input="#171b20",
    # Borders
    border="#2a3138",
    border_light="#3a444f",
    border_focus="#5b8ccf",
    # Text
    text_primary="#e8eaf0",
    text_secondary="#8b92a8",
    text_muted="#555d7a",
    text_on_accent="#ffffff",
    # Accents — Nature/Science journal palette
    accent_saxs="#00c8d4",      # Cyan — nanostructure
    accent_waxs="#4f8ef7",      # Blue — crystallography
    accent_dsc="#e69f00",       # Amber — thermal
    accent_ir="#00b87c",        # Emerald — spectroscopy
    accent_nmr="#9b72cf",       # Violet — magnetic resonance
    accent_joint="#f0a060",     # Coral — multi-technique
    # Functional
    success="#00b87c",
    warning="#e69f00",
    danger="#d55e00",
    info="#5ba4fc",
    # Special
    topbar_start="#0d0f13",
    topbar_end="#1a2028",
    scrollbar_bg="#101216",
    scrollbar_handle="#3a4652",
    shadow="rgba(0,0,0,0.50)",
    # Chart series — vibrant-on-dark
    chart_series="#4f8ef7,#00c8d4,#e69f00,#00b87c,#9b72cf,#f06292,#a1887f,#ffb74d",
)


# ============================================================================
# Light Theme
# ============================================================================

LIGHT_TOKENS = ThemeTokens(
    name="light",
    # Backgrounds — crisp academic white/grey
    bg_deep="#f7f9fc",
    bg_panel="#eef3f8",
    bg_surface="#f3f6fa",
    bg_card="#ffffff",
    bg_hover="#e8eef5",
    bg_input="#ffffff",
    # Borders
    border="#d6e0ea",
    border_light="#e4ebf2",
    border_focus="#3f6fb4",
    # Text
    text_primary="#172033",
    text_secondary="#4e5b6e",
    text_muted="#8792a3",
    text_on_accent="#ffffff",
    # Accents — slightly muted for light background readability
    accent_saxs="#168e9f",
    accent_waxs="#3f6fb4",
    accent_dsc="#b77a10",
    accent_ir="#17845d",
    accent_nmr="#7257ad",
    accent_joint="#b96b3c",
    # Functional
    success="#00875a",
    warning="#d48800",
    danger="#c45200",
    info="#3b82f6",
    # Special
    topbar_start="#ffffff",
    topbar_end="#ffffff",
    scrollbar_bg="#f7f9fc",
    scrollbar_handle="#c9d3df",
    shadow="rgba(0,0,0,0.06)",
    # Chart series — balanced on white
    chart_series="#3f6fb4,#168e9f,#b77a10,#17845d,#7257ad,#b85c73,#81766c,#c98f3d",
)


# ============================================================================
# Backward-compatible aliases (so styles.py can be migrated incrementally)
# ============================================================================

def _current_tokens() -> ThemeTokens:
    """Return tokens for the currently active theme (dark by default)."""
    return ThemeEngine.instance().tokens


def _get_dark_tokens():
    return DARK_TOKENS


# ── Technique metadata ──
TECHNIQUE_COLORS = {
    "saxs":  DARK_TOKENS.accent_saxs,
    "waxs":  DARK_TOKENS.accent_waxs,
    "dsc":   DARK_TOKENS.accent_dsc,
    "ir":    DARK_TOKENS.accent_ir,
    "nmr":   DARK_TOKENS.accent_nmr,
    "joint": DARK_TOKENS.accent_joint,
}

TECHNIQUE_ICONS = {
    "saxs":  "\u25a0",   # ■ filled square — scattering pattern
    "waxs":  "\u25c6",   # ◆ diamond — crystal lattice
    "dsc":   "\u25b2",   # ▲ triangle — thermal peak
    "ir":    "\u25cf",   # ● circle — molecular vibration
    "nmr":   "\u2b21",   # ⬡ hexagon — magnetic shielding
    "joint": "\u2263",   # ≣ triple bar — combined analysis
}

TECHNIQUE_LABELS = {
    "saxs":  "SAXS",
    "waxs":  "WAXS",
    "dsc":   "DSC",
    "ir":    "IR",
    "nmr":   "NMR",
    "joint": "Joint",
}

TECHNIQUE_DESCRIPTIONS = {
    "saxs":  "Small-Angle X-ray Scattering\nNanostructure: L, lc, GCF, IDF",
    "waxs":  "Wide-Angle X-ray Scattering\nCrystallinity, Scherrer, peaks",
    "dsc":   "Differential Scanning Calorimetry\nTg, Tm, Xc, Avrami kinetics",
    "ir":    "Infrared Spectroscopy\nDFT/DFPT simulation, peak assignment",
    "nmr":   "Solid-State NMR\nGIPAW-DFT, relaxation, CSA",
    "joint": "Multi-Technique Correlation\nCross-validate crystallinity, phase composition",
}


# ============================================================================
# Theme Engine
# ============================================================================

class ThemeEngine(QObject):
    """Singleton theme manager with live-switch capability.

    Emits theme_changed(name) whenever the theme is switched.
    Connected widgets should re-apply their styles in the slot.
    """

    theme_changed = Signal(str)

    _instance: Optional["ThemeEngine"] = None

    @classmethod
    def instance(cls) -> "ThemeEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, parent=None):
        if ThemeEngine._instance is not None:
            raise RuntimeError("Use ThemeEngine.instance()")
        super().__init__(parent)
        ThemeEngine._instance = self
        self._current = self._load_preference()

    # ── Properties ──

    @property
    def current(self) -> str:
        return self._current

    @property
    def tokens(self) -> ThemeTokens:
        return DARK_TOKENS if self._current == "dark" else LIGHT_TOKENS

    @property
    def is_dark(self) -> bool:
        return self._current == "dark"

    # ── Actions ──

    def switch(self, theme_name: str):
        """Switch to *theme_name* and broadcast theme_changed."""
        if theme_name not in ("dark", "light"):
            return
        if theme_name == self._current:
            return
        self._current = theme_name
        self._save_preference(theme_name)

        # Re-apply QSS to entire application
        app = QApplication.instance()
        if app:
            app.setStyleSheet(build_qss(self.tokens))
            # Force repaint of all top-level widgets
            for widget in app.topLevelWidgets():
                widget.style().unpolish(widget)
                widget.style().polish(widget)

        self.theme_changed.emit(theme_name)

    def toggle(self):
        """Toggle between dark and light."""
        self.switch("light" if self._current == "dark" else "dark")

    # ── Persistence ──

    def _load_preference(self) -> str:
        s = QSettings("PolyNexus", "PolyNexus")
        return s.value("theme", "dark")

    def _save_preference(self, theme_name: str):
        s = QSettings("PolyNexus", "PolyNexus")
        s.setValue("theme", theme_name)


# ============================================================================
# QSS Builder
# ============================================================================

def build_qss(t: ThemeTokens) -> str:
    """Generate complete QSS stylesheet from design tokens."""
    return f"""
/* ============================================================
   PolyNexus v2.1  {t.name.capitalize()} Theme
   Token-driven QSS — do not edit manually
   ============================================================ */

/* ── Root ── */
QWidget {{
    background-color: {t.bg_deep};
    color: {t.text_primary};
    font-family: {t.font_family};
    font-size: {t.font_size_base}px;
    letter-spacing: 0;
}}

QMainWindow {{
    background-color: {t.bg_deep};
}}

QMainWindow::separator {{
    width: 1px;
    height: 1px;
    background: {t.border};
}}

/* ── Top bar ── */
QWidget#topbar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {t.topbar_start}, stop:1 {t.topbar_end});
    border-bottom: 1px solid {t.border};
    min-height: 48px;
    max-height: 48px;
}}

QWidget#workspace {{
    background: transparent;
}}

QScrollArea#workspace_scroll {{
    background-color: transparent;
    border: none;
}}

QScrollArea#workspace_scroll QWidget#workspace {{
    background-color: transparent;
}}

QWidget#workflow_header {{
    background-color: transparent;
    border: none;
    border-bottom: 1px solid {t.border_light};
    border-radius: 0;
}}

QLabel#workspace_title {{
    color: {t.text_primary};
    font-size: {t.font_size_xl}px;
    font-weight: 650;
}}

QLabel#workspace_subtitle {{
    color: {t.text_secondary};
    font-size: {t.font_size_sm}px;
}}

QLabel#workflow_metric {{
    color: {t.text_secondary};
    font-size: {t.font_size_sm}px;
    background-color: transparent;
    border: none;
    padding: 2px 4px;
}}

QFrame#drop_banner {{
    background-color: {t.bg_surface};
    border: 1px dashed {t.border_focus};
    border-radius: {t.radius_md}px;
    min-height: 36px;
    max-height: 36px;
}}

QFrame#drop_banner QLabel {{
    color: {t.text_primary};
    font-size: {t.font_size_sm}px;
    font-weight: 600;
}}

QFrame#workflow_task_box {{
    background-color: {t.bg_surface};
    border: 1px solid {t.border_light};
    border-radius: {t.radius_md}px;
    min-width: 290px;
    max-width: 410px;
}}

QLabel#workflow_task_label {{
    color: {t.text_secondary};
    font-size: {t.font_size_sm2}px;
    font-weight: 700;
    letter-spacing: 0;
    text-transform: uppercase;
}}

QLabel#workflow_task_title {{
    color: {t.text_primary};
    font-size: {t.font_size_lg}px;
    font-weight: 700;
}}

QLabel#workflow_task_detail {{
    color: {t.text_secondary};
    font-size: {t.font_size_sm}px;
}}

QFrame#context_suggestion_box {{
    background-color: {t.bg_card};
    border: 1px solid {t.border_light};
    border-radius: {t.radius_md}px;
    margin-bottom: {t.spacing_xs}px;
}}

QLabel#context_suggestion_title {{
    color: {t.text_primary};
    font-size: {t.font_size_base}px;
    font-weight: 700;
}}

QLabel#context_suggestion_detail {{
    color: {t.text_secondary};
    font-size: {t.font_size_sm}px;
}}

QFrame#work_memory_box {{
    background-color: {t.bg_card};
    border: 1px solid {t.border_light};
    border-radius: {t.radius_md}px;
    margin-bottom: {t.spacing_xs}px;
}}

QLabel#work_memory_title {{
    color: {t.text_primary};
    font-size: {t.font_size_base}px;
    font-weight: 700;
}}

QLabel#work_memory_detail {{
    color: {t.text_secondary};
    font-size: {t.font_size_sm}px;
}}

QFrame#nav_indicator {{
    background-color: {t.accent_saxs};
    border: none;
    border-radius: 2px;
    min-width: 3px;
    max-width: 3px;
}}

/* ── Sidebar ── */
QWidget#sidebar {{
    background-color: {t.bg_panel};
    border-right: 1px solid {t.border};
    min-width: 232px;
    max-width: 232px;
}}

QScrollArea#sidebar_scroll {{
    background-color: transparent;
    border: none;
}}

QScrollArea#sidebar_scroll QWidget#sidebar_content {{
    background-color: transparent;
}}

/* ── Fixed recent projects panel at sidebar bottom ── */
QWidget#sidebar_recent_panel {{
    background-color: {t.bg_panel};
    border-top: 1px solid {t.border};
}}

QWidget#sidebar_recent_panel QLabel#sidebar_title {{
    padding-top: 4px;
}}

QWidget#sidebar_recent_panel QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
    padding: 0px {t.spacing_xs}px;
}}

QWidget#sidebar_recent_panel QListWidget::item {{
    padding: {t.spacing_xs}px {t.spacing_md}px;
    border-radius: {t.radius_sm}px;
    color: {t.text_secondary};
}}

QWidget#sidebar QLabel#sidebar_title {{
    color: {t.text_muted};
    font-size: {t.font_size_sm2}px;
    text-transform: uppercase;
    letter-spacing: 0;
    padding: 6px {t.spacing_xl}px 4px {t.spacing_xl}px;
    font-weight: 600;
    min-height: 28px;
    max-height: 28px;
}}

QPushButton#nav_parent_btn {{
    background: transparent;
    border: none;
    border-radius: {t.radius_sm}px;
    text-align: left;
    padding: 6px 18px;
    margin: 1px {t.spacing_md}px;
    color: {t.text_secondary};
    font-size: {t.font_size_sm}px;
    font-weight: 700;
}}

QPushButton#nav_parent_btn:hover {{
    background-color: {t.bg_hover};
    color: {t.text_primary};
}}

QPushButton#nav_sub_btn {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {t.radius_sm}px;
    text-align: left;
    padding: 6px 12px 6px 34px;
    margin: 1px {t.spacing_md}px;
    color: {t.text_secondary};
    font-size: {t.font_size_sm}px;
}}

QPushButton#nav_sub_btn:hover {{
    background-color: {t.bg_hover};
    border-color: {t.border_light};
    color: {t.text_primary};
}}

QPushButton#nav_sub_btn:checked {{
    background-color: {t.bg_card};
    border-color: {t.border_light};
    color: {t.text_primary};
    font-weight: 700;
}}

/* ── Navigation buttons (base — per-technique checked state via nav_button_style) ── */
QPushButton#nav_btn {{
    background: transparent;
    border: none;
    border-radius: {t.radius_md}px;
    text-align: left;
    padding: {t.spacing_sm}px {t.spacing_lg}px;
    margin: 2px {t.spacing_sm}px;
    color: {t.text_secondary};
    font-size: {t.font_size_base}px;
    font-weight: 400;
}}

QPushButton#nav_btn:hover {{
    background-color: {t.bg_hover};
    color: {t.text_primary};
}}

QPushButton#nav_btn:checked {{
    background-color: {t.bg_card};
    color: {t.text_primary};
    font-weight: 600;
    border-left: 3px solid {t.accent_waxs};
}}

/* ── Technique description ── */
QLabel#tech_desc {{
    color: {t.text_muted};
    font-size: {t.font_size_sm2}px;
    padding: 0 {t.spacing_xxl}px {t.spacing_sm}px {t.spacing_xxl}px;
    line-height: 1.5;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {t.bg_card};
    border: 1px solid {t.border_light};
    border-radius: {t.radius_sm}px;
    padding: 6px 14px;
    color: {t.text_secondary};
    font-size: {t.font_size_sm}px;
    min-height: 24px;
}}

QPushButton:hover {{
    border-color: {t.accent_waxs};
    color: {t.accent_waxs};
}}

QPushButton:pressed {{
    background-color: {t.bg_hover};
}}

QPushButton:disabled {{
    color: {t.text_muted};
    border-color: {t.border};
    background-color: {t.bg_deep};
}}

QPushButton#primary_btn {{
    background-color: {t.accent_waxs};
    color: {t.text_on_accent};
    border: none;
    font-weight: 600;
    font-size: {t.font_size_sm}px;
    padding: 7px 18px;
}}

QPushButton#primary_btn:hover {{
    background-color: {t.border_focus};
}}

QPushButton#primary_btn:disabled {{
    background: {t.border_light};
    color: {t.text_muted};
}}

QPushButton#secondary_btn {{
    background: transparent;
    border: 1px solid {t.border_light};
    color: {t.text_secondary};
}}

QPushButton#secondary_btn:hover {{
    border-color: {t.accent_waxs};
    color: {t.accent_waxs};
}}

QPushButton#danger_btn {{
    border-color: {t.danger};
    color: {t.danger};
}}

QPushButton#danger_btn:hover {{
    background-color: {t.danger};
    color: white;
}}

/* ── Theme / Lang toggle buttons ── */
QPushButton#theme_btn,
QPushButton#lang_btn {{
    background: transparent;
    border: 1px solid {t.border_light};
    border-radius: {t.radius_sm}px;
    font-size: 14px;
    padding: 0;
    color: {t.text_secondary};
    min-width: 36px;
    max-width: 36px;
    min-height: 30px;
    max-height: 30px;
}}

QPushButton#theme_btn:hover,
QPushButton#lang_btn:hover {{
    border-color: {t.accent_waxs};
    color: {t.accent_waxs};
    background-color: {t.bg_hover};
}}

/* ── Line Edit ── */
QLineEdit {{
    background-color: {t.bg_input};
    border: 1px solid {t.border_light};
    border-radius: {t.radius_sm}px;
    padding: {t.spacing_sm}px 10px;
    color: {t.text_primary};
    selection-background-color: {t.accent_waxs};
    selection-color: {t.text_on_accent};
}}

QLineEdit:focus {{
    border-color: {t.border_focus};
}}

QLineEdit#path_input {{
    font-family: {t.font_family};
    font-size: {t.font_size_base}px;
}}

/* ── Combo Box ── */
QComboBox {{
    background-color: {t.bg_input};
    border: 1px solid {t.border_light};
    border-radius: {t.radius_md}px;
    padding: 5px 10px;
    color: {t.text_primary};
    min-width: 120px;
}}

QComboBox:hover {{
    border-color: {t.accent_waxs};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border: none;
}}

QComboBox QAbstractItemView {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    selection-background-color: {t.bg_hover};
    selection-color: {t.text_primary};
    padding: {t.spacing_xs}px;
    outline: none;
}}

/* ── Tab Widget ── */
QTabWidget::pane {{
    border: none;
    border-top: 1px solid {t.border_light};
    background-color: transparent;
    border-radius: 0;
    top: -1px;
}}

QTabBar::tab {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: {t.spacing_sm}px {t.spacing_xxl}px;
    color: {t.text_secondary};
    font-size: {t.font_size_base}px;
    font-weight: 500;
    min-width: 80px;
}}

QTabBar::tab:hover {{
    color: {t.text_primary};
    background-color: transparent;
    border-radius: 0;
}}

QTabBar::tab:selected {{
    color: {t.accent_waxs};
    border-bottom: 2px solid {t.accent_waxs};
    font-weight: 650;
}}

/* ── Tables ── */
QTableWidget {{
    background-color: {t.bg_deep};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    gridline-color: {t.border};
    alternate-background-color: {t.bg_surface};
    selection-background-color: {t.bg_hover};
    selection-color: {t.text_primary};
}}

QTableWidget::item {{
    padding: {t.spacing_xs}px {t.spacing_sm}px;
    border-bottom: 1px solid {t.border};
}}

QTableWidget::item:selected {{
    background-color: {t.accent_waxs}22;
    color: {t.text_primary};
}}

QHeaderView::section {{
    background-color: {t.bg_panel};
    color: {t.text_secondary};
    border: none;
    border-bottom: 2px solid {t.border};
    border-right: 1px solid {t.border};
    padding: {t.spacing_sm}px {t.spacing_md}px;
    font-size: {t.font_size_sm}px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0;
}}

QHeaderView::section:hover {{
    background-color: {t.bg_hover};
    color: {t.text_primary};
}}

/* ── Tree View ── */
QTreeView {{
    background-color: {t.bg_deep};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    alternate-background-color: {t.bg_surface};
    selection-background-color: {t.bg_hover};
    selection-color: {t.text_primary};
    outline: none;
}}

QTreeView::item {{
    padding: {t.spacing_xs}px {t.spacing_sm}px;
    border: none;
}}

QTreeView::item:hover {{
    background-color: {t.bg_hover};
}}

QTreeView::item:selected {{
    background-color: {t.accent_waxs}22;
}}

QTreeView::branch {{
    background-color: {t.bg_deep};
}}

/* ── Scroll Bars ── */
QScrollBar:vertical {{
    background: {t.scrollbar_bg};
    width: 10px;
    margin: 0;
    border: none;
}}

QScrollBar::handle:vertical {{
    background: {t.scrollbar_handle};
    min-height: 40px;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: {t.text_muted};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
}}

QScrollBar:horizontal {{
    background: {t.scrollbar_bg};
    height: 10px;
    margin: 0;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background: {t.scrollbar_handle};
    min-width: 40px;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {t.text_muted};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
    border: none;
}}

/* ── Tool Tips ── */
QToolTip {{
    background-color: {t.bg_card};
    color: {t.text_primary};
    border: 1px solid {t.border_light};
    border-radius: {t.radius_sm}px;
    padding: {t.spacing_sm}px {t.spacing_md}px;
    font-size: {t.font_size_sm}px;
}}

/* ── Menu Bar ── */
QMenuBar {{
    background-color: {t.topbar_start};
    border-bottom: 1px solid {t.border};
    padding: 2px 0;
    font-size: {t.font_size_base}px;
}}

QMenuBar::item {{
    padding: {t.spacing_sm}px {t.spacing_md}px;
    border-radius: {t.radius_sm}px;
}}

QMenuBar::item:selected {{
    background-color: {t.bg_hover};
}}

QMenu {{
    background-color: {t.bg_card};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    padding: {t.spacing_xs}px;
}}

QMenu::item {{
    padding: {t.spacing_sm}px {t.spacing_xxl}px {t.spacing_sm}px {t.spacing_lg}px;
    border-radius: {t.radius_sm}px;
    font-size: {t.font_size_base}px;
}}

QMenu::item:selected {{
    background-color: {t.bg_hover};
}}

QMenu::separator {{
    height: 1px;
    background: {t.border_light};
    margin: {t.spacing_xs}px {t.spacing_sm}px;
}}

/* ── Status Bar ── */
QStatusBar {{
    background-color: transparent;
    border-top: 1px solid {t.border};
    color: {t.text_secondary};
    font-size: {t.font_size_sm}px;
    padding: 2px {t.spacing_sm}px;
    min-height: 24px;
}}

QStatusBar::item {{
    border: none;
}}

QLabel#status_tech {{
    color: {t.accent_waxs};
    font-size: {t.font_size_sm2}px;
    font-weight: 600;
    background-color: transparent;
    border: none;
    border-radius: 0;
    padding: 1px {t.spacing_sm}px;
    margin: 0 {t.spacing_xs}px;
}}

/* ── Progress Bar ── */
QProgressBar {{
    background-color: {t.bg_input};
    border: none;
    border-radius: 3px;
    max-height: 6px;
    min-height: 6px;
    text-align: center;
    font-size: {t.font_size_sm2}px;
    color: {t.text_muted};
}}

QProgressBar::chunk {{
    background-color: {t.accent_waxs};
    border: none;
    border-radius: 3px;
    margin: 1px;
}}

QProgressBar:indeterminate {{
    background-color: {t.bg_input};
}}

QProgressBar:indeterminate::chunk {{
    background-color: {t.accent_waxs};
    border: none;
    border-radius: 3px;
}}

/* ── Group Box ── */
QGroupBox {{
    background-color: transparent;
    border: 1px solid {t.border_light};
    border-radius: {t.radius_sm}px;
    margin-top: {t.spacing_lg}px;
    padding: {t.spacing_lg}px {t.spacing_lg}px {t.spacing_lg}px {t.spacing_lg}px;
    font-size: {t.font_size_base}px;
    font-weight: 650;
    color: {t.text_secondary};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 {t.spacing_sm}px;
    margin-left: {t.spacing_md}px;
    background-color: transparent;
    border-radius: 0;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {t.border};
    margin: 0;
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

QSplitter::handle:hover {{
    background-color: {t.accent_waxs};
}}

/* ── Text Edit ── */
QTextEdit, QPlainTextEdit {{
    background-color: {t.bg_input};
    border: 1px solid {t.border_light};
    border-radius: {t.radius_md}px;
    padding: {t.spacing_sm}px;
    color: {t.text_primary};
    font-family: {t.font_mono};
    font-size: {t.font_size_sm}px;
    selection-background-color: {t.accent_waxs}44;
    selection-color: {t.text_primary};
}}

/* ── Spin Box ── */
QSpinBox, QDoubleSpinBox {{
    background-color: {t.bg_input};
    border: 1px solid {t.border_light};
    border-radius: {t.radius_md}px;
    padding: {t.spacing_xs}px {t.spacing_sm}px;
    color: {t.text_primary};
    font-family: {t.font_mono};
    font-size: {t.font_size_base}px;
}}

QSpinBox::up-button,
QDoubleSpinBox::up-button {{
    border: none;
    border-left: 1px solid {t.border_light};
    border-radius: 0 {t.radius_md}px {t.radius_md}px 0;
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
}}

QSpinBox::down-button,
QDoubleSpinBox::down-button {{
    border: none;
    border-left: 1px solid {t.border_light};
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {t.border_focus};
}}

/* ── Check Box ── */
QCheckBox {{
    color: {t.text_secondary};
    spacing: {t.spacing_sm}px;
}}

QCheckBox:hover {{
    color: {t.text_primary};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {t.border_light};
    border-radius: {t.radius_sm}px;
    background-color: {t.bg_input};
}}

QCheckBox::indicator:checked {{
    background-color: {t.accent_waxs};
    border-color: {t.accent_waxs};
}}

/* ── Radio Button ── */
QRadioButton {{
    color: {t.text_secondary};
    spacing: {t.spacing_sm}px;
}}

QRadioButton:hover {{
    color: {t.text_primary};
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {t.border_light};
    border-radius: 8px;
    background-color: {t.bg_input};
}}

QRadioButton::indicator:checked {{
    background-color: {t.accent_waxs};
    border-color: {t.accent_waxs};
}}

/* ── Project Badge ── */
QWidget#project_badge {{
    background-color: transparent;
    border: none;
    border-radius: 0;
    padding: 0;
}}

QWidget#project_badge QLabel {{
    color: {t.text_secondary};
    font-size: {t.font_size_sm}px;
}}

/* ── List Widget ── */
QListWidget {{
    background-color: {t.bg_deep};
    border: 1px solid {t.border};
    border-radius: {t.radius_md}px;
    outline: none;
    padding: {t.spacing_xs}px;
}}

QListWidget::item {{
    padding: {t.spacing_sm}px {t.spacing_md}px;
    border-radius: {t.radius_sm}px;
    color: {t.text_secondary};
}}

QListWidget::item:hover {{
    background-color: {t.bg_hover};
    color: {t.text_primary};
}}

QListWidget::item:selected {{
    background-color: {t.accent_waxs}22;
    color: {t.text_primary};
}}

/* ── Message Box ── */
QMessageBox {{
    background-color: {t.bg_panel};
}}

QMessageBox QLabel {{
    color: {t.text_primary};
}}

/* ── Dialog ── */
QDialog {{
    background-color: {t.bg_deep};
}}

/* ── Label ── */
QLabel {{
    background: transparent;
    border: none;
}}
"""


# ============================================================================
# Technique Accent Helpers (theme-aware)
# ============================================================================

def nav_button_style(technique: str, tokens: ThemeTokens, checked: bool = False) -> str:
    """Return dynamic QSS for a technique navigation button.

    Each technique gets its own accent colour for the checked state.
    """
    accent_map = {
        "saxs":  tokens.accent_saxs,
        "waxs":  tokens.accent_waxs,
        "dsc":   tokens.accent_dsc,
        "ir":    tokens.accent_ir,
        "nmr":   tokens.accent_nmr,
        "joint": tokens.accent_joint,
    }
    accent = accent_map.get(technique, tokens.accent_waxs)

    if checked:
        return (
            f"QPushButton {{"
            f"  background-color: {tokens.bg_card};"
            f"  border: none;"
            f"  border-left: 3px solid {accent};"
            f"  border-radius: {tokens.radius_md}px;"
            f"  text-align: left;"
            f"  padding: {tokens.spacing_sm}px {tokens.spacing_lg}px;"
            f"  margin: 2px {tokens.spacing_sm}px;"
            f"  color: {tokens.text_primary};"
            f"  font-weight: 600;"
            f"  font-size: {tokens.font_size_base}px;"
            f"}}"
        )
    return (
        f"QPushButton {{"
        f"  background: transparent;"
        f"  border: none;"
        f"  border-radius: {tokens.radius_md}px;"
        f"  text-align: left;"
        f"  padding: {tokens.spacing_sm}px {tokens.spacing_lg}px;"
        f"  margin: 2px {tokens.spacing_sm}px;"
        f"  color: {tokens.text_secondary};"
        f"  font-size: {tokens.font_size_base}px;"
        f"}}"
        f"QPushButton:hover {{"
        f"  background-color: {tokens.bg_hover};"
        f"  color: {tokens.text_primary};"
        f"}}"
    )


def technique_accent(technique: str, tokens: ThemeTokens) -> str:
    """Return accent colour for a technique from the given tokens."""
    accent_map = {
        "saxs":  tokens.accent_saxs,
        "waxs":  tokens.accent_waxs,
        "dsc":   tokens.accent_dsc,
        "ir":    tokens.accent_ir,
        "nmr":   tokens.accent_nmr,
        "joint": tokens.accent_joint,
    }
    return accent_map.get(technique, tokens.accent_waxs)


def get_chart_colors(tokens: Optional[ThemeTokens] = None) -> list:
    """Return chart series colours as a list of hex strings.

    Args:
        tokens: Theme tokens (defaults to current theme).
    """
    if tokens is None:
        tokens = ThemeEngine.instance().tokens
    return [c.strip() for c in tokens.chart_series.split(",") if c.strip()]
