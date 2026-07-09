from __future__ import annotations

from .analysis_evidence_constraint_inventory_dsc import _dsc_constraint_inventory
from .analysis_evidence_constraint_inventory_ir import _ir_constraint_inventory
from .analysis_evidence_constraint_inventory_nmr import _nmr_constraint_inventory
from .analysis_evidence_constraint_inventory_saxs import _saxs_constraint_inventory
from .analysis_evidence_constraint_inventory_waxs import _waxs_constraint_inventory
from .analysis_evidence_constraint_models import EvidenceConstraint, _inventory


def physical_constraint_inventory(technique: str) -> list[EvidenceConstraint]:
    key = str(technique or "").upper()
    if key == "SAXS":
        return _saxs_constraint_inventory()
    if key == "DSC":
        return _dsc_constraint_inventory()
    if key == "WAXS":
        return _waxs_constraint_inventory()
    if key == "IR":
        return _ir_constraint_inventory()
    if key == "NMR":
        return _nmr_constraint_inventory()
    return []
