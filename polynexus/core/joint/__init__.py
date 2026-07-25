"""Cross-technique joint analysis coordinator (v2.0).

Joint analysis for multi-technique polymer characterization:
Phase A: extended comparison charts
Phase C: linked timeline (future)
Phase B: joint fitting models (future)
"""

from .coordinator import JointCoordinator
from .figure_provider import build_joint_figure_definitions
from .dataset import (
    JointBatchRow,
    JointRunRecord,
    build_joint_hub_report,
    collect_joint_dataset,
    detect_joint_opportunities,
)

__all__ = [
    "JointCoordinator",
    "build_joint_figure_definitions",
    "JointBatchRow",
    "JointRunRecord",
    "build_joint_hub_report",
    "collect_joint_dataset",
    "detect_joint_opportunities",
]
