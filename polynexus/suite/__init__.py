"""PolyNexus Research Suite integration services."""

from .contracts import SuiteComponent, SuiteManifest, SuiteStatus, SuiteComponentStatus
from .manager import SuiteManager
from .paper_contracts import (
    CONTRACT_VERSION,
    ClaimRecord,
    CitationRequest,
    FormulaRecord,
    FigurePlan,
    InputRequest,
    ManuscriptSource,
    PaperBrief,
    PreflightReport,
    stable_id,
)
from .figure_plans import render_figure_plan
from .figure_quality import check_figure_quality, check_svg_quality
from .figure_review import rank_figure_candidates, save_review_decisions
from .paper_source import build_manuscript_source
from .citations import detect_zotero, export_bibliography, render_citations

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
    "FormulaRecord",
    "ManuscriptSource",
    "PreflightReport",
    "stable_id",
    "build_manuscript_source",
    "render_figure_plan",
    "check_figure_quality",
    "check_svg_quality",
    "rank_figure_candidates",
    "save_review_decisions",
    "detect_zotero",
    "render_citations",
    "export_bibliography",
]
