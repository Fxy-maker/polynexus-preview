from __future__ import annotations

from .analysis_evidence_action_hint_rules_dsc import ACTION_HINT_RULES_DSC
from .analysis_evidence_action_hint_rules_ir import ACTION_HINT_RULES_IR
from .analysis_evidence_action_hint_rules_nmr import ACTION_HINT_RULES_NMR
from .analysis_evidence_action_hint_rules_saxs import ACTION_HINT_RULES_SAXS
from .analysis_evidence_action_hint_rules_waxs import ACTION_HINT_RULES_WAXS

ACTION_HINT_MAPPING: dict[str, dict[str, tuple[list[str], list[str]]]] = {
    "WAXS": ACTION_HINT_RULES_WAXS,
    "SAXS": ACTION_HINT_RULES_SAXS,
    "DSC": ACTION_HINT_RULES_DSC,
    "IR": ACTION_HINT_RULES_IR,
    "NMR": ACTION_HINT_RULES_NMR,
}
