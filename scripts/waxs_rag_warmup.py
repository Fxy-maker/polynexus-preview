from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAXS_ROOT = PROJECT_ROOT / "\u6d4b\u8bd5\u6570\u636e" / "WAXS"
OUTPUT_DIR = PROJECT_ROOT / "results" / "waxs_rag_warmup"
LOG_DIR = OUTPUT_DIR / "logs"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"

SUPPORTED_EXTS = {".edf", ".raw"}
SUBMODULE_MAP = {
    "原位变温广角": "waxs.in_situ_temp",
    "原位拉伸广角": "waxs.in_situ_stretch",
    "普通广角": "waxs.static",
}


def main() -> int:
    _configure_console()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    files = _find_waxs_files()
    print(f"found_waxs_files={len(files)} root={WAXS_ROOT}", flush=True)

    rows: list[dict] = []
    crash_count = 0
    for index, data_file in enumerate(files, start=1):
        submodule = _submodule_for_file(data_file)
        output_path = OUTPUT_DIR / f"{index:02d}_{_safe_name(data_file.parent.name)}_{_safe_name(data_file.name)}.json"
        log_path = LOG_DIR / f"{index:02d}_{_safe_name(data_file.parent.name)}_{_safe_name(data_file.name)}.log"
        if output_path.exists():
            output_path.unlink()

        command = [
            sys.executable,
            "-m",
            "polynexus",
            "ai-tune",
            "--technique",
            "waxs",
            "--submodule",
            submodule,
            "--input",
            str(data_file),
            "--polymer",
            "PA6",
            "--max-rounds",
            "2",
            "--model",
            "gpt-5.4-mini",
            "--reasoning",
            "low",
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
            row = _row_from_report(data_file, output_path, proc.returncode, time.time() - started, submodule)
            if row["status"] == "ERROR":
                row["remark"] = _error_remark(proc.returncode, stdout, stderr)
                crash_count += 1
        except subprocess.TimeoutExpired as exc:
            crash_count += 1
            log_path.write_text((exc.stdout or "") + "\n[TIMEOUT]\n" + (exc.stderr or ""), encoding="utf-8")
            row = {
                "file": data_file.name,
                "path": str(data_file),
                "output": str(output_path),
                "submodule": submodule,
                "baseline_r_squared": None,
                "best_r_squared": None,
                "delta_r_squared": None,
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
            f"baseline={_fmt(row.get('baseline_r_squared'))} best={_fmt(row.get('best_r_squared'))} "
            f"delta={_fmt(row.get('delta_r_squared'))} converged={row.get('converged')} remark={row.get('remark')}",
            flush=True,
        )
        if crash_count > 3:
            print(f"CRASH_LIMIT_EXCEEDED crash_count={crash_count}", flush=True)
            break

    print(_format_table(rows), flush=True)
    return 0


def _find_waxs_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(WAXS_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if "polynexus_output" in str(path):
            continue
        if path.suffix.lower() in SUPPORTED_EXTS:
            files.append(path)
    return files


def _submodule_for_file(data_file: Path) -> str:
    return SUBMODULE_MAP.get(data_file.parent.name, "waxs.static")


def _row_from_report(data_file: Path, output_path: Path, returncode: int, elapsed_sec: float, submodule: str) -> dict:
    if not output_path.exists():
        return {
            "file": data_file.name,
            "path": str(data_file),
            "output": str(output_path),
            "submodule": submodule,
            "baseline_r_squared": None,
            "best_r_squared": None,
            "delta_r_squared": None,
            "converged": None,
            "returncode": returncode,
            "status": "ERROR",
            "remark": "NO_REPORT",
            "elapsed_sec": round(elapsed_sec, 2),
        }

    report = json.loads(output_path.read_text(encoding="utf-8"))
    baseline = report.get("baseline_r_squared")
    best = report.get("best_r_squared")
    delta = None
    try:
        if baseline is not None and best is not None:
            delta = float(best) - float(baseline)
    except Exception:
        delta = None
    remark = "OK" if returncode == 0 else f"NONZERO_EXIT_{returncode}"
    return {
        "file": data_file.name,
        "path": str(data_file),
        "output": str(output_path),
        "submodule": report.get("submodule") or submodule,
        "baseline_r_squared": baseline,
        "best_r_squared": best,
        "delta_r_squared": delta,
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
    return re.sub(r"[^A-Za-z0-9_.()\-]+", "_", name).strip("_") or "waxs_case"


def _format_table(rows: list[dict]) -> str:
    lines = ["file | submodule | baseline_r2 | best_r2 | delta_r2 | converged | remark", "--- | --- | ---: | ---: | ---: | --- | ---"]
    for row in rows:
        lines.append(
            f"{row['file']} | {row.get('submodule')} | {_fmt(row.get('baseline_r_squared'))} | "
            f"{_fmt(row.get('best_r_squared'))} | {_fmt(row.get('delta_r_squared'))} | "
            f"{row.get('converged')} | {row.get('remark')}"
        )
    return "\n".join(lines)


def _fmt(value: object) -> str:
    if value is None:
        return "ERROR"
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return str(value)


def _configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
