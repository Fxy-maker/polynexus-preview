from __future__ import annotations

from .orchestrator_priority_rules_dsc import (
    GOAL_TUNING_PRIORITY_RULES_DSC,
    JOINT_TUNING_PRIORITY_RULES_DSC,
)
from .orchestrator_priority_rules_ir import (
    GOAL_TUNING_PRIORITY_RULES_IR,
    JOINT_TUNING_PRIORITY_RULES_IR,
)
from .orchestrator_priority_rules_nmr import (
    GOAL_TUNING_PRIORITY_RULES_NMR,
    JOINT_TUNING_PRIORITY_RULES_NMR,
)
from .orchestrator_priority_rules_saxs import (
    GOAL_TUNING_PRIORITY_RULES_SAXS,
    JOINT_TUNING_PRIORITY_RULES_SAXS,
)
from .orchestrator_priority_rules_waxs import (
    GOAL_TUNING_PRIORITY_RULES_WAXS,
    JOINT_TUNING_PRIORITY_RULES_WAXS,
)

JOINT_TUNING_PRIORITY_RULES: dict[str, dict[str, list[tuple[str, str]]]] = {
    "WAXS": JOINT_TUNING_PRIORITY_RULES_WAXS,
    "DSC": JOINT_TUNING_PRIORITY_RULES_DSC,
    "SAXS": JOINT_TUNING_PRIORITY_RULES_SAXS,
    "IR": JOINT_TUNING_PRIORITY_RULES_IR,
    "NMR": JOINT_TUNING_PRIORITY_RULES_NMR,
}

GOAL_TUNING_PRIORITY_RULES: dict[str, dict[str, list[tuple[str, str]]]] = {
    "WAXS": GOAL_TUNING_PRIORITY_RULES_WAXS,
    "SAXS": GOAL_TUNING_PRIORITY_RULES_SAXS,
    "DSC": GOAL_TUNING_PRIORITY_RULES_DSC,
    "IR": GOAL_TUNING_PRIORITY_RULES_IR,
    "NMR": GOAL_TUNING_PRIORITY_RULES_NMR,
}
