"""Shared AI platform data contracts."""

from .contracts import (
    AxisProvenance,
    CapabilityResultStatus,
    CalibrationRef,
    ComputationState,
    DataBlock,
    MissingnessPolicy,
    UncertaintyRef,
    axis_allows_quantitative,
    canonical_json_hash,
)
from .capabilities import (
    CapabilityDescriptor,
    CapabilityDescriptorRegistry,
    default_descriptor_registry,
    descriptor_from_capability_spec,
    descriptor_from_provider_spec,
    normalize_technique,
)
from .planner import CapabilityPlanItem, CapabilityPlanner, PLAN_OUTCOMES
from .execution import (
    ExecutionContext,
    ExecutionGraph,
    ExecutionNode,
    ExecutionResult,
    GraphResult,
    NodeResult,
)

__all__ = [
    "DataBlock",
    "AxisProvenance",
    "CalibrationRef",
    "UncertaintyRef",
    "MissingnessPolicy",
    "ComputationState",
    "CapabilityResultStatus",
    "canonical_json_hash",
    "axis_allows_quantitative",
    "CapabilityDescriptor",
    "CapabilityDescriptorRegistry",
    "default_descriptor_registry",
    "descriptor_from_capability_spec",
    "descriptor_from_provider_spec",
    "normalize_technique",
    "CapabilityPlanItem",
    "CapabilityPlanner",
    "PLAN_OUTCOMES",
    "ExecutionContext",
    "ExecutionNode",
    "NodeResult",
    "ExecutionResult",
    "GraphResult",
    "ExecutionGraph",
]
