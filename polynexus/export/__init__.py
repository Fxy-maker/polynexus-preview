"""
PolyNexus SCI export module — v2.0 unified across all techniques.

Generates structured output directories with:
- Figures (main + SI) in PDF/PNG
- Unified CSV parameter tables with quality flags
- HTML / Markdown reports
- Cross-technique joint export support
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np

from ..plotting.sci_style import (
    create_output_structure,
    save_figure_sci,
    get_quality_label,
    QUALITY_FLAGS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Unified Parameter Export
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExportRow:
    """One row in the unified parameter CSV.

    Maps to the design doc specification for DSC_Results_All.csv /
    SAXS_Results_All.csv / WAXS_Results_All.csv etc.
    """
    sample_id: str = ""
    technique: str = ""
    submodule: str = ""
    condition_type: str = ""   # "static", "strain", "temperature", "time"
    condition_value: float = 0.0
    # Quality
    quality_flag: int = 0
    quality_label: str = ""
    # Parameters (technique-specific, stored as flat dict)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_flat_dict(self) -> Dict[str, Any]:
        """Flatten to a single-level dict for CSV export."""
        flat = {
            "SampleID": self.sample_id,
            "Technique": self.technique,
            "Submodule": self.submodule,
            "ConditionType": self.condition_type,
            "ConditionValue": self.condition_value,
            "QualityFlag": self.quality_flag,
            "QualityLabel": self.quality_label,
        }
        # Add parameters with rounded floats
        for k, v in self.parameters.items():
            if isinstance(v, float):
                flat[k] = round(v, 6)
            else:
                flat[k] = v
        return flat


def export_parameters_csv(
    rows: List[ExportRow],
    output_path: str | Path,
    technique: str = "",
) -> Path:
    """Export analysis parameters to unified CSV format.

    Parameters
    ----------
    rows : list of ExportRow
        One row per sample/condition.
    output_path : str or Path
        Output file path.
    technique : str
        Technique name for the filename if output_path is a directory.

    Returns
    -------
    Path
        Path to the written CSV file.
    """
    output = Path(output_path)
    if output.is_dir():
        output = output / f"{technique}_Results_All.csv"

    flat_rows = [r.to_flat_dict() for r in rows]
    df = pd.DataFrame(flat_rows)

    # Reorder columns: metadata first, then parameters
    meta_cols = ["SampleID", "Technique", "Submodule", "ConditionType",
                  "ConditionValue", "QualityFlag", "QualityLabel"]
    param_cols = [c for c in df.columns if c not in meta_cols]
    df = df[meta_cols + param_cols]

    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    return output


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Unified Report Generation
# ═══════════════════════════════════════════════════════════════════════════════

def generate_tech_report(
    technique: str,
    rows: List[ExportRow],
    output_dir: str | Path,
    figures: Optional[Dict[str, str]] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> Path:
    """Generate a Markdown analysis report for one technique.

    Parameters
    ----------
    technique : str
        Technique name (dsc/saxs/waxs/nmr/ir).
    rows : list of ExportRow
        Analysis result rows.
    output_dir : str or Path
        Directory to write the report.
    figures : dict, optional
        {figure_name: filepath} mapping of generated figures.
    metadata : dict, optional
        Extra metadata (experiment date, instrument, etc.).

    Returns
    -------
    Path
        Path to the written report.
    """
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f"# {technique.upper()} Analysis Report")
    lines.append("")
    lines.append(f"**Generated**: {pd.Timestamp.now().isoformat()}")
    lines.append("")

    if metadata:
        lines.append("## Experiment Information")
        lines.append("")
        for k, v in metadata.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    # Quality summary
    lines.append("## Quality Summary")
    lines.append("")
    flag_counts = {}
    for row in rows:
        label = row.quality_label or get_quality_label(row.quality_flag, technique)
        flag_counts[label] = flag_counts.get(label, 0) + 1
    for label, count in flag_counts.items():
        lines.append(f"- {label}: {count} sample(s)")
    lines.append("")

    # Parameter table
    if rows:
        lines.append("## Parameters")
        lines.append("")
        flat_rows = [r.to_flat_dict() for r in rows]
        df = pd.DataFrame(flat_rows)
        lines.append(df.to_markdown(index=False))
        lines.append("")

    # Figures
    if figures:
        lines.append("## Figures")
        lines.append("")
        for name, path in figures.items():
            lines.append(f"- **{name}**: `{path}`")
        lines.append("")

    report_path = root / "analysis_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Full SCI Export Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def sci_export(
    technique: str,
    rows: List[ExportRow],
    output_root: str | Path,
    figures: Optional[Dict[str, str]] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> Path:
    """Create complete SCI-standard output for one technique.

    Directory structure:
        output_root/
        ├── raw_{technique}/
        ├── parameters/
        │   └── {technique}_Results_All.csv
        ├── figures/
        │   ├── main/          (vector PDF + raster PNG)
        │   └── SI/            (supplementary)
        └── report/
            └── analysis_report.md

    Parameters
    ----------
    technique : str
        Technique name.
    rows : list of ExportRow
        Analysis result rows.
    output_root : str or Path
        Root output directory.
    figures : dict, optional
        {name: filepath} of generated figures.
    metadata : dict, optional
        Experiment metadata.

    Returns
    -------
    Path
        Root output directory.
    """
    root = Path(output_root)

    # 1. Create directory structure
    dirs = create_output_structure(root, technique)

    # 2. Export parameters CSV
    export_parameters_csv(rows, dirs["parameters"], technique=technique)

    # 3. Copy figures into main / SI
    if figures:
        for name, src_path in figures.items():
            src = Path(src_path)
            if src.exists():
                # P1 (main) figures go to main/, P2/P3 go to SI
                dst_dir = dirs["figures_si"] if name.startswith(("fig_s", "SI_")) else dirs["figures_main"]
                shutil.copy2(src, dst_dir / src.name)

    # 4. Generate report
    generate_tech_report(
        technique, rows,
        dirs["report"],
        figures=figures,
        metadata=metadata,
    )

    return root


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Joint / Cross-Technique Export
# ═══════════════════════════════════════════════════════════════════════════════

def sci_export_joint(
    results_by_technique: Dict[str, Dict[str, Any]],
    output_root: str | Path,
) -> Path:
    """Export joint analysis from multiple techniques.

    Parameters
    ----------
    results_by_technique : dict
        {technique_name: {"rows": [...], "figures": {...}, "metadata": {...}}}
    output_root : str or Path
        Root output directory for the joint report.

    Returns
    -------
    Path
        Root output directory.
    """
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)

    for tech, data in results_by_technique.items():
        sci_export(
            technique=tech,
            rows=data.get("rows", []),
            output_root=root,
            figures=data.get("figures"),
            metadata=data.get("metadata"),
        )

    # Joint summary report
    lines = ["# Joint Analysis Report", ""]
    lines.append(f"**Generated**: {pd.Timestamp.now().isoformat()}")
    lines.append("")
    lines.append("## Techniques Included")
    lines.append("")
    for tech in results_by_technique:
        lines.append(f"- {tech.upper()}")
    lines.append("")

    (root / "report" / "joint_report.md").write_text(
        "\n".join(lines), encoding="utf-8")

    return root
