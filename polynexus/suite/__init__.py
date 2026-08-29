"""PolyNexus Research Suite integration services."""

from .contracts import SuiteComponent, SuiteManifest, SuiteStatus, SuiteComponentStatus
from .manager import SuiteManager
from .paper_contracts import (
    CONTRACT_VERSION,
    ClaimRecord,
    CitationRequest,
    FigurePlan,
    InputRequest,
    ManuscriptSource,
    PaperBrief,
    PreflightReport,
    stable_id,
)

__all__ = [
    "SuiteComponent",
    "SuiteManifest",
    "SuiteStatus",
    "SuiteComponentStatus",
    "SuiteManager",
    "CONTRACT_VERSION",
    "InputRequest",
    "PaperBrief",
    "ClaimRecord",
    "FigurePlan",
    "CitationRequest",
    "ManuscriptSource",
    "PreflightReport",
    "stable_id",
]
