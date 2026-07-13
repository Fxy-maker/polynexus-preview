from __future__ import annotations

from typing import Any


def _handle_preprocess_intent_round(
    self: Any,
    engine: Any,
    round_num: int,
    advice: dict[str, Any],
    previous_record: Any,
    prompt: str,
) -> dict[str, Any]:
    intent_payload = advice.get("preprocess_intent")
    if intent_payload is None and advice.get("preprocess_intent_error"):
        intent_payload = {"advisor_error": advice["preprocess_intent_error"]}
    report = self.run_preprocess_intent(
        intent_payload,
        engine=engine,
        previous_record=previous_record,
        prompt=prompt,
    )
    self._last_preprocess_report = self._to_plain_value(report) if hasattr(
        self, "_to_plain_value"
    ) else report
    decision = report.get("preprocess_decision", {})
    accepted = decision.get("decision") == "auto_accept"
    record_engine = self._engine if accepted and self._engine is not None else engine
    record = self._record_round(
        record_engine,
        round_num,
        advice,
        before_r_squared=previous_record.r_squared,
        changes={},
        accepted=accepted,
        prompt=prompt,
    )
    record.preprocess_intent = dict(report.get("preprocess_intent", {}))
    record.preprocess_candidates = list(report.get("preprocess_candidates", []))
    record.preprocess_evidence = list(report.get("preprocess_evidence", []))
    record.preprocess_decision = dict(decision)
    self.history.append(record)
    if accepted:
        self._best_record = record
        self._best_r_squared = record.r_squared
        self._best_eval_score = record.eval_score

    decision_name = str(decision.get("decision", "keep_original"))
    status = {
        "auto_accept": "accepted",
        "request_confirmation": "confirmation_required",
        "keep_original": "rolled_back",
    }.get(decision_name, "rolled_back")
    self._emit_progress(
        round_num,
        previous_record.r_squared,
        record.r_squared,
        {},
        status,
        error=str(report.get("error", "") or ""),
        converged=decision_name != "request_confirmation",
        target_symptom=str(advice.get("target_symptom", "") or ""),
        symptom_summary=record.symptom_summary,
    )
    return {
        "stop": True,
        "converged": decision_name != "request_confirmation",
        "convergence_reason": f"preprocess_{decision_name}",
    }
