from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import asdict, fields, replace
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from .models import BenchmarkSummary, EvalCase, EvalResult, GroundTruth, Range
from .runner import EvalRunner


class AuditReporter:
    VALID_ANNOTATIONS = {"PASS", "WARN", "FAIL"}

    def __init__(self, runner: EvalRunner | None = None):
        self.runner = runner or EvalRunner()
        self.last_cases: list[EvalCase] = []
        self.last_results_path: Path | None = None
        self.last_timestamp: str | None = None

    def batch_run(
        self,
        cases_dir: str,
        output_dir: str,
        real_data_root: str | None = None,
    ) -> list[EvalResult]:
        cases = self.runner.load_all_cases(cases_dir)
        if self.runner.load_errors:
            errors = "\n".join(f"{path}: {message}" for path, message in self.runner.load_errors)
            raise RuntimeError(f"Failed to load one or more eval cases:\n{errors}")

        if real_data_root is not None:
            cases = [self._apply_real_data_root(case, real_data_root) for case in cases]

        total = len(cases)
        results: list[EvalResult] = []
        for index, case in enumerate(cases, start=1):
            print(f"[{index}/{total}] running: {case.case_id} ... ", end="", flush=True)
            result = self.runner.run_case(case)
            results.append(result)
            print(self._status_for_result(result))

        timestamp = self._timestamp()
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        results_path = output_path / f"results_{timestamp}.json"
        bundle = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cases_dir": str(Path(cases_dir)),
            "real_data_root": real_data_root,
            "cases": [self._case_to_dict(case) for case in cases],
            "results": [self._result_to_dict(result) for result in results],
            "summary": self._bundle_summary(results),
        }
        results_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.last_cases = cases
        self.last_results_path = results_path
        self.last_timestamp = timestamp
        return results

    def generate_report(
        self,
        results: list[EvalResult],
        cases: list[EvalCase],
        output_path: str,
    ) -> str:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        case_by_id = {case.case_id: case for case in cases}
        ordered_pairs = [(case_by_id.get(result.case_id), result) for result in results]
        statuses = [self._status_for_result(result) for _, result in ordered_pairs]
        status_counts = {name: statuses.count(name) for name in ("PASS", "WARN", "FAIL")}
        technique_counts = self._technique_counts(cases)
        average_score = sum(result.composite for result in results) / len(results) if results else 0.0
        average_phys = sum(result.phys_score for result in results) / len(results) if results else 0.0
        average_peak = sum(result.peak_score for result in results) / len(results) if results else 0.0
        quality_counters = self._quality_counters(results)
        benchmark_summary = self._benchmark_summary(results)

        case_cards = []
        for case, result in ordered_pairs:
            if case is None:
                continue
            case_cards.append(self._render_case_card(case, result))

        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PolyNexus Eval Audit Report</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #667085;
      --line: #d8dee8;
      --pass: #0f8a4b;
      --pass-bg: #e7f7ee;
      --warn: #a66a00;
      --warn-bg: #fff5d6;
      --fail: #b42318;
      --fail-bg: #fde8e7;
      --accent: #2563eb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.5;
    }}
    main {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 48px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: end;
      margin-bottom: 18px;
    }}
    h1 {{
      font-size: 28px;
      margin: 0 0 4px;
      letter-spacing: 0;
    }}
    .muted {{ color: var(--muted); }}
    .overview {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .metric, .case-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }}
    .metric {{ padding: 14px; }}
    .metric strong {{ display: block; font-size: 26px; }}
    .boundary-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .boundary-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
      box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }}
    .boundary-card strong {{
      display: block;
      margin-bottom: 4px;
      font-size: 13px;
      text-transform: uppercase;
    }}
    .section-label {{
      margin: 8px 0 10px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0;
    }}
    .distribution {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }}
    .chip {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 13px;
      background: #fff;
    }}
    details.case-card {{
      margin: 12px 0;
      overflow: hidden;
    }}
    details.case-card > summary {{
      cursor: pointer;
      list-style: none;
      padding: 14px 16px;
      display: grid;
      grid-template-columns: minmax(220px, 1.4fr) 110px 110px minmax(160px, 1fr);
      gap: 12px;
      align-items: center;
      border-bottom: 1px solid var(--line);
    }}
    details.case-card > summary::-webkit-details-marker {{ display: none; }}
    .case-body {{ padding: 14px 16px 18px; }}
    .status {{
      display: inline-flex;
      align-items: center;
      width: fit-content;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 13px;
      font-weight: 700;
    }}
    .status.PASS {{ color: var(--pass); background: var(--pass-bg); }}
    .status.WARN {{ color: var(--warn); background: var(--warn-bg); }}
    .status.FAIL {{ color: var(--fail); background: var(--fail-bg); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      font-size: 14px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      text-align: left;
      padding: 8px 10px;
      vertical-align: top;
    }}
    th {{ color: #344054; background: #f9fafb; }}
    .score-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      margin-top: 12px;
    }}
    .score {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px 10px;
      background: #fcfcfd;
    }}
    .annotation-bar {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
      margin-top: 14px;
    }}
    button {{
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      border-radius: 6px;
      padding: 7px 10px;
      cursor: pointer;
      font-weight: 700;
    }}
    button[data-status="PASS"].active {{ border-color: var(--pass); background: var(--pass-bg); color: var(--pass); }}
    button[data-status="WARN"].active {{ border-color: var(--warn); background: var(--warn-bg); color: var(--warn); }}
    button[data-status="FAIL"].active {{ border-color: var(--fail); background: var(--fail-bg); color: var(--fail); }}
    .ok {{ color: var(--pass); font-weight: 700; }}
    .bad {{ color: var(--fail); font-weight: 700; }}
    @media (max-width: 820px) {{
      .overview, .score-grid, .boundary-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      details.case-card > summary {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
    }}
    @media (max-width: 520px) {{
      main {{ width: min(100vw - 20px, 1180px); padding-top: 18px; }}
      .overview, .score-grid, .boundary-grid {{ grid-template-columns: 1fr; }}
      header {{ display: block; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>PolyNexus Eval Audit Report</h1>
        <div class="muted">Generated at {escape(datetime.now(timezone.utc).isoformat())}</div>
      </div>
      <div class="status PASS">Local annotations saved in browser</div>
    </header>
    <section class="overview" aria-label="overview">
      <div class="metric"><span class="muted">Total cases</span><strong>{len(results)}</strong></div>
      <div class="metric"><span class="muted">Status</span><strong>{status_counts["PASS"]}/{status_counts["WARN"]}/{status_counts["FAIL"]}</strong><span class="muted">PASS / WARN / FAIL</span></div>
      <div class="metric"><span class="muted">Average composite</span><strong>{average_score:.3f}</strong><span class="muted">phys {average_phys:.3f} | peak {average_peak:.3f}</span></div>
      <div class="metric"><span class="muted">Quality mix</span><div class="distribution">{self._render_distribution(quality_counters)}</div></div>
      <div class="metric"><span class="muted">Technique distribution</span><div class="distribution">{self._render_distribution(technique_counts)}</div></div>
    </section>
    <div class="section-label">Benchmark</div>
    <section class="boundary-grid" aria-label="benchmark">
      <div class="boundary-card"><strong>Objective delta</strong><span class="muted">{self._format_benchmark_delta(benchmark_summary.get("average_objective_delta"))}</span><span class="muted">gain {benchmark_summary.get("objective_gain_cases", 0)} / loss {benchmark_summary.get("objective_loss_cases", 0)} | accept {self._format_benchmark_rate(benchmark_summary.get("acceptance_rate", 0.0))} / reject {self._format_benchmark_rate(benchmark_summary.get("rejection_rate", 0.0))}</span></div>
      <div class="boundary-card"><strong>Rollback reasons</strong><div class="distribution">{self._render_distribution(benchmark_summary.get("rollback_reasons", {}))}</div></div>
      <div class="boundary-card"><strong>Constraint hits</strong><span class="muted">{self._format_benchmark_rate(benchmark_summary.get("constraint_hit_rate", 0.0))}</span><span class="muted">failed {benchmark_summary.get("constraint_hit_counts", {}).get("failed_checks", 0)} / {benchmark_summary.get("constraint_hit_counts", {}).get("total_checks", 0)}</span></div>
      <div class="boundary-card"><strong>Symptom fixes</strong><span class="muted">{self._format_benchmark_rate(benchmark_summary.get("symptom_fix_rate", 0.0))}</span><span class="muted">hit {benchmark_summary.get("symptom_hit_counts", {}).get("hit", 0)} / {benchmark_summary.get("symptom_hit_counts", {}).get("total", 0)}</span></div>
    </section>
    <div class="section-label">Boundary</div>
    <section class="boundary-grid" aria-label="boundary">
      {''.join(
          f'<div class="boundary-card"><strong>{escape(name)}</strong><span class="muted">{escape(text)}</span></div>'
          for name, text in self._boundary_summary().items()
      )}
    </section>
    <section aria-label="case details">
      {''.join(case_cards)}
    </section>
  </main>
  <script>
    const storageKey = "polynexus.audit.annotations";
    function readAnnotations() {{
      try {{ return JSON.parse(localStorage.getItem(storageKey) || "{{}}"); }}
      catch (err) {{ return {{}}; }}
    }}
    function writeAnnotations(data) {{
      localStorage.setItem(storageKey, JSON.stringify(data));
    }}
    function applyAnnotations() {{
      const data = readAnnotations();
      document.querySelectorAll("[data-ann-group]").forEach(group => {{
        const caseId = group.getAttribute("data-ann-group");
        const selected = data[caseId];
        group.querySelectorAll("button[data-status]").forEach(button => {{
          button.classList.toggle("active", button.getAttribute("data-status") === selected);
        }});
        const label = document.querySelector(`[data-ann-label="${{caseId}}"]`);
        if (label) label.textContent = selected ? `Annotation: ${{selected}}` : "Annotation: none";
      }});
    }}
    function setAnnotation(caseId, status) {{
      const data = readAnnotations();
      data[caseId] = status;
      writeAnnotations(data);
      applyAnnotations();
    }}
    document.addEventListener("DOMContentLoaded", applyAnnotations);
  </script>
</body>
</html>
"""
        path.write_text(html, encoding="utf-8")
        return str(path)

    def write_annotations(self, annotations: dict[str, str], cases_dir: str) -> None:
        real_dir = Path(cases_dir) / "real"
        timestamp = datetime.now(timezone.utc).isoformat()
        for case_id, status in annotations.items():
            normalized = status.upper()
            if normalized not in self.VALID_ANNOTATIONS:
                raise ValueError(f"Invalid annotation for {case_id}: {status}")
            target = real_dir / f"{case_id}.json"
            if not target.exists():
                raise FileNotFoundError(f"Cannot annotate missing real case JSON: {target}")
            payload = json.loads(target.read_text(encoding="utf-8"))
            payload["human_annotation"] = normalized
            payload["annotated_at"] = timestamp
            tmp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
            try:
                tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                tmp.replace(target)
            finally:
                if tmp.exists():
                    tmp.unlink()

    def load_results_bundle(self, results_path: str | Path) -> tuple[list[EvalResult], list[EvalCase]]:
        bundle = json.loads(Path(results_path).read_text(encoding="utf-8"))
        results = [self._result_from_dict(item) for item in bundle.get("results", [])]
        cases = [self._case_from_dict(item) for item in bundle.get("cases", [])]
        return results, cases

    def _render_case_card(self, case: EvalCase, result: EvalResult) -> str:
        status = self._status_for_result(result)
        diff_rows = self._render_diff_rows(case, result)
        data_name = Path(case.data_file).name if not case.data_file.startswith("synth:") else case.data_file
        return f"""
<details class="case-card" open>
  <summary>
    <div><strong>{escape(case.case_id)}</strong><br><span class="muted">{escape(case.polymer_name)} {escape(case.polymer_phase or "")}</span></div>
    <div>{escape(case.technique.upper())}</div>
    <div><span class="status {status}">{status}</span></div>
    <div class="muted">{escape(data_name)}</div>
  </summary>
  <div class="case-body">
    <div class="score-grid">
      {self._score_box("PHYS", result.phys_score)}
      {self._score_box("PEAK", result.peak_score)}
      {self._score_box("CROSS", result.cross_score)}
      {self._score_box("HUMAN", result.human_score)}
    </div>
    <table>
      <thead><tr><th>Parameter</th><th>Ground Truth</th><th>Agent Output</th><th>Deviation</th></tr></thead>
      <tbody>{diff_rows}</tbody>
    </table>
    <div class="annotation-bar" data-ann-group="{escape(case.case_id)}">
      <span class="muted" data-ann-label="{escape(case.case_id)}">Annotation: none</span>
      <button type="button" data-status="PASS" onclick="setAnnotation('{escape(case.case_id)}', 'PASS')">✅ PASS</button>
      <button type="button" data-status="WARN" onclick="setAnnotation('{escape(case.case_id)}', 'WARN')">⚠️ WARN</button>
      <button type="button" data-status="FAIL" onclick="setAnnotation('{escape(case.case_id)}', 'FAIL')">❌ FAIL</button>
    </div>
  </div>
</details>
"""

    def _render_diff_rows(self, case: EvalCase, result: EvalResult) -> str:
        rows = []
        gt = case.ground_truth
        for field in fields(GroundTruth):
            name = field.name
            truth = getattr(gt, name)
            if truth is None:
                continue
            output = result.output_parameters.get(name)
            if name in EvalRunner.RANGE_LIST_FIELDS:
                rows.extend(self._diff_rows_for_range_list(name, truth, output))
            elif name == "crystal_form":
                rows.append(self._diff_row_for_text(name, truth, output))
            else:
                rows.append(self._diff_row_for_range(name, truth, output))
        return "".join(rows) if rows else "<tr><td colspan=\"4\" class=\"muted\">No ground truth fields.</td></tr>"

    def _diff_rows_for_range_list(self, name: str, truth: list[Range], output: Any) -> list[str]:
        output_values = output if isinstance(output, list) else []
        rows = []
        for index, truth_range in enumerate(truth):
            value = output_values[index] if index < len(output_values) else None
            rows.append(self._diff_row_for_range(f"{name}[{index}]", truth_range, value))
        return rows

    def _diff_row_for_range(self, name: str, truth: Range, output: Any) -> str:
        truth_text = self._format_range(truth)
        if output is None:
            output_text = "<span class=\"bad\">missing ❌</span>"
            deviation = "missing"
        else:
            value = float(output)
            in_range = float(truth[0]) <= value <= float(truth[1])
            mark = "✅" if in_range else "❌"
            css = "ok" if in_range else "bad"
            output_text = f"<span class=\"{css}\">{self._format_number(value)} {mark}</span>"
            deviation = "-" if in_range else self._format_deviation(value, truth)
        return f"<tr><td>{escape(name)}</td><td>{truth_text}</td><td>{output_text}</td><td>{escape(deviation)}</td></tr>"

    def _diff_row_for_text(self, name: str, truth: str, output: Any) -> str:
        in_range = output == truth
        mark = "✅" if in_range else "❌"
        css = "ok" if in_range else "bad"
        output_text = f"<span class=\"{css}\">{escape(str(output))} {mark}</span>"
        return f"<tr><td>{escape(name)}</td><td>{escape(truth)}</td><td>{output_text}</td><td>{'-' if in_range else 'mismatch'}</td></tr>"

    def _apply_real_data_root(self, case: EvalCase, real_data_root: str) -> EvalCase:
        if case.data_file.startswith("synth:"):
            return case
        path = Path(case.data_file)
        if path.is_absolute():
            return case
        return replace(case, data_file=str((Path(real_data_root) / path).resolve()))

    def _case_to_dict(self, case: EvalCase) -> dict[str, Any]:
        return {
            "case_id": case.case_id,
            "technique": case.technique,
            "submodule": case.submodule,
            "data_file": case.data_file,
            "polymer_name": case.polymer_name,
            "polymer_phase": case.polymer_phase,
            "config_overrides": case.config_overrides,
            "ground_truth": self._ground_truth_to_dict(case.ground_truth),
            "source": case.source,
            "notes": case.notes,
        }

    def _case_from_dict(self, payload: dict[str, Any]) -> EvalCase:
        return EvalCase(
            case_id=payload["case_id"],
            technique=payload["technique"],
            submodule=payload.get("submodule", ""),
            data_file=payload["data_file"],
            polymer_name=payload["polymer_name"],
            polymer_phase=payload.get("polymer_phase"),
            config_overrides=dict(payload.get("config_overrides", {})),
            ground_truth=self._ground_truth_from_dict(payload.get("ground_truth", {})),
            source=payload["source"],
            notes=payload.get("notes", ""),
        )

    def _result_to_dict(self, result: EvalResult) -> dict[str, Any]:
        return {
            "case_id": result.case_id,
            "technique": result.technique,
            "phys_score": result.phys_score,
            "peak_score": result.peak_score,
            "cross_score": result.cross_score,
            "human_score": result.human_score,
            "composite": result.composite,
            "details": result.details,
            "parameters_used": result.parameters_used,
            "output_parameters": result.output_parameters,
        }

    def _bundle_summary(self, results: list[EvalResult]) -> dict[str, Any]:
        status_counts = {name: 0 for name in ("PASS", "WARN", "FAIL")}
        reasons: dict[str, int] = {}
        for result in results:
            status = self._status_for_result(result)
            status_counts[status] = status_counts.get(status, 0) + 1
            reason = self._result_reason(result)
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
        benchmark = self._benchmark_summary(results)
        return {
            "count": len(results),
            "status_counts": status_counts,
            "average_composite": (sum(result.composite for result in results) / len(results)) if results else 0.0,
            "average_phys": (sum(result.phys_score for result in results) / len(results)) if results else 0.0,
            "average_peak": (sum(result.peak_score for result in results) / len(results)) if results else 0.0,
            "average_cross": self._mean_or_none(result.cross_score for result in results),
            "average_human": self._mean_or_none(result.human_score for result in results),
            "reasons": reasons,
            "benchmark": benchmark,
        }

    def _boundary_summary(self) -> dict[str, str]:
        return {
            "core": "Evidence pack drives the result; no free-form overrides.",
            "AI": "AI only proposes small whitelist-constrained action hypotheses.",
            "orchestrator": "Accept / rollback is evidence-gated and reversible.",
            "user": "Final scientific judgment stays with the user.",
        }

    def _quality_counters(self, results: list[EvalResult]) -> dict[str, int]:
        counters = {"phys": 0, "peak": 0, "cross": 0, "human": 0}
        for result in results:
            if result.phys_score < 1.0:
                counters["phys"] += 1
            if result.peak_score < 1.0:
                counters["peak"] += 1
            if result.cross_score is not None:
                counters["cross"] += 1
            if result.human_score is not None:
                counters["human"] += 1
        return counters

    def _result_reason(self, result: EvalResult) -> str:
        if result.details.get("rollback_reason"):
            return str(result.details.get("rollback_reason"))
        if result.phys_score < 1.0 and result.composite < 0.60:
            return "phys_or_composite_fail"
        if result.composite < 0.85:
            return "low_composite"
        return ""

    def _result_from_dict(self, payload: dict[str, Any]) -> EvalResult:
        return EvalResult(
            case_id=payload["case_id"],
            technique=payload["technique"],
            phys_score=float(payload["phys_score"]),
            peak_score=float(payload["peak_score"]),
            cross_score=payload.get("cross_score"),
            human_score=payload.get("human_score"),
            composite=float(payload["composite"]),
            details=dict(payload.get("details", {})),
            parameters_used=dict(payload.get("parameters_used", {})),
            output_parameters=dict(payload.get("output_parameters", {})),
        )

    def _ground_truth_to_dict(self, gt: GroundTruth) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for field in fields(GroundTruth):
            value = getattr(gt, field.name)
            if value is not None:
                payload[field.name] = value
        return payload

    def _ground_truth_from_dict(self, payload: dict[str, Any]) -> GroundTruth:
        values: dict[str, Any] = {}
        for field in fields(GroundTruth):
            value = payload.get(field.name)
            if value is None:
                continue
            if field.name in EvalRunner.RANGE_FIELDS:
                values[field.name] = tuple(value)
            elif field.name in EvalRunner.RANGE_LIST_FIELDS:
                values[field.name] = [tuple(item) for item in value]
            else:
                values[field.name] = value
        return GroundTruth(**values)

    def _technique_counts(self, cases: list[EvalCase]) -> dict[str, int]:
        counts = {name: 0 for name in ("waxs", "dsc", "saxs", "ir", "nmr")}
        for case in cases:
            counts[case.technique] = counts.get(case.technique, 0) + 1
        return counts

    def _render_distribution(self, counts: dict[str, int]) -> str:
        return "".join(f"<span class=\"chip\">{escape(name.upper())}: {count}</span>" for name, count in counts.items())

    def _score_box(self, name: str, value: float | None) -> str:
        text = "N/A" if value is None else f"{value:.3f}"
        return f"<div class=\"score\"><span class=\"muted\">{escape(name)}</span><br><strong>{escape(text)}</strong></div>"

    def _benchmark_summary(self, results: list[EvalResult]) -> dict[str, Any]:
        total_cases = len(results)
        status_counts = {name: 0 for name in ("PASS", "WARN", "FAIL")}
        reasons: dict[str, int] = {}
        objective_deltas: list[float] = []
        objective_gain_cases = 0
        objective_loss_cases = 0
        accepted_cases = 0
        rejected_cases = 0
        benchmark_case_count = 0
        rollback_reasons: dict[str, int] = {}
        symptom_hit_counts = {"hit": 0, "miss": 0, "total": 0}
        constraint_hit_counts = {"passed_checks": 0, "failed_checks": 0, "total_checks": 0}

        for result in results:
            status = self._status_for_result(result)
            status_counts[status] = status_counts.get(status, 0) + 1
            reason = self._result_reason(result)
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1

            benchmark = result.details.get("benchmark") if isinstance(result.details, dict) else {}
            if isinstance(benchmark, dict) and benchmark:
                benchmark_case_count += 1
                objective_delta = self._safe_float(benchmark.get("objective_delta"))
                if objective_delta is None:
                    baseline = benchmark.get("baseline") if isinstance(benchmark.get("baseline"), dict) else {}
                    tuned = benchmark.get("tuned") if isinstance(benchmark.get("tuned"), dict) else {}
                    if isinstance(baseline, dict) and isinstance(tuned, dict):
                        tuned_composite = self._safe_float(tuned.get("composite"))
                        baseline_composite = self._safe_float(baseline.get("composite"))
                        if tuned_composite is not None and baseline_composite is not None:
                            objective_delta = tuned_composite - baseline_composite
                if objective_delta is not None:
                    objective_deltas.append(objective_delta)
                    if objective_delta > 0:
                        objective_gain_cases += 1
                    elif objective_delta < 0:
                        objective_loss_cases += 1

                accepted = benchmark.get("accepted")
                if accepted is True:
                    accepted_cases += 1
                elif accepted is False:
                    rejected_cases += 1

                reason_text = str(benchmark.get("rollback_reason") or "").strip()
                if reason_text:
                    rollback_reasons[reason_text] = rollback_reasons.get(reason_text, 0) + 1

                if "symptom_hit" in benchmark:
                    if bool(benchmark.get("symptom_hit")):
                        symptom_hit_counts["hit"] += 1
                    else:
                        symptom_hit_counts["miss"] += 1

            phys = result.details.get("phys") if isinstance(result.details, dict) else {}
            checks = phys.get("checks") if isinstance(phys, dict) else []
            if isinstance(checks, list):
                for check in checks:
                    if not isinstance(check, dict):
                        continue
                    constraint_hit_counts["total_checks"] += 1
                    if bool(check.get("passed")):
                        constraint_hit_counts["passed_checks"] += 1
                    else:
                        constraint_hit_counts["failed_checks"] += 1

        return asdict(
            BenchmarkSummary(
                total_cases=total_cases,
                status_counts=status_counts,
                average_composite=(sum(result.composite for result in results) / len(results)) if results else 0.0,
                average_phys=(sum(result.phys_score for result in results) / len(results)) if results else 0.0,
                average_peak=(sum(result.peak_score for result in results) / len(results)) if results else 0.0,
                average_cross=self._mean_or_none(result.cross_score for result in results),
                average_human=self._mean_or_none(result.human_score for result in results),
                reasons=reasons,
                average_objective_delta=self._mean_or_none(objective_deltas),
                objective_gain_cases=objective_gain_cases,
                objective_loss_cases=objective_loss_cases,
                acceptance_rate=(accepted_cases / benchmark_case_count) if benchmark_case_count else 0.0,
                rejection_rate=(rejected_cases / benchmark_case_count) if benchmark_case_count else 0.0,
                objective_gain_rate=(objective_gain_cases / benchmark_case_count) if benchmark_case_count else 0.0,
                rollback_reasons=rollback_reasons,
                constraint_hit_counts=constraint_hit_counts,
                constraint_hit_rate=(
                    constraint_hit_counts["failed_checks"] / constraint_hit_counts["total_checks"]
                    if constraint_hit_counts["total_checks"]
                    else 0.0
                ),
                symptom_hit_counts={**symptom_hit_counts, "total": benchmark_case_count},
                symptom_fix_rate=(symptom_hit_counts["hit"] / benchmark_case_count) if benchmark_case_count else 0.0,
            )
        )

    def _format_benchmark_delta(self, value: Any) -> str:
        if value is None:
            return "N/A"
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "N/A"
        sign = "+" if number > 0 else ""
        return f"{sign}{number:.3f}"

    def _format_benchmark_rate(self, value: Any) -> str:
        if value is None:
            return "0.0%"
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "0.0%"
        return f"{number * 100:.1f}%"

    def _mean_or_none(self, values) -> float | None:
        items = []
        for value in values:
            if value is None:
                continue
            try:
                items.append(float(value))
            except (TypeError, ValueError):
                continue
        if not items:
            return None
        return sum(items) / len(items)

    def _safe_float(self, value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number != number:
            return None
        return number

    def _status_for_result(self, result: EvalResult) -> str:
        if result.phys_score < 1.0 or result.composite < 0.60:
            return "FAIL"
        if result.composite < 0.85:
            return "WARN"
        return "PASS"

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _format_range(self, value: Range) -> str:
        return f"[{self._format_number(float(value[0]))}, {self._format_number(float(value[1]))}]"

    def _format_number(self, value: float) -> str:
        if abs(value) >= 100:
            return f"{value:.1f}"
        return f"{value:.3g}"

    def _format_deviation(self, value: float, truth: Range) -> str:
        lower, upper = float(truth[0]), float(truth[1])
        nearest = lower if value < lower else upper
        midpoint = (lower + upper) / 2.0
        if abs(midpoint) < 1e-12:
            return f"{value - nearest:+.3g}"
        return f"{((value - nearest) / abs(midpoint)) * 100:+.2f}%"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate PolyNexus eval audit reports.")
    parser.add_argument("--cases-dir", default="tests/eval/cases/", help="Directory containing eval cases.")
    parser.add_argument("--output-dir", default="tests/eval/reports/", help="Directory for report artifacts.")
    parser.add_argument("--real-data-root", default=None, help="Optional root for relative real data paths.")
    parser.add_argument("--from-results", default=None, help="Generate a report from an existing results JSON.")
    args = parser.parse_args(argv)

    reporter = AuditReporter()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.from_results:
        results, cases = reporter.load_results_bundle(args.from_results)
        timestamp = reporter._timestamp()
    else:
        results = reporter.batch_run(args.cases_dir, args.output_dir, args.real_data_root)
        cases = reporter.last_cases
        timestamp = reporter.last_timestamp or reporter._timestamp()
        if reporter.last_results_path:
            print(f"Results JSON: {reporter.last_results_path}")

    report_path = output_dir / f"report_{timestamp}.html"
    reporter.generate_report(results, cases, str(report_path))
    print(f"HTML report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
