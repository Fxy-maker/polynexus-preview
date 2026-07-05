"""PolyNexus dark theme — Qt stylesheet matching the HTML design spec.

Colour palette from PolyNexus v1.0 interface design:
    --bg-deep:     #0f1117   (window background)
    --bg-panel:    #1a1d2e   (panel / sidebar)
    --bg-card:     #222538   (card / group box)
    --bg-hover:    #2a2e45   (hover state)
    --border:      #2d3150   (border)
    --border-light:#3a3f5c   (lighter border)
    --text-primary:#e8eaf0   (primary text)
    --text-secondary:#8b92a8(secondary text)
    --text-muted:  #555d7a   (muted text)

Accent colours per technique:
    SAXS  cyan   #00c8d4
    WAXS  blue   #4f8ef7
    DSC   orange #e69f00
    IR    green  #00b87c
    NMR   purple #9b72cf

Functional accents:
    success  #00b87c
    warning  #e69f00
    danger   #d55e00
"""

# ── Colour palette ────────────────────────────────────────────────────────

C_BG_DEEP      = "#0f1117"
C_BG_PANEL     = "#1a1d2e"
C_BG_CARD      = "#222538"
C_BG_HOVER     = "#2a2e45"
C_BORDER       = "#2d3150"
C_BORDER_LIGHT = "#3a3f5c"
C_TEXT_PRIMARY = "#e8eaf0"
C_TEXT_SECONDARY = "#8b92a8"
C_TEXT_MUTED   = "#555d7a"

C_ACCENT_SAXS  = "#00c8d4"
C_ACCENT_WAXS  = "#4f8ef7"
C_ACCENT_DSC   = "#e69f00"
C_ACCENT_IR    = "#00b87c"
C_ACCENT_NMR   = "#9b72cf"

C_SUCCESS = "#00b87c"
C_WARNING = "#e69f00"
C_DANGER  = "#d55e00"

# ── Technique metadata ────────────────────────────────────────────────────

TECHNIQUE_COLORS = {
    "saxs": C_ACCENT_SAXS,
    "waxs": C_ACCENT_WAXS,
    "dsc":  C_ACCENT_DSC,
    "ir":   C_ACCENT_IR,
    "nmr":  C_ACCENT_NMR,
}

TECHNIQUE_ICONS = {
    "saxs": "◈",
    "waxs": "◆",
    "dsc":  "◆",   # fire emoji causes encoding issues in QSS
    "ir":   "◆",
    "nmr":  "◆",
}

TECHNIQUE_LABELS = {
    "saxs": "SAXS",
    "waxs": "WAXS",
    "dsc":  "DSC",
    "ir":   "IR",
    "nmr":  "NMR",
}

TECHNIQUE_DESCRIPTIONS = {
    "saxs": "Small-Angle X-ray Scattering\nNanostructure: L, lc, GCF, IDF",
    "waxs": "Wide-Angle X-ray Scattering\nCrystallinity, Scherrer, peaks",
    "dsc":  "Differential Scanning Calorimetry\nTg, Tm, Xc, Avrami kinetics",
    "ir":   "Infrared Spectroscopy\nDFT/DFPT simulation, peak assignment",
    "nmr":  "Solid-State NMR\nGIPAW-DFT, relaxation, CSA",
}

# ── QSS Stylesheet ────────────────────────────────────────────────────────

DARK_THEME = f"""
/* ============================================================
   PolyNexus v1.0  Dark Theme
   ============================================================ */

/* ----  Global  ---- */
QWidget {{
    background-color: {C_BG_DEEP};
    color: {C_TEXT_PRIMARY};
    font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {C_BG_DEEP};
}}

QMainWindow::separator {{
    width: 1px;
    height: 1px;
    background: {C_BORDER};
}}

/* ----  Top bar  ---- */
QWidget#topbar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0d1021, stop:1 #151828);
    border-bottom: 1px solid {C_BORDER};
    min-height: 44px;
    max-height: 44px;
}}

/* ----  Sidebar  ---- */
QWidget#sidebar {{
    background-color: {C_BG_PANEL};
    border-right: 1px solid {C_BORDER};
    min-width: 200px;
    max-width: 200px;
}}

QWidget#sidebar QLabel#sidebar_title {{
    color: {C_TEXT_MUTED};
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 2px;
    padding: 12px 16px 4px 16px;
}}

/* ----  Navigation buttons  ---- */
QPushButton#nav_btn {{
    background: transparent;
    border: none;
    border-radius: 6px;
    text-align: left;
    padding: 8px 16px;
    margin: 2px 8px;
    color: {C_TEXT_SECONDARY};
    font-size: 13px;
    font-weight: 400;
}}

QPushButton#nav_btn:hover {{
    background-color: {C_BG_HOVER};
    color: {C_TEXT_PRIMARY};
}}

QPushButton#nav_btn:checked {{
    background-color: {C_BG_CARD};
    color: {C_TEXT_PRIMARY};
    font-weight: 600;
    border-left: 3px solid {C_ACCENT_SAXS};
}}

/* ----  Navigation parent buttons (v2.0)  ---- */
QPushButton#nav_parent_btn {{
    background: transparent;
    border: none;
    text-align: left;
    padding: 6px 16px;
    margin: 0 8px;
    font-weight: 700;
    font-size: 12px;
}}

QPushButton#nav_sub_btn {{
    background: transparent;
    border: none;
    border-radius: 4px;
    text-align: left;
    padding: 4px 16px 4px 32px;
    margin: 1px 8px;
    color: {C_TEXT_SECONDARY};
    font-size: 12px;
}}

QPushButton#nav_sub_btn:hover {{
    background-color: {C_BG_HOVER};
    color: {C_TEXT_PRIMARY};
}}

QPushButton#nav_sub_btn:checked {{
    background-color: {C_BG_CARD};
    color: {C_TEXT_PRIMARY};
    font-weight: 600;
    border-left: 2px solid {C_ACCENT_WAXS};
}}

/* ----  Buttons  ---- */
QPushButton {{
    background-color: {C_BG_CARD};
    border: 1px solid {C_BORDER_LIGHT};
    border-radius: 6px;
    padding: 6px 14px;
    color: {C_TEXT_SECONDARY};
    font-size: 12px;
}}

QPushButton:hover {{
    border-color: {C_ACCENT_WAXS};
    color: {C_ACCENT_WAXS};
}}

QPushButton:pressed {{
    background-color: {C_BG_HOVER};
}}

QPushButton#primary_btn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {C_ACCENT_WAXS}, stop:1 #3a6fd8);
    color: white;
    border: none;
    font-weight: 600;
}}

QPushButton#primary_btn:hover {{
    opacity: 0.9;
}}

QPushButton#danger_btn {{
    border-color: {C_DANGER};
    color: {C_DANGER};
}}

QPushButton#danger_btn:hover {{
    background-color: {C_DANGER};
    color: white;
}}

/* ----  Line Edit  ---- */
QLineEdit {{
    background-color: {C_BG_CARD};
    border: 1px solid {C_BORDER_LIGHT};
    border-radius: 6px;
    padding: 6px 10px;
    color: {C_TEXT_PRIMARY};
    selection-background-color: {C_ACCENT_WAXS};
    selection-color: white;
}}

QLineEdit:focus {{
    border-color: {C_ACCENT_WAXS};
}}

QLineEdit#path_input {{
    font-family: "Consolas", "Cascadia Code", monospace;
    font-size: 11px;
}}

/* ----  Combo Box  ---- */
QComboBox {{
    background-color: {C_BG_CARD};
    border: 1px solid {C_BORDER_LIGHT};
    border-radius: 6px;
    padding: 5px 10px;
    color: {C_TEXT_PRIMARY};
    min-width: 120px;
}}

QComboBox:hover {{
    border-color: {C_ACCENT_WAXS};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {C_BG_CARD};
    border: 1px solid {C_BORDER};
    selection-background-color: {C_BG_HOVER};
    selection-color: {C_TEXT_PRIMARY};
    padding: 4px;
}}

/* ----  Tab Widget  ---- */
QTabWidget::pane {{
    border: 1px solid {C_BORDER};
    background-color: {C_BG_DEEP};
    border-radius: 4px;
}}

QTabBar::tab {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 20px;
    color: {C_TEXT_SECONDARY};
    font-size: 12px;
    min-width: 80px;
}}

QTabBar::tab:hover {{
    color: {C_TEXT_PRIMARY};
}}

QTabBar::tab:selected {{
    color: {C_ACCENT_WAXS};
    border-bottom: 2px solid {C_ACCENT_WAXS};
    font-weight: 600;
}}

/* ----  Table  ---- */
QTableWidget {{
    background-color: {C_BG_DEEP};
    border: 1px solid {C_BORDER};
    gridline-color: {C_BORDER};
    alternate-background-color: {C_BG_CARD};
    selection-background-color: {C_BG_HOVER};
    selection-color: {C_TEXT_PRIMARY};
}}

QTableWidget::item {{
    padding: 4px 8px;
    border-bottom: 1px solid {C_BORDER};
}}

QHeaderView::section {{
    background-color: {C_BG_PANEL};
    border: none;
    border-bottom: 1px solid {C_BORDER};
    padding: 6px 10px;
    color: {C_TEXT_SECONDARY};
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
}}

/* ----  Text Edit / Log Panel  ---- */
QTextEdit, QPlainTextEdit {{
    background-color: #0a0c14;
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 8px;
    color: {C_TEXT_SECONDARY};
    font-family: "Consolas", "Cascadia Code", monospace;
    font-size: 11px;
    selection-background-color: {C_ACCENT_WAXS};
}}

/* ----  Group Box  ---- */
QGroupBox {{
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    margin-top: 16px;
    padding: 12px;
    background-color: {C_BG_CARD};
    font-weight: 600;
    color: {C_TEXT_PRIMARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {C_TEXT_SECONDARY};
}}

/* ----  Scroll Bar  ---- */
QScrollBar:vertical {{
    background: {C_BG_DEEP};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {C_BORDER_LIGHT};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {C_TEXT_MUTED};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    height: 8px;
}}

QScrollBar::handle:horizontal {{
    background: {C_BORDER_LIGHT};
    border-radius: 4px;
}}

/* ----  Progress Bar  ---- */
QProgressBar {{
    background-color: {C_BG_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    height: 6px;
    text-align: center;
    font-size: 9px;
    color: {C_TEXT_MUTED};
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {C_ACCENT_SAXS}, stop:1 {C_ACCENT_WAXS});
    border-radius: 3px;
}}

/* ----  Splitter  ---- */
QSplitter::handle {{
    background-color: {C_BORDER};
    width: 1px;
}}

QSplitter::handle:hover {{
    background-color: {C_ACCENT_WAXS};
}}

/* ----  Tool Tip  ---- */
QToolTip {{
    background-color: {C_BG_CARD};
    border: 1px solid {C_BORDER_LIGHT};
    border-radius: 4px;
    padding: 4px 8px;
    color: {C_TEXT_PRIMARY};
    font-size: 11px;
}}

/* ----  Menu  ---- */
QMenu {{
    background-color: {C_BG_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {C_BG_HOVER};
}}

/* ----  Message Box  ---- */
QMessageBox {{
    background-color: {C_BG_PANEL};
}}

QMessageBox QLabel {{
    color: {C_TEXT_PRIMARY};
}}

/* ----  Project Badge  ---- */
QWidget#project_badge {{
    background-color: {C_BG_CARD};
    border: 1px solid {C_BORDER_LIGHT};
    border-radius: 6px;
    padding: 3px 10px;
}}

QWidget#project_badge QLabel {{
    color: {C_TEXT_SECONDARY};
    font-size: 11px;
}}

/* ----  Icon labels for technique nav ---- */
QLabel#tech_icon {{
    font-size: 18px;
    padding: 0;
}}

QLabel#tech_desc {{
    color: {C_TEXT_MUTED};
    font-size: 10px;
    padding-left: 24px;
}}
"""

# ── Technique-specific button style helper ────────────────────────────────

def nav_button_style(technique: str, checked: bool = False) -> str:
    """Return dynamic QSS for a technique navigation button."""
    accent = TECHNIQUE_COLORS.get(technique, C_ACCENT_WAXS)
    if checked:
        return (
            f"QPushButton {{"
            f"  background-color: {C_BG_CARD};"
            f"  border: none;"
            f"  border-left: 3px solid {accent};"
            f"  border-radius: 6px;"
            f"  text-align: left;"
            f"  padding: 8px 16px;"
            f"  margin: 2px 8px;"
            f"  color: {C_TEXT_PRIMARY};"
            f"  font-weight: 600;"
            f"  font-size: 13px;"
            f"}}"
        )
    return (
        f"QPushButton {{"
        f"  background: transparent;"
        f"  border: none;"
        f"  border-radius: 6px;"
        f"  text-align: left;"
        f"  padding: 8px 16px;"
        f"  margin: 2px 8px;"
        f"  color: {C_TEXT_SECONDARY};"
        f"  font-size: 13px;"
        f"}}"
        f"QPushButton:hover {{"
        f"  background-color: {C_BG_HOVER};"
        f"  color: {C_TEXT_PRIMARY};"
        f"}}"
    )


def technique_accent_style(technique: str) -> str:
    """Return accent colour for a technique."""
    return TECHNIQUE_COLORS.get(technique, C_ACCENT_WAXS)

# ── Missing from original D:\PolyNexus styles.py (restored) ──

def get_chart_colors(n=None):
    """Return a cycle of chart colors."""
    from matplotlib import colormaps
    colors = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b',
              '#e377c2','#7f7f7f','#bcbd22','#17becf']
    if n is None:
        return colors
    return colors[:n]

def nav_button_style(accent_color=None):
    """Return inline stylesheet for navigation buttons."""
    return ""

# Also ensure TECHNIQUE_LABELS and TECHNIQUE_ICONS exist
if "TECHNIQUE_LABELS" not in dir():
    TECHNIQUE_LABELS = {"saxs":"SAXS","waxs":"WAXS","dsc":"DSC","ir":"IR","nmr":"NMR"}

if "TECHNIQUE_ICONS" not in dir():
    TECHNIQUE_ICONS = {"saxs":"","waxs":"","dsc":"","ir":"","nmr":""}
