from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable

from .preprocess_decision_service import build_preprocess_ui_decision


@dataclass
class PreprocessTransactionState:
    phase: str = "idle"
    technique: str = ""
    previous_config: dict[str, Any] = field(default_factory=dict)
    selected_config: dict[str, Any] = field(default_factory=dict)
    previous_result: Any = None
    selected_result: Any = None
    proposal: dict[str, Any] = field(default_factory=dict)
    accepted_by: str = ""
    experience_id: str = ""


class PreprocessTransactionService:
    def __init__(
        self,
        *,
        capture_config: Callable[[list[str]], dict[str, Any]],
        apply_config: Callable[[dict[str, Any]], None],
        get_result: Callable[[], Any],
        set_result: Callable[[Any], None],
        rerun: Callable[[], None],
        persist_experience: Callable[[dict[str, Any], str], str],
        revoke_experience: Callable[[str], bool],
    ) -> None:
        self._capture_config = capture_config
        self._apply_config = apply_config
        self._get_result = get_result
        self._set_result = set_result
        self._rerun = rerun
        self._persist_experience = persist_experience
        self._revoke_experience = revoke_experience
        self.state = PreprocessTransactionState()

    @staticmethod
    def _report_config(report: object, key: str) -> dict[str, Any]:
        if not isinstance(report, dict):
            return {}
        value = report.get(key, {})
        return deepcopy(value) if isinstance(value, dict) else {}

    def begin_confirmation(self, report: object, *, accepted_by: str) -> bool:
        view = build_preprocess_ui_decision(report)
        selected = deepcopy(view.selected_config)
        if view.mode != "confirm" or not selected:
            return False
        previous_config = self._capture_config(list(selected))
        self.state = PreprocessTransactionState(
            phase="apply_pending",
            selected_config=selected,
            previous_config=deepcopy(previous_config),
            previous_result=self._get_result(),
            proposal=self._report_config(report, "experience_proposal"),
            accepted_by=str(accepted_by or "user_confirmed"),
        )
        try:
            self._apply_config(selected)
            self._rerun()
        except Exception:
            self.rollback_failure()
            return False
        return True

    def register_auto_accept(
        self,
        report: object,
        *,
        previous_config: dict[str, Any] | None = None,
        previous_result: Any = None,
    ) -> bool:
        view = build_preprocess_ui_decision(report)
        selected = deepcopy(view.selected_config)
        if view.mode != "auto_apply" or not selected:
            return False
        original = deepcopy(previous_config or self._report_config(report, "original_preprocess_config"))
        if not original:
            return False
        self.state = PreprocessTransactionState(
            phase="applied",
            previous_config=original,
            selected_config=selected,
            previous_result=previous_result,
            selected_result=self._get_result(),
            proposal=self._report_config(report, "experience_proposal"),
            accepted_by="auto_accept",
        )
        self._persist_pending_experience()
        return True

    def _persist_pending_experience(self) -> None:
        proposal = self.state.proposal
        if not proposal:
            return
        try:
            self.state.experience_id = str(
                self._persist_experience(
                    proposal,
                    accepted_by=self.state.accepted_by,
                )
                or ""
            )
        except Exception:
            self.state.experience_id = ""

    def finalize_success(self) -> None:
        if self.state.phase == "apply_pending":
            self._persist_pending_experience()
            self.state.selected_result = self._get_result()
            self.state.phase = "applied"
        elif self.state.phase == "undo_pending":
            experience_id = self.state.experience_id
            if experience_id:
                try:
                    self._revoke_experience(experience_id)
                except Exception:
                    pass
            self.state.phase = "undone"

    def rollback_failure(self) -> None:
        if self.state.phase == "apply_pending":
            try:
                self._apply_config(deepcopy(self.state.previous_config))
                self._set_result(self.state.previous_result)
            finally:
                self.state.phase = "failed"
        elif self.state.phase == "undo_pending":
            try:
                self._apply_config(deepcopy(self.state.selected_config))
                self._set_result(self.state.selected_result)
            finally:
                self.state.phase = "applied"

    def undo(self) -> bool:
        if self.state.phase != "applied" or not self.state.previous_config:
            return False
        self.state.selected_config = self._capture_config(
            list(self.state.selected_config)
        )
        self.state.selected_result = self._get_result()
        self.state.phase = "undo_pending"
        try:
            self._apply_config(deepcopy(self.state.previous_config))
            self._rerun()
        except Exception:
            self.rollback_failure()
            return False
        return True
