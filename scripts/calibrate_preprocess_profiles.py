from __future__ import annotations

import argparse
import json
from pathlib import Path

from polynexus.core.preprocess_optimization import get_preprocess_policy
from polynexus.core.preprocess_optimization.calibration import (
    calibrate_cases,
    write_calibration_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calibrate a preprocessing policy profile.")
    parser.add_argument("--technique", required=True, choices=("DSC", "IR", "WAXS", "SAXS", "NMR"))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    payload = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    cases = payload.get("cases", payload) if isinstance(payload, dict) else payload
    if not isinstance(cases, list):
        raise ValueError("Calibration manifest must contain a cases list")
    selected = [
        item
        for item in cases
        if isinstance(item, dict)
        and str(item.get("technique", args.technique)).upper() == args.technique
    ]
    report = calibrate_cases(selected, policy=get_preprocess_policy(args.technique))
    write_calibration_report(args.output, report)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.promotion_allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
