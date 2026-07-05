from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAXS_ROOT = PROJECT_ROOT / "测试数据" / "saxs"
OUTPUT_DIR = PROJECT_ROOT / "results" / "saxs_rag_warmup"
LOG_DIR = OUTPUT_DIR / "logs"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    files = [
        path
        for path in sorted(SAXS_ROOT.rglob("*.edf"))
        if "polynexus_output" not in str(path)
    ]
    print(f"found_edf={len(files)} root={SAXS_ROOT}", flush=True)

    rows: list[dict] = []
    for index, data_file in enumerate(files, start=1):
        output_path = OUTPUT_DIR / f"{_safe_name(data_file.stem)}.json"
        log_path = LOG_DIR / f"{index:02d}_{_safe_name(data_file.stem)}.log"
        if output_path.exists():
            output_path.unlink()

        command = [
            sys.executable,
            "-m",
            "polynexus",
            "ai-tune",
            "--technique",
            "saxs",
            "--input",
            str(data_file),
            "--polymer",
            "PA6",
            "--max-rounds",
            "5",
            "--output",
            str(output_path),
        ]
        print(f"[{index}/{len(files)}] start {data_file}", flush=True)
        started = time.time()
        try:
            proc = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=900,
            )
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            log_path.write_text(stdout + ("\n[stderr]\n" + stderr if stderr else ""), encoding="utf-8")
            row = _row_from_report(data_file, output_path, proc.returncode, time.time() - started)
            if row["status"] == "ERROR":
                row["remark"] = _error_remark(proc.returncode, stdout, stderr)
        except subprocess.TimeoutExpired as exc:
            log_path.write_text((exc.stdout or "") + "\n[TIMEOUT]\n" + (exc.stderr or ""), encoding="utf-8")
            row = {
                "file": data_file.name,
                "path": str(data_file),
                "output": str(output_path),
                "baseline_r_squared": None,
                "best_r_squared": None,
                "converged": None,
                "returncode": None,
                "status": "ERROR",
                "remark": "TIMEOUT",
                "elapsed_sec": round(time.time() - started, 2),
            }

        rows.append(row)
        SUMMARY_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"[{index}/{len(files)}] {row['status']} "
            f"baseline={row['baseline_r_squared']} best={row['best_r_squared']} "
            f"converged={row['converged']} remark={row['remark']}",
            flush=True,
        )

    print(_format_table(rows), flush=True)
    return 0


def _row_from_report(data_file: Path, output_path: Path, returncode: int, elapsed_sec: float) -> dict:
    if not output_path.exists():
        return {
            "file": data_file.name,
            "path": str(data_file),
            "output": str(output_path),
            "baseline_r_squared": None,
            "best_r_squared": None,
            "converged": None,
            "returncode": returncode,
            "status": "ERROR",
            "remark": "NO_REPORT",
            "elapsed_sec": round(elapsed_sec, 2),
        }

    report = json.loads(output_path.read_text(encoding="utf-8"))
    remark = "OK"
    if returncode:
        remark = f"NONZERO_EXIT_{returncode}"
    return {
        "file": data_file.name,
        "path": str(data_file),
        "output": str(output_path),
        "baseline_r_squared": report.get("baseline_r_squared"),
        "best_r_squared": report.get("best_r_squared"),
        "converged": report.get("converged"),
        "returncode": returncode,
        "status": "OK",
        "remark": remark,
        "elapsed_sec": round(elapsed_sec, 2),
    }


def _error_remark(returncode: int, stdout: str, stderr: str) -> str:
    text = "\n".join([stdout, stderr])
    if "AI tune engine error" in text:
        return f"ENGINE_ERROR_EXIT_{returncode}"
    if "Traceback" in text:
        return f"TRACEBACK_EXIT_{returncode}"
    return f"NO_REPORT_EXIT_{returncode}"


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.()\\-]+", "_", name).strip("_") or "saxs_case"


def _format_table(rows: list[dict]) -> str:
    lines = ["文件名 | baseline r² | best r² | converged | 备注"]
    lines.append("--- | ---: | ---: | --- | ---")
    for row in rows:
        baseline = _fmt(row.get("baseline_r_squared"))
        best = _fmt(row.get("best_r_squared"))
        lines.append(
            f"{row['file']} | {baseline} | {best} | {row.get('converged')} | {row.get('remark')}"
        )
    return "\n".join(lines)


def _fmt(value: object) -> str:
    if value is None:
        return "ERROR"
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
