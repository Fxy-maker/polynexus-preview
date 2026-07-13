from __future__ import annotations

from copy import deepcopy

from polynexus.gui.preprocess_transaction_service import (
    PreprocessTransactionService,
)


class Harness:
    def __init__(self) -> None:
        self.config = {"smooth_window": 11}
        self.original_result = {"status": "original"}
        self.result = self.original_result
        self.apply_calls: list[dict[str, object]] = []
        self.persisted: list[tuple[str, str]] = []
        self.revoked: list[str] = []
        self.rerun_calls = 0
        self.fail_rerun = False
        self.service = PreprocessTransactionService(
            capture_config=self._capture_config,
            apply_config=self._apply_config,
            get_result=lambda: self.result,
            set_result=self._set_result,
            rerun=self._rerun,
            persist_experience=self._persist_experience,
            revoke_experience=self._revoke_experience,
        )

    def _capture_config(self, keys: list[str]) -> dict[str, object]:
        return {key: self.config[key] for key in keys if key in self.config}

    def _apply_config(self, config: dict[str, object]) -> None:
        self.apply_calls.append(deepcopy(config))
        self.config.update(config)

    def _set_result(self, result: object) -> None:
        self.result = result

    def _rerun(self) -> None:
        self.rerun_calls += 1
        if self.fail_rerun:
            raise RuntimeError("rerun failed")

    def _persist_experience(
        self,
        proposal: dict[str, object],
        *,
        accepted_by: str,
    ) -> str:
        experience_id = str(proposal["experience_id"])
        self.persisted.append((experience_id, accepted_by))
        return experience_id

    def _revoke_experience(self, experience_id: str) -> bool:
        self.revoked.append(experience_id)
        return True

    def report(self, decision: str = "request_confirmation") -> dict[str, object]:
        return {
            "preprocess_decision": {
                "decision": decision,
                "simulated_decision": decision,
                "confidence_band": "high" if decision == "auto_accept" else "medium",
            },
            "selected_preprocess_config": {"smooth_window": 15},
            "original_preprocess_config": {"smooth_window": 11},
            "experience_proposal": {
                "experience_id": "preprocess-c1",
                "config_delta": {"smooth_window": 15},
            },
        }


def test_confirmation_persists_experience_only_after_successful_rerun() -> None:
    harness = Harness()

    assert harness.service.begin_confirmation(
        harness.report(), accepted_by="user_confirmed"
    )
    assert harness.config == {"smooth_window": 15}
    assert harness.persisted == []
    assert harness.rerun_calls == 1

    harness.service.finalize_success()

    assert harness.persisted == [("preprocess-c1", "user_confirmed")]
    assert harness.service.state.phase == "applied"


def test_rerun_failure_restores_config_and_result_without_experience() -> None:
    harness = Harness()
    harness.fail_rerun = True

    assert harness.service.begin_confirmation(
        harness.report(), accepted_by="user_confirmed"
    ) is False

    assert harness.config == {"smooth_window": 11}
    assert harness.result is harness.original_result
    assert harness.persisted == []
    assert harness.service.state.phase == "failed"


def test_auto_accept_registers_existing_commit_without_second_apply() -> None:
    harness = Harness()

    assert harness.service.register_auto_accept(
        harness.report("auto_accept"),
        previous_config={"smooth_window": 11},
        previous_result=harness.original_result,
    )

    assert harness.apply_calls == []
    assert harness.rerun_calls == 0
    assert harness.persisted == [("preprocess-c1", "auto_accept")]
    assert harness.service.state.phase == "applied"


def test_undo_revokes_experience_only_after_undo_rerun_success() -> None:
    harness = Harness()
    assert harness.service.begin_confirmation(
        harness.report(), accepted_by="user_confirmed"
    )
    harness.service.finalize_success()

    assert harness.service.undo() is True
    assert harness.config == {"smooth_window": 11}
    assert harness.revoked == []
    assert harness.service.state.phase == "undo_pending"

    harness.service.finalize_success()

    assert harness.revoked == ["preprocess-c1"]
    assert harness.service.state.phase == "undone"
