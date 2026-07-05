"""PolyNexus analysis engines - auto-discovers all techniques."""

from .engine import (
    BaseEngine, AnalysisResult, EngineCategory,
    register_technique, get_engine, list_techniques,
)
from .analysis_evidence import AnalysisEvidence, build_analysis_evidence

# Import all technique modules to trigger @register_technique decorators
from . import saxs
from . import waxs
from . import dsc
from . import ir
from . import nmr
from . import joint

__all__ = [
    "BaseEngine", "AnalysisResult", "EngineCategory",
    "register_technique", "get_engine", "list_techniques",
    "AnalysisEvidence", "build_analysis_evidence",
]

from .report import generate_report, save_report

# ── SubModule v2.0 exports ──
from .submodule_registry import (
    SubModuleSpec, register_submodule,
    get_submodule_registry, list_all_submodules, detect_submodule,
)

__all__ += [
    "SubModuleSpec", "register_submodule",
    "get_submodule_registry", "list_all_submodules", "detect_submodule",
]
