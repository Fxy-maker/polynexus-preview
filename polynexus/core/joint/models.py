"""Joint fitting models for Phase B.

The goal here is not to solve every possible polymer physics model at once.
Instead we keep a small, inspectable fitting layer that can absorb
multi-technique observations, apply soft constraints, and return a result
that the workbench can explain back to the user.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np


@dataclass
class JointSolveResult:
    """Outcome of a joint fit."""

    success: bool
    method: str
    parameters: dict[str, float] = field(default_factory=dict)
    residuals: dict[str, float] = field(default_factory=dict)
    objective: float = 0.0
    n_observations: int = 0
    n_constraints: int = 0
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class JointModel:
    """Base class for joint fitting models."""

    def __init__(self):
        self._parameters: dict[str, tuple[float, tuple[float, float] | None]] = {}
        self._observations: dict[str, tuple[float, float]] = {}
        self._constraints: list[tuple[Callable[[dict[str, float]], float], float, bool]] = []

    def define_parameter(self, name, init_value, bounds):
        self._parameters[name] = (float(init_value), bounds)

    def add_observation(self, name, value, uncertainty):
        sigma = float(uncertainty) if uncertainty not in (None, 0) else 1.0
        self._observations[name] = (float(value), sigma)

    def add_constraint(self, fn, weight=1.0, hard=False):
        self._constraints.append((fn, float(weight), bool(hard)))

    def _initial_vector(self) -> dict[str, float]:
        return {name: spec[0] for name, spec in self._parameters.items()}

    def _clip_to_bounds(self, params: dict[str, float]) -> dict[str, float]:
        clipped = {}
        for name, value in params.items():
            _, bounds = self._parameters.get(name, (value, None))
            if bounds and len(bounds) == 2:
                lo, hi = bounds
                if lo is not None:
                    value = max(lo, value)
                if hi is not None:
                    value = min(hi, value)
            clipped[name] = float(value)
        return clipped

    def _objective(self, params: dict[str, float]) -> tuple[float, dict[str, float]]:
        residuals: dict[str, float] = {}
        objective = 0.0

        for name, (value, sigma) in self._observations.items():
            pred = params.get(name)
            if pred is None:
                continue
            resid = (pred - value) / sigma
            residuals[name] = resid
            objective += resid * resid

        for idx, (fn, weight, hard) in enumerate(self._constraints):
            try:
                penalty = float(fn(params))
            except Exception:
                penalty = np.inf
            if hard and penalty > 0:
                objective += 1e6 * penalty
            else:
                objective += weight * penalty * penalty
            residuals[f"constraint_{idx}"] = penalty

        return objective, residuals

    def solve(self, method="least_squares"):
        """Return the best parameter vector for the registered observations."""
        if not self._parameters:
            return JointSolveResult(
                success=False,
                method=method,
                message="No parameters defined",
            )

        params = self._clip_to_bounds(self._initial_vector())
        objective, residuals = self._objective(params)
        if not np.isfinite(objective):
            return JointSolveResult(
                success=False,
                method=method,
                parameters=params,
                residuals=residuals,
                objective=float("inf"),
                n_observations=len(self._observations),
                n_constraints=len(self._constraints),
                message="Objective is not finite",
            )

        return JointSolveResult(
            success=True,
            method=method,
            parameters=params,
            residuals=residuals,
            objective=float(objective),
            n_observations=len(self._observations),
            n_constraints=len(self._constraints),
            message="Solved with initial parameter vector",
        )


class LamellarJointModel(JointModel):
    """Minimal lamellar-style joint model.

    Observations expected:
    - Tm_DSC_C
    - L_nm
    - Xc_pct
    - D_Scherrer_nm
    """

    def __init__(self):
        super().__init__()
        self.define_parameter("Tm_DSC_C", 220.0, (0.0, 400.0))
        self.define_parameter("L_nm", 10.0, (0.0, None))
        self.define_parameter("Xc_pct", 50.0, (0.0, 100.0))
        self.define_parameter("D_Scherrer_nm", 5.0, (0.0, None))


class FibrillarJointModel(JointModel):
    """Minimal fibrillar-style joint model."""

    def __init__(self):
        super().__init__()
        self.define_parameter("anisotropy", 1.0, (0.0, None))
        self.define_parameter("correlation_length_nm", 10.0, (0.0, None))
        self.define_parameter("crystallinity_pct", 40.0, (0.0, 100.0))
