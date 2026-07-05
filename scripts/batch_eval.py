from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.advisor import Advisor
from rag.indexer import RagIndexer
from rag.retriever import RagRetriever
from scripts.convert_real_data import DEFAULT_OUTPUT_DIR, convert_all


DEFAULT_RESULTS_DIR = PROJECT_ROOT / "results"
DEFAULT_SUMMARY_PATH = DEFAULT_RESULTS_DIR / "real_eval_summary.json"


def batch_eval(real_cases_dir: Path = DEFAULT_OUTPUT_DIR, summary_path: Path = DEFAULT_SUMMARY_PATH) -> list[dict[str, Any]]:
    real_cases_dir.mkdir(parents=True, exist_ok=True)
    if not list(real_cases_dir.glob("*.json")):
        convert_all(output_dir=real_cases_dir)

    indexed = RagIndexer().index_all(str(PROJECT_ROOT / "tests" / "eval" / "results"))
    print(f"RAG 索引记录: {indexed}")

    advisor = Advisor(retriever=RagRetriever())
    summary: list[dict[str, Any]] = []
    for case_path in sorted(real_cases_dir.glob("*.json")):
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        advice = advisor.advise(payload)
        summary.append(
            {
                "case": case_path.name,
                "assessment": advice["assessment"],
                "confidence": advice["confidence"],
                "llm_used": advice["llm_used"],
                "reasoning": advice["reasoning"],
            }
        )

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print_summary(summary)
    print(f"结果已写入: {summary_path}")
    return summary


def print_summary(summary: list[dict[str, Any]]) -> None:
    total = len(summary)
    pass_count = sum(1 for item in summary if item["assessment"] == "PASS")
    warn_count = sum(1 for item in summary if item["assessment"] == "WARN")
    fail_count = sum(1 for item in summary if item["assessment"] == "FAIL")
    llm_success = sum(1 for item in summary if item["llm_used"])
    success_rate = (llm_success / total * 100.0) if total else 0.0
    print(f"总计: {total} 个案例")
    print(f"PASS: {pass_count} 个")
    print(f"WARN: {warn_count} 个")
    print(f"FAIL: {fail_count} 个")
    print(f"LLM 调用成功率: {success_rate:.1f}%")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run rag.advisor over real WAXS EvalCases.")
    parser.add_argument("--real-cases-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory with real EvalCase JSON files.")
    parser.add_argument("--summary-path", default=str(DEFAULT_SUMMARY_PATH), help="Output summary JSON path.")
    args = parser.parse_args(argv)

    batch_eval(Path(args.real_cases_dir), Path(args.summary_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
