"""
Base engine for all analysis techniques in PolyNexus.

Each technique (DSC, IR, WAXS, SAXS, NMR) inherits from BaseEngine
and implements: load(), preprocess(), analyze(), plot(), export().

New techniques register via TECHNIQUE_REGISTRY for auto-discovery
by the GUI and CLI.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
import numpy as np
import pandas as pd

from .analysis_evidence import AnalysisEvidence


logger = logging.getLogger("polynexus")
if not logger.handlers:
    handler = logging.FileHandler("polynexus.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def _build_supported_formats() -> dict[str, list[str]]:
    from .saxs_engine.io import SUPPORTED_1D_EXTENSIONS, SUPPORTED_2D_EXTENSIONS
    from .nmr_engine.io import NMR_EXTS

    saxs_formats = sorted(SUPPORTED_1D_EXTENSIONS | SUPPORTED_2D_EXTENSIONS)
    waxs_formats = sorted({".edf", ".tif", ".tiff", ".cbf", ".raw", ".dat", ".txt", ".csv", ".xlsx", ".chi", ".xy"})
    dsc_formats = sorted({".csv", ".txt", ".dat", ".001", ".asc", ".xls", ".xlsx"})
    ir_formats = sorted({".csv", ".txt", ".dat", ".asc", ".prn", ".spa", ".dpt"})
    nmr_formats = sorted(set(NMR_EXTS) | {"fid"})
    return {
        "saxs": saxs_formats,
        "waxs": waxs_formats,
        "dsc": dsc_formats,
        "ir": ir_formats,
        "nmr": nmr_formats,
    }


SUPPORTED_FORMATS = _build_supported_formats()


def check_file_format(technique: str, filepath: str) -> None:
    """Raise ValueError when *filepath* is not supported by *technique*."""
    path = Path(filepath)
    if path.is_dir():
        return

    technique_key = (technique or "").lower()
    supported = SUPPORTED_FORMATS.get(technique_key, [])
    if not supported:
        return

    name = path.name.lower()
    ext = path.suffix.lower()
    if technique_key == "nmr" and name == "fid":
        return

    if ext not in supported:
        display_ext = ext or f"<no suffix: {path.name}>"
        raise ValueError(
            f"不支持的文件格式：{display_ext}\n"
            f"{technique_key.upper()} 支持的格式：{', '.join(supported)}"
        )


class EngineCategory(str, Enum):
    """Classification of engine by source and workflow.

    PolyNexus v1.0 unified architecture:
        - EXPERIMENTAL:  data-driven engines that process instrument measurements
        - COMPUTATIONAL: structure-driven engines that simulate spectra/properties
        - HYBRID:        engines that do both (experimental + DFT/MD comparison)
    """
    EXPERIMENTAL = "experimental"
    COMPUTATIONAL = "computational"
    HYBRID = "hybrid"


@dataclass
class AnalysisResult:
    """Container for analysis results from any technique (v4.0 enhanced)."""
    # ── v4.0 validation infrastructure ──
    validation_passed: bool = True
    quality_flags: Dict[str, str] = field(default_factory=dict)
    validation_warnings: List[str] = field(default_factory=list)
    validation_summary: str = ""
    technique: str = ""
    category: EngineCategory = EngineCategory.EXPERIMENTAL
    parameters: Dict[str, Any] = field(default_factory=dict)
    dataframes: Dict[str, pd.DataFrame] = field(default_factory=dict)
    figures: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, np.ndarray] = field(default_factory=dict)
    metadata: Dict[str, str] = field(default_factory=dict)
    logs: list = field(default_factory=list)
    analysis_evidence: dict[str, Any] = field(default_factory=dict)
    effective_q_min: float = np.nan

    def to_dict(self) -> dict:
        return {
            'technique': self.technique,
            'category': self.category.value,
            'parameters': {k: (round(v, 6) if isinstance(v, float) else v)
                          for k, v in self.parameters.items()},
            'validation_passed': self.validation_passed,
            'quality_flags': self.quality_flags,
            'validation_warnings': self.validation_warnings,
            'validation_summary': self.validation_summary,
            'metadata': self.metadata,
            'analysis_evidence': self.analysis_evidence,
            'effective_q_min': self.effective_q_min,
            'logs': self.logs[-10:],
        }

    def set_analysis_evidence(self, evidence: AnalysisEvidence | dict[str, Any] | None) -> None:
        if evidence is None:
            self.analysis_evidence = {}
        elif isinstance(evidence, AnalysisEvidence):
            self.analysis_evidence = evidence.to_dict()
        else:
            self.analysis_evidence = dict(evidence)


@dataclass
class CurveOverride:
    """Override for a single curve (Line2D) in a figure."""
    color: Optional[str] = None
    linewidth: Optional[float] = None
    linestyle: Optional[str] = None
    marker: Optional[str] = None
    markersize: Optional[float] = None
    label: Optional[str] = None
    visible: Optional[bool] = None


@dataclass
class AxesOverride:
    """Override for a single subplot axes."""
    xlabel: Optional[str] = None
    ylabel: Optional[str] = None
    title: Optional[str] = None
    xlim: Optional[tuple] = None
    ylim: Optional[tuple] = None
    xscale: Optional[str] = None
    yscale: Optional[str] = None


@dataclass
class PlotEdits:
    """Persistent plot editing state for a single figure.

    Stored in AnalysisRun.plot_edits as JSON. Applied by
    BaseEngine._apply_edits() before figure save.
    """
    title: Optional[str] = None
    xlabel: Optional[str] = None
    ylabel: Optional[str] = None
    font_size: Optional[float] = None
    bg_color: Optional[str] = None
    grid_visible: Optional[bool] = None
    grid_alpha: Optional[float] = None
    spine_width: Optional[float] = None
    spine_color: Optional[str] = None
    tick_direction: Optional[str] = None
    curve_overrides: dict = field(default_factory=dict)  # str -> CurveOverride
    axes_overrides: dict = field(default_factory=dict)   # int -> AxesOverride

    def to_json(self) -> str:
        import json
        from dataclasses import asdict
        return json.dumps(asdict(self), default=str)

    @classmethod
    def from_json(cls, data: str) -> 'PlotEdits':
        import json
        if not data: return cls()
        d = json.loads(data)
        co = {k: CurveOverride(**v) for k, v in d.pop('curve_overrides', {}).items()}
        ao = {int(k): AxesOverride(**v) for k, v in d.pop('axes_overrides', {}).items()}
        return cls(**d, curve_overrides=co, axes_overrides=ao)


class BaseEngine(ABC):
    """Abstract base for all analysis engines.

    Subclass and implement the five pipeline methods.
    Register with TECHNIQUE_REGISTRY for auto-discovery.

    Example:
        @register_technique("my_technique")
        class MyEngine(BaseEngine):
            ...
    """

    name: str = "base"
    label: str = "Base"
    icon: str = "🔬"
    description: str = ""
    category: EngineCategory = EngineCategory.EXPERIMENTAL

    def __init__(self, config=None, log_fn: Optional[Callable] = None):
        self.config = config
        self.log_fn = log_fn or print
        self.result = AnalysisResult(technique=self.name, category=self.category)
        self.active_submodule = None  # v2.0: set by get_engine()

    def get_polymer_db(self, families: list[str] = None):
        """Return a MultiFamilyDB view filtered to the requested families.

        Falls back to the legacy PolymerDB if MultiFamilyDB is not yet available.
        """
        try:
            from ..data.db_manager import MultiFamilyDB
            return MultiFamilyDB(families=families)
        except ImportError:
            from ..data.db_manager import get_db
            return get_db()

    def _apply_edits(self, fig, edits: PlotEdits):
        """Apply PlotEdits to a matplotlib Figure in-place.

        Subclasses may override to handle technique-specific figure layouts.
        This default implementation iterates all axes and lines.
        """
        for i, ax in enumerate(fig.axes):
            ax_edit = edits.axes_overrides.get(i)
            if ax_edit:
                if ax_edit.xlabel: ax.set_xlabel(ax_edit.xlabel)
                if ax_edit.ylabel: ax.set_ylabel(ax_edit.ylabel)
                if ax_edit.title: ax.set_title(ax_edit.title)
                if ax_edit.xlim: ax.set_xlim(*ax_edit.xlim)
                if ax_edit.ylim: ax.set_ylim(*ax_edit.ylim)
                if ax_edit.xscale: ax.set_xscale(ax_edit.xscale)
                if ax_edit.yscale: ax.set_yscale(ax_edit.yscale)
            elif i == 0 and not edits.axes_overrides:
                # Legacy: global xlabel/ylabel/title apply to first axes
                if edits.xlabel: ax.set_xlabel(edits.xlabel)
                if edits.ylabel: ax.set_ylabel(edits.ylabel)
                if edits.title: ax.set_title(edits.title)

            for line in ax.lines:
                label = line.get_label()
                if label in edits.curve_overrides:
                    ov = edits.curve_overrides[label]
                    if ov.color: line.set_color(ov.color)
                    if ov.linewidth: line.set_linewidth(ov.linewidth)
                    if ov.linestyle: line.set_linestyle(ov.linestyle)
                    if ov.marker: line.set_marker(ov.marker)
                    if ov.markersize: line.set_markersize(ov.markersize)
                    if ov.label: line.set_label(ov.label)
                    if ov.visible is not None: line.set_visible(ov.visible)

            if edits.grid_visible is not None: ax.grid(edits.grid_visible, alpha=edits.grid_alpha or 0.2)
            for spine in ax.spines.values():
                if edits.spine_width: spine.set_linewidth(edits.spine_width)
                if edits.spine_color: spine.set_color(edits.spine_color)
            if edits.tick_direction: ax.tick_params(direction=edits.tick_direction)
            if edits.font_size: ax.tick_params(labelsize=edits.font_size)
            if edits.bg_color: ax.set_facecolor(edits.bg_color)

    def log(self, msg: str):
        self.result.logs.append(msg)
        line = f"[{self.name}] {msg}"
        try:
            self.log_fn(line)
        except UnicodeEncodeError:
            self.log_fn(line.encode("ascii", errors="replace").decode("ascii"))

    # ── v4.0 Validation infrastructure ──────────────────────────────────

    def add_quality_flag(self, param: str, flag: str):
        """Record a quality flag for a parameter.

        flag: 'OK' | 'WARN' | 'ERROR'.
        'ERROR' automatically sets validation_passed = False.
        """
        self.result.quality_flags[param] = flag
        if flag == "ERROR":
            self.result.validation_passed = False
            self.log(f"  [VALIDATION] {param} = ERROR")
        elif flag == "WARN":
            self.result.validation_warnings.append(param)
            self.log(f"  [VALIDATION] {param} = WARN")

    def _validate_results(self) -> bool:
        """Post-analysis validation hook.

        Subclasses override for technique-specific checks
        (range, cross-validation, SNR, etc.).
        Returns True if all checks pass.
        """
        return self.result.validation_passed

    # ── v4.0 Appendix B: polymer reference database ─────────────────────

    DHM0_REF: Dict[str, float] = {
        "PE": 293, "HDPE": 293, "LDPE": 293,
        "iPP": 207, "PP": 207, "sPP": 196,
        "PET": 140, "PBT": 145,
        "PA6": 230, "PA66": 255,
        "PTFE": 82, "PEEK": 130, "POM": 326, "PPS": 80,
        "PLA": 93, "PVDF": 105,
    }

    TG_BOUNDS: Dict[str, tuple] = {
        "PE": (-130, -80), "iPP": (-30, 0), "PS": (85, 110),
        "PET": (60, 85), "PA6": (35, 65), "PA66": (45, 75),
        "PTFE": (115, 135), "PMMA": (95, 125), "PC": (135, 155),
        "PEEK": (140, 155), "PVDF": (-45, -25), "PLA": (50, 70),
    }

    TM_BOUNDS: Dict[str, tuple] = {
        "PE": (100, 145), "iPP": (155, 175), "PET": (240, 270),
        "PA6": (210, 230), "PA66": (250, 270), "PTFE": (320, 345),
        "PEEK": (330, 348), "PVDF": (165, 185), "PLA": (145, 185),
        "PBT": (220, 235), "POM": (170, 185), "PPS": (275, 290),
    }

    SAXS_L_BOUNDS: tuple = (3.0, 150.0)
    WAXS_D_BOUNDS: tuple = (1.0, 1000.0)

    @abstractmethod
    def load(self, filepath: str) -> bool:
        """Load raw data from file(s). Return True on success."""
        ...

    @abstractmethod
    def preprocess(self) -> bool:
        """Preprocess: baseline, smooth, normalize. Return True on success."""
        ...

    @abstractmethod
    def analyze(self) -> bool:
        """Core analysis. Return True on success."""
        ...

    @abstractmethod
    def plot(self, output_dir: str = "") -> Dict[str, str]:
        """Generate figures. Returns {figure_name: filepath}."""
        ...

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return key analysis parameters as dict."""
        ...

    def check_file_compatibility(self, filepath: str) -> tuple[bool, str]:
        """Check if the selected file is compatible with this technique.

        Returns (ok, message).  Default implementation accepts all files.
        Subclasses should override for technique-specific validation.
        """
        import os
        # Check basic file existence
        if not os.path.exists(filepath):
            return False, f"File not found: {filepath}"
        # Default: accept all files
        return True, ""

    def run_pipeline(self, filepath: str, output_dir: str = "",                     skip_to: str | None = None) -> AnalysisResult:
        """Run full pipeline: load -> preprocess -> analyze -> plot.

        Parameters
        ----------
        skip_to : str or None
            If "plot", skip load/preprocess/analyze and only regenerate figures.
            Requires the engine to already hold cached data from a prior run.
        """
        self.log(f"Starting {self.label} analysis...")
        try:
            if skip_to != "plot":
                if not self.load(filepath):
                    self.log("ERROR: Failed to load data")
                    return self.result
                self.log(f"Data loaded successfully")

                if not self.preprocess():
                    self.log("ERROR: Preprocessing failed")
                    return self.result
                self.log("Preprocessing complete")

                if not self.analyze():
                    self.log("ERROR: Analysis failed")
                    return self.result
                self.log("Analysis complete")

                self.result.parameters = self.get_parameters()

            if output_dir:
                figures = self.plot(output_dir)
                if figures:
                    self.result.figures = figures
                self.log(f"Figures saved to {output_dir}")

            self.log(f"{self.label} analysis finished")
        except Exception as e:
            self.log(f"ERROR: {e}")
            import traceback
            self.log(traceback.format_exc())
            logger.warning("异常已处理", exc_info=True)

        # ── v4.0: post-analysis validation ──
        try:
            self._validate_results()
            if not self.result.validation_passed:
                self.log("⚠️  VALIDATION: errors detected — export blocked")
            elif self.result.validation_warnings:
                n = len(self.result.validation_warnings)
                self.log(f"⚠️  VALIDATION: {n} warning(s)")
            else:
                self.log("✅ VALIDATION: all checks passed")
        except Exception as e:
            self.log(f"⚠️  VALIDATION: internal error — {e}")
            self.result.validation_passed = False
            logger.warning("异常已处理", exc_info=True)

        return self.result

# ---------------------------------------------------------------------------
#  Technique registry for extensibility
# ---------------------------------------------------------------------------

TECHNIQUE_REGISTRY: Dict[str, type] = {}


def register_technique(name: str):
    """Decorator to register a technique engine."""
    def decorator(cls):
        TECHNIQUE_REGISTRY[name] = cls
        return cls
    return decorator


def get_engine(name: str, config=None, log_fn=None, submodule_id=None) -> Optional[BaseEngine]:
    """Factory: get an engine instance by technique name.

    If submodule_id is provided, sets engine.active_submodule to route
    the analysis pipeline to the correct sub-module.
    """
    cls = TECHNIQUE_REGISTRY.get(name)
    if cls is None:
        return None
    engine = cls(config=config, log_fn=log_fn)
    if submodule_id:
        engine.active_submodule = submodule_id
    return engine


def list_techniques() -> list:
    """List all registered techniques with metadata."""
    return [
        {'name': name, 'label': cls.label, 'icon': cls.icon,
         'description': cls.description,
         'category': getattr(cls, 'category', EngineCategory.EXPERIMENTAL).value}
        for name, cls in TECHNIQUE_REGISTRY.items()
    ]


# ── SubModule support (v2.0) ──
from .submodule_registry import (
    SubModuleSpec, SUBMODULE_REGISTRY,
    register_submodule, get_submodule_registry,
    list_all_submodules, detect_submodule,
)
