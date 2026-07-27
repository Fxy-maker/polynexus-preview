from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable

from ..core.preprocess_optimization import stable_config_hash
from ..core.saxs_engine.saxs_ai_rescue import SAXSConfirmedRerunAudit
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
    technique: str = ""
    mode: str = "static"
    candidate_id: str = ""
    candidate_base_config_hash: str = ""
    apply_performed: bool = False
    audit: dict[str, Any] = field(default_factory=dict)
    persistence_error: str = ""


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
        technique: str = "",
        mode_provider: Callable[[], str] | None = None,
        validate_confirmation: Callable[..., dict[str, Any]] | None = None,
        validate_rerun: Callable[[Any], dict[str, Any]] | None = None,
        record_audit: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._capture_config = capture_config
        self._apply_config = apply_config
        self._get_result = get_result
        self._set_result = set_result
        self._rerun = rerun
        self._persist_experience = persist_experience
        self._revoke_experience = revoke_experience
        self._technique = str(technique or "").strip().upper()
        self._mode_provider = mode_provider
        self._validate_confirmation = validate_confirmation
        self._validate_rerun = validate_rerun
        self._record_audit = record_audit
        self.state = PreprocessTransactionState()

    @staticmethod
    def _report_config(report: object, key: str) -> dict[str, Any]:
        if not isinstance(report, dict):
            return {}
        value = report.get(key, {})
        return deepcopy(value) if isinstance(value, dict) else {}

    def _mode(self, report: object) -> str:
        if isinstance(report, dict) and report.get("mode"):
            return str(report.get("mode")).strip().lower()
        if callable(self._mode_provider):
            try:
                return str(self._mode_provider() or "static").strip().lower()
            except Exception:
                return "static"
        return "static"

    def _emit_audit(self, payload: dict[str, Any]) -> None:
        detached = deepcopy(payload)
        self.state.audit = detached
        if callable(self._record_audit):
            try:
                self._record_audit(deepcopy(detached))
            except Exception:
                pass

    def _new_audit(self, **overrides: Any) -> dict[str, Any]:
        payload = SAXSConfirmedRerunAudit.now(
            technique=self.state.technique or "preprocess",
            mode=self.state.mode,
            candidate_id=self.state.candidate_id,
            candidate_base_config_hash=self.state.candidate_base_config_hash,
            before_config_hash=stable_config_hash(self.state.previous_config),
            accepted_by=self.state.accepted_by,
            **overrides,
        ).to_dict()
        self._emit_audit(payload)
        return payload

    def _is_saxs(self) -> bool:
        return self._technique == "SAXS"

    def begin_confirmation(self, report: object, *, accepted_by: str) -> bool:
        if self.state.phase in {"apply_pending", "undo_pending"}:
            return False
        view = build_preprocess_ui_decision(report)
        selected = deepcopy(view.selected_config)
        if view.mode != "confirm" or not selected:
            return False
        original_config = self._report_config(report, "original_preprocess_config")
        capture_keys = list(original_config) or list(selected)
        previous_config = self._capture_config(capture_keys)
        mode = self._mode(report)
        confirmation_metadata: dict[str, Any] = {}
        if self._is_saxs():
            if not callable(self._validate_confirmation):
                return False
            try:
                confirmation_metadata = self._validate_confirmation(
                    report,
                    current_config=previous_config,
                    mode=mode,
                )
            except (TypeError, ValueError):
                return False
        self.state = PreprocessTransactionState(
            phase="apply_pending",
            technique=self._technique,
            mode=mode,
            selected_config=selected,
            previous_config=deepcopy(previous_config),
            previous_result=self._get_result(),
            proposal=self._report_config(report, "experience_proposal"),
            accepted_by=str(accepted_by or "user_confirmed"),
            candidate_id=str(confirmation_metadata.get("candidate_id", "") or ""),
            candidate_base_config_hash=str(
                confirmation_metadata.get("candidate_base_config_hash", "") or ""
            ),
        )
        before_assessment: dict[str, Any] | None = None
        if callable(self._validate_rerun):
            try:
                before_assessment = self._validate_rerun(
                    self.state.previous_result,
                    mode=self.state.mode,
                )
            except TypeError:
                before_assessment = self._validate_rerun(self.state.previous_result)
            except Exception:
                before_assessment = None
        self._new_audit(
            phase="apply_pending",
            before_quality_evidence=before_assessment,
        )
        try:
            self._apply_config(selected)
            self._rerun()
        except Exception as exc:
            self.rollback_failure(reason=f"rerun_exception:{type(exc).__name__}")
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
        self.state.apply_performed = True
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
            if not self.state.experience_id:
                self.state.persistence_error = "experience_persistence_failed"
        except Exception as exc:
            self.state.experience_id = ""
            self.state.persistence_error = f"experience_persistence_failed:{type(exc).__name__}"

    def finalize_success(self, result: Any = None) -> bool:
        if self.state.phase == "apply_pending":
            selected_result = self._get_result() if result is None else result
            assessment: dict[str, Any] = {
                "accepted": True,
                "physical_gate_status": "unavailable",
                "quality_gate_status": "unavailable",
            }
            if callable(self._validate_rerun):
                try:
                    assessment = self._validate_rerun(selected_result, mode=self.state.mode)
                except TypeError:
                    assessment = self._validate_rerun(selected_result)
                except Exception as exc:
                    self.rollback_failure(reason=f"rerun_validation_exception:{type(exc).__name__}")
                    return False
                if not isinstance(assessment, dict) or not bool(assessment.get("accepted")):
                    reason = "post_rerun_gate_failed"
                    if isinstance(assessment, dict):
                        reason_codes = assessment.get("reason_codes", [])
                        if reason_codes:
                            reason = f"post_rerun_gate_failed:{reason_codes[0]}"
                    self.rollback_failure(reason=reason, assessment=assessment)
                    return False
            current_config = self._capture_config(list(self.state.selected_config))
            if stable_config_hash(current_config) != stable_config_hash(self.state.selected_config):
                self.rollback_failure(reason="selected_config_hash_mismatch", assessment=assessment)
                return False
            self._persist_pending_experience()
            self.state.selected_result = selected_result
            self.state.apply_performed = True
            self.state.phase = "applied"
            self._new_audit(
                phase="applied",
                after_config_hash=stable_config_hash(current_config),
                apply_performed=True,
                physical_gate_status=str(assessment.get("physical_gate_status", "unavailable")),
                quality_gate_status=str(assessment.get("quality_gate_status", "unavailable")),
                after_quality_evidence=assessment,
                rollback_reason=self.state.persistence_error,
            )
            return True
        elif self.state.phase == "undo_pending":
            selected_result = self._get_result() if result is None else result
            assessment: dict[str, Any] = {"accepted": True}
            if callable(self._validate_rerun):
                try:
                    assessment = self._validate_rerun(selected_result, mode=self.state.mode)
                except TypeError:
                    assessment = self._validate_rerun(selected_result)
                except Exception:
                    self.rollback_failure(reason="undo_validation_exception")
                    return False
                if not isinstance(assessment, dict) or not bool(assessment.get("accepted")):
                    self.rollback_failure(reason="undo_post_rerun_gate_failed", assessment=assessment)
                    return False
            experience_id = self.state.experience_id
            if experience_id:
                try:
                    revoked = self._revoke_experience(experience_id)
                    revoke_error = "" if revoked else "experience_revoke_failed"
                except Exception as exc:
                    revoke_error = f"experience_revoke_failed:{type(exc).__name__}"
            else:
                revoke_error = ""
            self.state.phase = "undone"
            self.state.apply_performed = False
            self._new_audit(
                phase="undone",
                after_config_hash=stable_config_hash(self.state.previous_config),
                apply_performed=False,
                physical_gate_status=str(assessment.get("physical_gate_status", "unavailable")),
                quality_gate_status=str(assessment.get("quality_gate_status", "unavailable")),
                after_quality_evidence=assessment,
                rollback_reason=revoke_error,
            )
            return True
        return False

    def rollback_failure(
        self,
        *,
        reason: str = "rerun_failed",
        assessment: dict[str, Any] | None = None,
    ) -> None:
        if self.state.phase == "apply_pending":
            restore_error = ""
            try:
                self._apply_config(deepcopy(self.state.previous_config))
                self._set_result(self.state.previous_result)
            except Exception as exc:
                restore_error = f"restore_failed:{type(exc).__name__}"
            finally:
                self.state.phase = "failed"
                self.state.apply_performed = False
                assessment = assessment if isinstance(assessment, dict) else {}
                self._new_audit(
                    phase="failed" if restore_error else ("rolled_back" if reason.startswith("post_rerun") or "gate" in reason else "failed"),
                    after_config_hash=stable_config_hash(self.state.previous_config),
                    apply_performed=False,
                    physical_gate_status=str(assessment.get("physical_gate_status", "unavailable")),
                    quality_gate_status=str(assessment.get("quality_gate_status", "unavailable")),
                    after_quality_evidence=assessment or None,
                    rollback_reason=restore_error or reason,
                )
        elif self.state.phase == "undo_pending":
            restore_error = ""
            try:
                self._apply_config(deepcopy(self.state.selected_config))
                self._set_result(self.state.selected_result)
            except Exception as exc:
                restore_error = f"restore_failed:{type(exc).__name__}"
            finally:
                self.state.phase = "failed" if restore_error else "applied"
                self.state.apply_performed = not bool(restore_error)
                self._new_audit(
                    phase="failed" if restore_error else "applied",
                    after_config_hash=stable_config_hash(self.state.selected_config),
                    apply_performed=not bool(restore_error),
                    rollback_reason=restore_error or reason,
                )

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
        except Exception as exc:
            self.rollback_failure(reason=f"undo_rerun_exception:{type(exc).__name__}")
            return False
        return True
