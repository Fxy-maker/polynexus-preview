from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_DATA_DIR = PROJECT_ROOT / "\u6d4b\u8bd5\u6570\u636e"
DEFAULT_WAXS_ROOT = TEST_DATA_DIR / "waxs"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tests" / "eval" / "cases" / "real"
SUPPORTED_EXTENSIONS = {".raw", ".edf"}


def convert_all(waxs_root: Path = DEFAULT_WAXS_ROOT, output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    from polynexus.core.waxs_engine.io import load_scan

    if not waxs_root.exists():
        raise FileNotFoundError(f"WAXS data directory not found: {waxs_root}")

    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("waxs_real_*.json"):
        old.unlink()

    written: list[Path] = []
    for data_file in discover_waxs_files(waxs_root):
        scan = load_scan(str(data_file))
        case = build_case(data_file, scan)
        target = output_dir / f"{case['case_id']}.json"
        target.write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(target)
    return written


def discover_waxs_files(waxs_root: Path = DEFAULT_WAXS_ROOT) -> list[Path]:
    files = []
    for path in sorted(waxs_root.rglob("*")):
        if not path.is_file():
            continue
        if "polynexus_output" in path.parts:
            continue
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    return files


def build_case(data_file: Path, scan: Any) -> dict[str, Any]:
    rel_to_test_data = data_file.relative_to(TEST_DATA_DIR).as_posix()
    submodule = infer_submodule(data_file)
    polymer_name = infer_polymer_name(data_file)
    features = extract_features(data_file, scan, submodule)
    return {
        "case_id": make_case_id(data_file, submodule),
        "technique": "waxs",
        "submodule": submodule,
        "data_file": rel_to_test_data,
        "polymer_name": polymer_name,
        "polymer_phase": None,
        "config_overrides": {
            "real_data": True,
            "source_file": str(data_file),
            "file_format": data_file.suffix.lower().lstrip("."),
            "extracted_features": features,
        },
        "ground_truth": {},
        "source": "expert_review",
        "notes": "Converted from real WAXS data. Ground truth is empty until human review.",
    }


def extract_features(data_file: Path, scan: Any, submodule: str) -> dict[str, Any]:
    features: dict[str, Any] = {
        "label": getattr(scan, "label", data_file.stem),
        "submodule": submodule,
        "extension": data_file.suffix.lower(),
    }
    image = getattr(scan, "image", None)
    two_theta = np.asarray(getattr(scan, "two_theta_deg", np.array([])), dtype=float)
    intensity = np.asarray(getattr(scan, "I_arb", np.array([])), dtype=float)

    if image is not None:
        arr = np.asarray(image, dtype=float)
        features.update(
            {
                "data_kind": "2d_image",
                "image_shape": list(arr.shape),
                "intensity_min": float(np.nanmin(arr)),
                "intensity_max": float(np.nanmax(arr)),
                "intensity_mean": float(np.nanmean(arr)),
            }
        )
    elif len(two_theta) and len(intensity):
        features.update(
            {
                "data_kind": "1d_profile",
                "n_points": int(len(two_theta)),
                "two_theta_min": float(np.nanmin(two_theta)),
                "two_theta_max": float(np.nanmax(two_theta)),
                "intensity_min": float(np.nanmin(intensity)),
                "intensity_max": float(np.nanmax(intensity)),
                "estimated_peak_centers": estimate_peak_centers(two_theta, intensity),
            }
        )
    else:
        features["data_kind"] = "unknown"

    condition = infer_condition(data_file, submodule)
    if condition:
        features["condition"] = condition
    return features


def estimate_peak_centers(two_theta: np.ndarray, intensity: np.ndarray, top_n: int = 5) -> list[float]:
    if len(two_theta) < 3 or len(intensity) < 3:
        return []
    y = intensity.astype(float)
    local_max = np.where((y[1:-1] > y[:-2]) & (y[1:-1] >= y[2:]))[0] + 1
    if len(local_max) == 0:
        return []
    strongest = local_max[np.argsort(y[local_max])[-top_n:]]
    centers = sorted(float(two_theta[index]) for index in strongest)
    return [round(center, 4) for center in centers]


def infer_submodule(path: Path) -> str:
    parent_text = " ".join(part.lower() for part in path.parts)
    if "\u53d8\u6e29" in parent_text or "temperature" in parent_text:
        return "temperature"
    if "\u62c9\u4f38" in parent_text or "strain" in parent_text:
        return "strain"
    return "static"


def infer_polymer_name(path: Path) -> str:
    text = path.stem.upper()
    if "PA6" in text:
        return "PA6"
    return "unknown"


def infer_condition(path: Path, submodule: str) -> dict[str, Any] | None:
    stem = path.stem
    if submodule == "temperature":
        head = re.split(r"-W(?:_|-|$)", stem, maxsplit=1, flags=re.IGNORECASE)[0]
        tokens = [float(item) for item in re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", head)]
        if tokens:
            value = tokens[-1]
            return {"type": "temperature", "value": value, "unit": "C"}
    if submodule == "strain":
        match = re.match(r"(\d+)-", stem)
        if match:
            return {"type": "strain", "value": float(match.group(1)), "unit": "%"}
    return None


def make_case_id(path: Path, submodule: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "_", path.stem).strip("_").lower()
    stem = stem or "case"
    return f"waxs_real_{submodule}_{stem}"


def print_inventory(waxs_root: Path = DEFAULT_WAXS_ROOT) -> None:
    files = discover_waxs_files(waxs_root)
    print(f"真实 WAXS 原始文件: {len(files)}")
    for path in files:
        print(f"- {path} ({path.suffix.lower()}, {path.stat().st_size} bytes)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert real WAXS files to EvalCase JSON.")
    parser.add_argument("--waxs-root", default=str(DEFAULT_WAXS_ROOT), help="Real WAXS data directory.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="EvalCase output directory.")
    args = parser.parse_args(argv)

    waxs_root = Path(args.waxs_root)
    output_dir = Path(args.output_dir)
    print_inventory(waxs_root)
    written = convert_all(waxs_root, output_dir)
    print(f"写出 EvalCase: {len(written)} -> {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
