"""Argument parser construction for the PolyNexus CLI."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="polynexus",
        description="PolyNexus -- Multi-Technique Polymer Characterization Platform",
    )
    parser.add_argument("--gui", action="store_true", help="Launch GUI")

    sub = parser.add_subparsers(dest="cmd", help="Technique")

    ps = sub.add_parser("saxs", help="SAXS")
    ps.add_argument("input")
    ps.add_argument("-o", "--output", default="")
    ps.add_argument("--skip-to", default=None, choices=["preprocess", "analyze", "plot"])
    ps.add_argument("--type", default="temperature", choices=["static", "strain", "temperature"])
    ps.add_argument("--json", action="store_true", help="Print the shared compute run as JSON")

    pd = sub.add_parser("dsc", help="DSC")
    pd.add_argument("input")
    pd.add_argument("-o", "--output", default="")
    pd.add_argument("--skip-to", default=None, choices=["preprocess", "analyze", "plot"])
    pd.add_argument("--json", action="store_true", help="Print the shared compute run as JSON")

    pi = sub.add_parser("ir", help="IR")
    pi.add_argument("input")
    pi.add_argument("-o", "--output", default="")
    pi.add_argument("--skip-to", default=None, choices=["preprocess", "analyze", "plot"])
    pi.add_argument("--json", action="store_true", help="Print the shared compute run as JSON")

    pw = sub.add_parser("waxs", help="WAXS")
    pw.add_argument("input")
    pw.add_argument("-o", "--output", default="")
    pw.add_argument("--skip-to", default=None, choices=["preprocess", "analyze", "plot"])
    pw.add_argument("--json", action="store_true", help="Print the shared compute run as JSON")

    pn = sub.add_parser("nmr", help="NMR")
    pn.add_argument("input")
    pn.add_argument("-o", "--output", default="")
    pn.add_argument("--skip-to", default=None, choices=["preprocess", "analyze", "plot"])
    pn.add_argument("--json", action="store_true", help="Print the shared compute run as JSON")

    pg = sub.add_parser("gui", help="AI tuning convergence viewer")
    pg.add_argument("--dry-run", action="store_true", help="Print AI tuning counts without opening a window")
    pg.add_argument("--db", default=None, help="Path to polynexus_samples.db")

    pa = sub.add_parser("ai-tune", help="AI-assisted parameter tuning")
    pa.add_argument("--technique", default="waxs", choices=["waxs", "dsc", "saxs", "ir", "nmr"], help="Technique to tune")
    pa.add_argument("--file", "--input", dest="file", required=True, help="Input data file")
    pa.add_argument("--polymer", required=True, help="Polymer name, e.g. PA6")
    pa.add_argument("--submodule", default=None, help="Optional technique submodule override")
    pa.add_argument("--rounds", "--max-rounds", dest="rounds", type=int, default=5, help="Max tuning rounds")
    pa.add_argument("--model", default="gpt-5.4-mini", help="LLM model name for reporting/compatibility")
    pa.add_argument("--reasoning", default="low", help="Reasoning effort label for reporting/compatibility")
    pa.add_argument("--output", default="ai_tune_report.json", help="Output JSON report path")

    pe = sub.add_parser("evaluate-analysis-plans", help="Project a shared analysis-plan evaluation")
    pe.add_argument("--plan", required=True, help="AnalysisPlan JSON path")
    pe.add_argument("--evaluation", required=True, help="AnalysisPlanEvaluation JSON path")

    paw = sub.add_parser("agent-workflow", help="Machine-readable agent workflow operations")
    paw.add_argument("operation", choices=["inspect", "propose", "run", "validate", "export"])
    paw.add_argument("--manifest", help="External workflow manifest JSON")
    paw.add_argument("--recipe", help="Persisted recipe JSON for deterministic replay")
    paw.add_argument("--run", help="Persisted run JSON for validate or export")
    paw.add_argument("--output-dir", default=None, help="Output directory for run/export operations")
    paw.add_argument("--export-dir", default=None, help="Destination for an exported workflow bundle")

    ppw = sub.add_parser("project-workflow", help="Codex project evidence workflow")
    ppw.add_argument(
        "operation",
        choices=["inspect", "plan", "run", "package", "manuscript-plan", "analyze-project", "attach-quick-run"],
        help="Project operation to execute",
    )
    ppw.add_argument(
        "--project-root",
        required=True,
        help="Paper/project directory containing raw data and .polynexus outputs",
    )
    ppw.add_argument(
        "--request",
        default=None,
        help="AnalysisRequest JSON path (required for plan, or run without --plan)",
    )
    ppw.add_argument(
        "--paths",
        nargs="+",
        default=(),
        help="Raw project paths to inspect (files or directories)",
    )
    ppw.add_argument(
        "--plan",
        default=None,
        help="Persisted ProjectPlan JSON path for run",
    )
    ppw.add_argument(
        "--runs",
        nargs="+",
        default=(),
        help="Persisted project workflow run JSON paths for package",
    )
    ppw.add_argument(
        "--package-id",
        default="pa6-crystallization",
        help="Evidence package identifier",
    )
    ppw.add_argument(
        "--relations",
        default=None,
        help="Optional relations JSON path for package",
    )
    ppw.add_argument(
        "--question",
        default="Analyze this research project and prepare evidence for writing.",
        help="Research question for analyze-project",
    )
    ppw.add_argument(
        "--figure-selection",
        default=None,
        help="ARS FigureSelectionRequest JSON path for analyze-project",
    )
    ppw.add_argument("--quick-run-id", default=None, help="Existing standalone quick-run identifier")
    ppw.add_argument("--technique", default=None, help="Technique for an attached quick run")
    ppw.add_argument("--source-file", default=None, help="Existing quick-run source file")
    ppw.add_argument("--output-dir", default=None, help="Existing quick-run output directory")
    ppw.add_argument("--package", default=None, help="Immutable evidence package directory for manuscript-plan")
    ppw.add_argument("--brief", default=None, help="PaperBrief JSON path for manuscript-plan")
    ppw.add_argument("--output", default=None, help="Destination JSON path for manuscript-plan")

    pb = sub.add_parser("batch", help="Batch-analyze all supported files in a directory")
    pb.add_argument("input_dir", nargs="?", help="Input directory path")
    pb.add_argument("--technique", choices=["saxs", "waxs", "dsc", "ir", "nmr"], help="Technique to analyze")
    pb.add_argument("--pattern", default="*", metavar="GLOB", help="Filename glob filter, default *")
    pb.add_argument("--workers", type=int, default=1, metavar="N", help="Parallel worker count, default 1")
    pb.add_argument("--output-dir", metavar="DIR", help="Batch output directory, default same as input directory")
    pb.add_argument("--preset", metavar="NAME", help="Load a saved batch preset by name")
    pb.add_argument("--save-preset", metavar="NAME", help="Save current batch arguments as a preset, then exit")
    pb.add_argument("--delete-preset", metavar="NAME", help="Delete a saved batch preset, then exit")
    pb.add_argument("--list-presets", action="store_true", help="List saved batch presets, then exit")
    pb.add_argument("--rerun-last", action="store_true", help="Rerun the most recent batch task snapshot")

    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)
