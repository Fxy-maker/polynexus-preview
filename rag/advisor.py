from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from llm.llm_client import LLMCancelledError, LLMClient

from .prompt_builder import PromptBuilder
from .preprocess_intent import (
    contains_preprocess_action,
    normalize_preprocess_intent,
    strip_numeric_preprocess_changes,
)
from .retriever import RagRetriever

if TYPE_CHECKING:
    import threading


ADVISOR_SYSTEM_PROMPT = """You are PolyNexus's constrained tuning advisor.
Core evidence and versioned policy are authoritative. Choose only allowed actions and,
for preprocessing, emit only a strict qualitative PreprocessIntent. Never invent or
write numeric baseline or smoothing parameters. For SAXS, candidate references may
only use exact IDs already present in the current summary context; references are
diagnostic-only and never execute, rerun, or mutate a configuration. Return exactly
one JSON object.
"""


class Advisor:
    def __init__(
        self,
        retriever: RagRetriever | None = None,
        prompt_builder: PromptBuilder | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.retriever = retriever or RagRetriever()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.llm_client = llm_client or LLMClient()
        self.last_prompt = ""

    def advise(
        self,
        eval_case: dict[str, Any],
        *,
        workspace_context: dict[str, Any] | None = None,
        cancel_event: "threading.Event | None" = None,
    ) -> dict[str, Any]:
        current_sample = self._normalize_case(eval_case)
        saxs_candidate_ids = self._saxs_candidate_ids(current_sample)
        query = self._query_from_sample(current_sample)
        retrieved = self.retriever.retrieve(
            query,
            str(current_sample.get("technique", "")),
            top_k=3,
            polymer_name=str(current_sample.get("polymer_name", "")),
        )
        prompt = self.prompt_builder.build(
            current_sample,
            retrieved,
            current_sample.get("history", []),
            workspace_context=workspace_context,
        )
        if workspace_context:
            context_text = ""
            formatter = getattr(self.prompt_builder, "_format_workspace_context", None)
            if callable(formatter):
                context_text = str(formatter(workspace_context) or "").strip()
            if context_text and context_text != "None" and "## Workspace context" not in prompt:
                prompt = f"{prompt}\n\n## Workspace context\n{context_text}"
        self.last_prompt = prompt
        try:
            try:
                raw = self.llm_client.chat(
                    prompt,
                    system=ADVISOR_SYSTEM_PROMPT,
                    json_mode=True,
                    cancel_event=cancel_event,
                )
            except TypeError as exc:
                if "system" not in str(exc):
                    raise
                # Compatibility for lightweight third-party/test clients that
                # predate the optional system-message argument.
                raw = self.llm_client.chat(
                    prompt,
                    json_mode=True,
                    cancel_event=cancel_event,
                )
            parsed = self._parse_response(raw)
            parsed["llm_used"] = not self.llm_client.last_used_mock
            normalized = self._normalize_advice(
                parsed,
                saxs_candidate_ids=saxs_candidate_ids,
            )
        except LLMCancelledError:
            raise
        except Exception as exc:
            print(f"[Advisor] LLM call failed, falling back to mock: {exc}")
            fallback = self._mock_response(retrieved, str(exc))
            fallback["llm_used"] = False
            normalized = self._normalize_advice(
                fallback,
                saxs_candidate_ids=saxs_candidate_ids,
            )
        normalized["reference_cases"] = normalized.get("reference_cases") or [
            item["case_id"] for item in retrieved
        ]
        return normalized

    def _normalize_case(self, eval_case: dict[str, Any]) -> dict[str, Any]:
        params = (
            eval_case.get("params")
            or eval_case.get("output_parameters")
            or eval_case.get("ground_truth")
            or eval_case.get("config_overrides")
            or {}
        )
        saxs_ai_context = eval_case.get("saxs_ai_context", {})
        if not isinstance(saxs_ai_context, dict):
            saxs_ai_context = {}
        return {
            "case_id": eval_case.get("case_id", "unknown"),
            "technique": str(eval_case.get("technique", "unknown")).upper(),
            "polymer_name": eval_case.get("polymer_name", "unknown"),
            "params": params,
            "current_config": eval_case.get("current_config", {}),
            "output_parameters": eval_case.get("output_parameters", params),
            "r_squared": eval_case.get("r_squared", ""),
            "residuals_pattern": eval_case.get("residuals_pattern", ""),
            "residual_pattern": eval_case.get("residual_pattern", {}),
            "polymer_knowledge": eval_case.get("polymer_knowledge", {}),
            "history": eval_case.get("history", []),
            "round": eval_case.get("round"),
            "previous_score": eval_case.get("previous_score"),
            "tunable_params": eval_case.get("tunable_params", []),
            "allowed_actions": eval_case.get("allowed_actions", []),
            "allowed_changes": eval_case.get("allowed_changes", {}),
            "symptoms": eval_case.get("symptoms", []),
            "symptom_summary": eval_case.get("symptom_summary", ""),
            "workspace_context": eval_case.get("workspace_context", {}),
            "analysis_evidence": eval_case.get("analysis_evidence", {}),
            "ir_reference_bands": eval_case.get("ir_reference_bands", {}),
            "saxs_ai_context": dict(saxs_ai_context),
        }

    def _query_from_sample(self, current_sample: dict[str, Any]) -> str:
        return (
            f"技术: {current_sample.get('technique')} | "
            f"聚合物: {current_sample.get('polymer_name')} | "
            f"参数: {json.dumps(current_sample.get('params', {}), ensure_ascii=False, sort_keys=True)}"
        )

    @staticmethod
    def _saxs_candidate_ids(current_sample: dict[str, Any]) -> set[str] | None:
        """Return the only candidate IDs the current SAXS case can reference."""

        if str(current_sample.get("technique", "")).upper() != "SAXS":
            return None
        context = current_sample.get("saxs_ai_context", {})
        if not isinstance(context, dict):
            return set()
        if str(context.get("mode", "") or "").strip().lower() != "temperature":
            return set()
        series = context.get("series", {})
        if not isinstance(series, dict):
            return set()
        candidates = series.get("sequence_rescue_candidates", [])
        if not isinstance(candidates, list):
            return set()
        return {
            str(item.get("candidate_id", "")).strip()
            for item in candidates
            if isinstance(item, dict) and str(item.get("candidate_id", "")).strip()
        }

    @staticmethod
    def _normalize_saxs_candidate_references(
        value: object,
        allowed_ids: set[str],
    ) -> list[str]:
        if not isinstance(value, list):
            return []
        references: list[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            candidate_id = item.strip()
            if candidate_id in allowed_ids and candidate_id not in references:
                references.append(candidate_id)
        return references

    # ── JSON response parsing ─────────────────────────────────────────
    @staticmethod
    def _extract_json_object(text: str) -> str:
        """Extract the first complete JSON object using bracket counting.

        Handles nested objects, strings containing braces, escaped
        characters, and markdown code fences.
        """
        # Strip markdown code fences: ```json ... ``` or ``` ... ```
        cleaned = re.sub(r"```(?:json)?\s*\n?", "", text)
        cleaned = re.sub(r"\n?```\s*", "", cleaned)

        start = cleaned.find("{")
        if start == -1:
            raise ValueError("响应中未找到 JSON 对象")

        depth = 0
        in_string = False
        escape_next = False
        for i in range(start, len(cleaned)):
            ch = cleaned[i]
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return cleaned[start : i + 1]

        raise ValueError("响应中 JSON 对象未闭合")

    def _parse_response(self, raw: str) -> dict[str, Any]:
        # 1. Direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 2. Bracket-counting extraction
        try:
            extracted = self._extract_json_object(raw)
            return json.loads(extracted)
        except (ValueError, json.JSONDecodeError):
            pass

        # 3. Last resort: fix common LLM JSON mistakes
        try:
            extracted = self._extract_json_object(raw)
            # Repair single quotes → double quotes (common LLM mistake)
            repaired = re.sub(r"(?<!\\)'", '"', extracted)
            return json.loads(repaired)
        except (ValueError, json.JSONDecodeError):
            pass

        raise ValueError(
            f"LLM 响应无法解析为 JSON。原始响应前 200 字符: {raw[:200]}"
        )

    def _mock_response(self, retrieved_cases: list[dict[str, Any]], error: str) -> dict[str, Any]:
        provider_label = getattr(self.llm_client, "provider_label", "LLM")
        return {
            "assessment": "WARN",
            "confidence": 0.0,
            "diagnosis": "provider_unavailable",
            "reasoning": f"{provider_label} API 不可用，已降级 mock。原因: {error}",
            "recommended_actions": [],
            "changes": {},
            "expected_improvement": {},
            "risk": "high",
            "suggestions": ["检查 API Key、网络连通性和模型/接口地址是否正确。"],
            "reference_cases": [item["case_id"] for item in retrieved_cases],
            "converge": True,
        }

    def _normalize_advice(
        self,
        advice: dict[str, Any],
        *,
        saxs_candidate_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        assessment = str(advice.get("assessment", "WARN")).upper()
        if assessment not in {"PASS", "WARN", "FAIL"}:
            assessment = "WARN"
        confidence = float(advice.get("confidence", 0.0))
        if not math.isfinite(confidence):
            raise ValueError("AI advice confidence must be finite")
        confidence = max(0.0, min(1.0, confidence))
        suggestions = advice.get("suggestions", [])
        if not isinstance(suggestions, list):
            suggestions = [str(suggestions)]
        reference_cases = advice.get("reference_cases", [])
        if not isinstance(reference_cases, list):
            reference_cases = [str(reference_cases)]
        changes = advice.get("changes", {})
        if not isinstance(changes, dict):
            changes = {}
        expected_improvement = advice.get("expected_improvement", {})
        if not isinstance(expected_improvement, dict):
            expected_improvement = {"value": str(expected_improvement)}
        diagnosis = str(advice.get("diagnosis", "") or "").strip()
        hypothesis = str(advice.get("hypothesis", "") or diagnosis).strip()
        target_symptom = str(advice.get("target_symptom", "") or "").strip()
        allowed_changes = advice.get("allowed_changes", {})
        if not isinstance(allowed_changes, dict):
            allowed_changes = {}
        expected_evidence_change = advice.get("expected_evidence_change", {})
        if not isinstance(expected_evidence_change, dict):
            expected_evidence_change = {}
        rollback_condition = str(advice.get("rollback_condition", "") or "").strip()
        recommended_actions = advice.get("recommended_actions", [])
        if not isinstance(recommended_actions, list):
            recommended_actions = [recommended_actions] if recommended_actions else []
        normalized_actions: list[dict[str, Any]] = []
        for item in recommended_actions:
            if isinstance(item, dict):
                name = str(item.get("name", "") or "").strip()
                if not name:
                    continue
                normalized_actions.append(
                    {
                        "name": name,
                        "reason": str(item.get("reason", "") or "").strip(),
                        "expected_evidence_change": str(item.get("expected_evidence_change", "") or "").strip(),
                    }
                )
            else:
                name = str(item or "").strip()
                if name:
                    normalized_actions.append({"name": name, "reason": "", "expected_evidence_change": ""})
        preprocess_intent, preprocess_intent_error = normalize_preprocess_intent(advice)
        has_preprocess_request = (
            "preprocess_intent" in advice
            or contains_preprocess_action(normalized_actions)
        )
        if has_preprocess_request:
            changes = strip_numeric_preprocess_changes(changes)
        converge = bool(advice.get("converge", False))
        if converge:
            changes = {}
        normalized = {
            "assessment": assessment,
            "confidence": confidence,
            "diagnosis": diagnosis,
            "reasoning": str(advice.get("reasoning", "")),
            "hypothesis": hypothesis,
            "target_symptom": target_symptom,
            "changes": changes,
            "allowed_changes": allowed_changes,
            "recommended_actions": normalized_actions,
            "expected_improvement": expected_improvement,
            "expected_evidence_change": expected_evidence_change,
            "rollback_condition": rollback_condition,
            "risk": str(advice.get("risk", "medium")),
            "suggestions": [str(item) for item in suggestions],
            "reference_cases": [str(item) for item in reference_cases],
            "converge": converge,
            "llm_used": bool(advice.get("llm_used", False)),
        }
        if saxs_candidate_ids is not None or "saxs_candidate_references" in advice:
            normalized["saxs_candidate_references"] = self._normalize_saxs_candidate_references(
                advice.get("saxs_candidate_references", []),
                saxs_candidate_ids or set(),
            )
        if has_preprocess_request:
            normalized["preprocess_intent"] = preprocess_intent
            normalized["preprocess_intent_error"] = preprocess_intent_error
        return normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate RAG-backed PolyNexus tuning advice.")
    parser.add_argument("--case", required=True, help="EvalCase JSON file.")
    parser.add_argument("--db-path", default="rag/chroma_db", help="RAG database path.")
    args = parser.parse_args(argv)

    payload = json.loads(Path(args.case).read_text(encoding="utf-8"))
    advisor = Advisor(retriever=RagRetriever(db_path=args.db_path))
    advice = advisor.advise(payload)
    print(json.dumps(advice, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
