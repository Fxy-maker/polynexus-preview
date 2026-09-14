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
from .validation_harness import (
    ValidationCase,
    ValidationExpectation,
    ValidationReport,
    run_validation,
)
from .public_validation import (
    PublicReplayCase,
    load_public_validation_manifest,
    public_canonical_dataset_id,
    public_source_artifact_id,
    run_public_validation_case,
    run_public_validation_manifest,
)
from .validation_suite import (
    ValidationSuiteEntry,
    ValidationSuiteReport,
    build_validation_suite_report,
)

# Import all technique modules to trigger @register_technique decorators
from . import saxs  # noqa: F401
from . import waxs  # noqa: F401
from . import dsc  # noqa: F401
from . import ir  # noqa: F401
from . import nmr  # noqa: F401
from . import tga  # noqa: F401
from . import tga_validation  # noqa: F401
from . import dma  # noqa: F401
from . import rheology  # noqa: F401
from . import sec  # noqa: F401
from . import mechanics  # noqa: F401
from . import joint  # noqa: F401

__all__ = [
    "BaseEngine", "AnalysisResult", "EngineCategory",
    "register_technique", "get_engine", "list_techniques",
    "AnalysisEvidence", "build_analysis_evidence",
    "REVIEW_SCOPES", "REVIEW_STATUSES", "ReviewPromotionDecision",
    "ScientificReviewRecord", "promotion_decision", "review_decision_snapshot",
    "review_record_from_payload", "validate_review_record",
    "ValidationCase", "ValidationExpectation", "ValidationReport", "run_validation",
    "PublicReplayCase", "load_public_validation_manifest",
    "public_canonical_dataset_id", "public_source_artifact_id",
    "run_public_validation_case", "run_public_validation_manifest",
    "ValidationSuiteEntry", "ValidationSuiteReport",
    "build_validation_suite_report",
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
