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

    pd = sub.add_parser("dsc", help="DSC")
    pd.add_argument("input")
    pd.add_argument("-o", "--output", default="")
    pd.add_argument("--skip-to", default=None, choices=["preprocess", "analyze", "plot"])

    pi = sub.add_parser("ir", help="IR")
    pi.add_argument("input")
    pi.add_argument("-o", "--output", default="")
    pi.add_argument("--skip-to", default=None, choices=["preprocess", "analyze", "plot"])

    pw = sub.add_parser("waxs", help="WAXS")
    pw.add_argument("input")
    pw.add_argument("-o", "--output", default="")
    pw.add_argument("--skip-to", default=None, choices=["preprocess", "analyze", "plot"])

    pn = sub.add_parser("nmr", help="NMR")
    pn.add_argument("input")
    pn.add_argument("-o", "--output", default="")
    pn.add_argument("--skip-to", default=None, choices=["preprocess", "analyze", "plot"])

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

