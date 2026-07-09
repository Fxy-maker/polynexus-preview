from __future__ import annotations

import math
import threading
from pathlib import Path
from typing import Any, Callable

from polynexus.orchestrator_models import RoundRecord


def __init__(
    self,
    technique: str,
    data_file: str,
    polymer_name: str,
    max_rounds: int = 5,
    advisor: "Advisor | None" = None,
    llm_settings: dict[str, Any] | None = None,
    project_root: str | Path | None = None,
    workspace_context: dict[str, Any] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    submodule_override: str | None = None,
    cancel_event: "threading.Event | None" = None,
):
    from polynexus import orchestrator as orchestrator_module

    if technique.lower() not in {"waxs", "dsc", "saxs", "ir", "nmr"}:
        raise ValueError("ParameterOrchestrator currently supports WAXS static, DSC standard, SAXS static, IR standard, and NMR partitions only.")
    self.technique = technique.lower()
    self.data_file = str(data_file)
    self.polymer_name = polymer_name
    self.max_rounds = max_rounds
    self.llm_settings = dict(llm_settings or {})
    self.advisor = advisor or orchestrator_module.Advisor(
        llm_client=orchestrator_module.create_llm_client(self.llm_settings)
    )
    self.project_root = Path(project_root).resolve() if project_root else Path.cwd()
    self.workspace_context = self._to_plain_value(workspace_context or {})
    self.progress_callback = progress_callback
    self.submodule_override = submodule_override
    self._cancel_event = cancel_event
    self.polymer_knowledge = orchestrator_module.load_polymer_knowledge(polymer_name)
    self.history: list[RoundRecord] = []

    self._engine = None
    self._best_config = None
    self._best_output: dict[str, Any] = {}
    self._best_record: RoundRecord | None = None
    self._best_r_squared = -math.inf
    self._best_eval_score = -math.inf
    self._baseline_r_squared = 0.0
    self._baseline_eval_score = 0.0


def _emit_progress(
    self,
    round_num: int,
    before_r_squared: float,
    after_r_squared: float,
    changes: dict[str, Any],
    status: str,
    error: str = "",
    converged: bool = False,
    target_symptom: str = "",
    symptom_summary: str = "",
) -> None:
    if self.progress_callback is None:
        return
    self.progress_callback(
        {
            "round_num": round_num,
            "max_rounds": self.max_rounds,
            "before_r_squared": before_r_squared,
            "after_r_squared": after_r_squared,
            "changes": self._to_plain_value(changes),
            "status": status,
            "error": error,
            "converged": converged,
            "target_symptom": target_symptom,
            "symptom_summary": symptom_summary,
        }
    )
