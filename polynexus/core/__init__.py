"""PolyNexus analysis engines - auto-discovers all techniques."""

from .engine import (
    BaseEngine, AnalysisResult, EngineCategory,
    register_technique, get_engine, list_techniques,
)
from .analysis_evidence import AnalysisEvidence, build_analysis_evidence
from .scientific_review import (
    REVIEW_SCOPES,
    REVIEW_STATUSES,
    ReviewPromotionDecision,
    ScientificReviewRecord,
    promotion_decision,
    review_decision_snapshot,
    review_record_from_payload,
    validate_review_record,
)

# Import all technique modules to trigger @register_technique decorators
from . import saxs  # noqa: F401
from . import waxs  # noqa: F401
from . import dsc  # noqa: F401
from . import ir  # noqa: F401
from . import nmr  # noqa: F401
from . import joint  # noqa: F401

__all__ = [
    "BaseEngine", "AnalysisResult", "EngineCategory",
    "register_technique", "get_engine", "list_techniques",
    "AnalysisEvidence", "build_analysis_evidence",
    "REVIEW_SCOPES", "REVIEW_STATUSES", "ReviewPromotionDecision",
    "ScientificReviewRecord", "promotion_decision", "review_decision_snapshot",
    "review_record_from_payload", "validate_review_record",
]

from .report import generate_report, save_report  # noqa: F401

# ── SubModule v2.0 exports ──
from .submodule_registry import (
    SubModuleSpec, register_submodule,
    get_submodule_registry, list_all_submodules, detect_submodule,
)

__all__ += [
    "SubModuleSpec", "register_submodule",
    "get_submodule_registry", "list_all_submodules", "detect_submodule",
]
