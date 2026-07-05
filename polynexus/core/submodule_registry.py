"""SubModule declaration and registry for PolyNexus v2.0.

Each analysis technique (SAXS, WAXS, DSC, IR, NMR) registers its
experimental sub-modules (static, strain, temperature, etc.) via
@register_submodule decorators.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

@dataclass
class SubModuleSpec:
    id: str
    parent_technique: str
    label: str
    icon: str = ""
    description: str = ""
    priority: int = 0
    required_polymer_families: list[str] = field(default_factory=list)
    config_schema: dict = field(default_factory=dict)
    accepted_formats: list[str] = field(default_factory=list)
    input_mode: str = "single"
    detect_experiment_type: Optional[Callable] = None
    output_parameters: list[dict] = field(default_factory=list)
    figure_types: list[str] = field(default_factory=list)

SUBMODULE_REGISTRY: dict[str, list[SubModuleSpec]] = {}

def register_submodule(spec: SubModuleSpec):
    def decorator(cls):
        tech = spec.parent_technique
        if tech not in SUBMODULE_REGISTRY:
            SUBMODULE_REGISTRY[tech] = []
        SUBMODULE_REGISTRY[tech].append(spec)
        return cls
    return decorator

def get_submodule_registry():
    return SUBMODULE_REGISTRY

def list_all_submodules():
    result = []
    for tech, specs in SUBMODULE_REGISTRY.items():
        for spec in sorted(specs, key=lambda s: s.priority, reverse=True):
            result.append({
                'technique': tech, 'id': spec.id, 'label': spec.label,
                'icon': spec.icon, 'description': spec.description,
                'priority': spec.priority,
                'config_schema': spec.config_schema,
                'output_parameters': spec.output_parameters,
                'figure_types': spec.figure_types,
            })
    return result

def detect_submodule(technique: str, filepath: str) -> Optional[str]:
    specs = SUBMODULE_REGISTRY.get(technique, [])
    candidates = []
    for spec in specs:
        if spec.detect_experiment_type is not None:
            r = spec.detect_experiment_type(filepath)
            if r is not None:
                candidates.append((spec.priority, spec.id))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]
