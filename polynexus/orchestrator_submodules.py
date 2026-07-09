from __future__ import annotations

from typing import Any


def _submodule_id(self: Any) -> str:
    if self.submodule_override:
        return self._canonical_submodule_id(self.submodule_override)
    if self.technique == "dsc":
        return "dsc.standard"
    if self.technique == "saxs":
        return "saxs.static"
    if self.technique == "ir":
        if self._engine is not None:
            active_submodule = str(getattr(self._engine, "active_submodule", "") or "").strip()
            if active_submodule:
                return self._canonical_submodule_id(active_submodule)
        return "ir.standard"
    if self.technique == "nmr":
        return self._nmr_submodule_id()
    if self.technique == "waxs":
        return self._waxs_submodule_id()
    return "waxs.static"


def _submodule_name(self: Any) -> str:
    if self.technique == "ir":
        submodule_id = self._submodule_id()
        if submodule_id == "ir.temperature_2d":
            return "temperature_2d"
        return "standard"
    if self.technique == "dsc":
        return "standard"
    if self.technique == "nmr":
        return self._nmr_submodule_id().split(".", 1)[1]
    if self.technique == "waxs":
        return self._public_submodule().split(".", 1)[1]
    return "static"


def _public_submodule(self: Any) -> str:
    submodule_id = self._submodule_id()
    if self.technique == "waxs":
        mapping = {
            "waxs.temperature": "waxs.in_situ_temp",
            "waxs.strain": "waxs.in_situ_stretch",
            "waxs.static": "waxs.static",
        }
        return mapping.get(submodule_id, submodule_id)
    if self.technique == "nmr":
        return submodule_id
    if self.technique == "ir":
        if submodule_id == "ir.temperature_2d":
            return submodule_id
        return "standard"
    if self.technique == "dsc":
        return "standard"
    return submodule_id


def _agent_state_submodule(self: Any) -> str:
    if self.technique == "ir":
        submodule_id = self._submodule_id()
        if submodule_id == "ir.temperature_2d":
            return submodule_id
        return "standard"
    if self.technique == "dsc":
        return "standard"
    return self._public_submodule()
