"""Batch preset helpers for the PolyNexus CLI."""

from __future__ import annotations

import sys
from typing import Any

from polynexus.utils import (
    delete_batch_preset,
    list_batch_presets,
    load_batch_last_run,
    load_batch_preset,
    save_batch_preset,
)


def batch_preset_values_from_args(args) -> dict:
    return {
        "input_dir": str(getattr(args, "input_dir", "") or ""),
        "technique": str(getattr(args, "technique", "") or ""),
        "pattern": str(getattr(args, "pattern", "*") or "*"),
        "workers": int(getattr(args, "workers", 1) or 1),
        "output_dir": str(getattr(args, "output_dir", "") or ""),
    }


def apply_loaded_batch_preset(args, values: dict) -> None:
    if not isinstance(values, dict):
        return
    for key in ("input_dir", "technique", "pattern", "workers", "output_dir"):
        if key in values:
            setattr(args, key, values.get(key))


def batch_cli_overrides_from_args(args) -> dict:
    overrides = {}
    if getattr(args, "input_dir", None):
        overrides["input_dir"] = getattr(args, "input_dir")
    if getattr(args, "technique", None):
        overrides["technique"] = getattr(args, "technique")
    pattern = getattr(args, "pattern", "*")
    if pattern not in (None, "", "*"):
        overrides["pattern"] = pattern
    workers = getattr(args, "workers", 1)
    if workers not in (None, 1):
        overrides["workers"] = workers
    if getattr(args, "output_dir", None):
        overrides["output_dir"] = getattr(args, "output_dir")
    return overrides


def describe_batch_task(values: dict) -> str:
    if not isinstance(values, dict):
        return ""
    parts = []
    technique = str(values.get("technique") or "").strip()
    input_dir = str(values.get("input_dir") or "").strip()
    pattern = str(values.get("pattern") or "").strip()
    output_dir = str(values.get("output_dir") or "").strip()
    workers = values.get("workers")
    if technique:
        parts.append(f"technique={technique}")
    if input_dir:
        parts.append(f"input_dir={input_dir}")
    if pattern:
        parts.append(f"pattern={pattern}")
    if output_dir:
        parts.append(f"output_dir={output_dir}")
    if workers not in (None, ""):
        parts.append(f"workers={workers}")
    return ", ".join(parts)


def apply_batch_preset_actions(args) -> int | None:
    preset_name = str(getattr(args, "preset", "") or "").strip()
    overrides = batch_cli_overrides_from_args(args)
    if preset_name and getattr(args, "rerun_last", False):
        print("Use either --preset or --rerun-last, not both.", file=sys.stderr)
        return 2

    if preset_name:
        values = load_batch_preset(preset_name)
        if values is None:
            print(f"Batch preset not found: {preset_name}", file=sys.stderr)
            return 2
        apply_loaded_batch_preset(args, values)
        apply_loaded_batch_preset(args, overrides)
        details = describe_batch_task(batch_preset_values_from_args(args))
        if details:
            print(f"Loaded batch preset: {preset_name} ({details})")
        else:
            print(f"Loaded batch preset: {preset_name}")

    if getattr(args, "rerun_last", False):
        values = load_batch_last_run()
        if values is None:
            print("No previous batch task snapshot found.", file=sys.stderr)
            return 2
        apply_loaded_batch_preset(args, values)
        apply_loaded_batch_preset(args, overrides)
        details = describe_batch_task(batch_preset_values_from_args(args))
        if details:
            print(f"Loaded last batch task snapshot. ({details})")
        else:
            print("Loaded last batch task snapshot.")

    if getattr(args, "list_presets", False):
        names = list_batch_presets()
        if not names:
            print("No batch presets saved.")
        else:
            print("Batch presets:")
            for name in names:
                values = load_batch_preset(name)
                details = describe_batch_task(values or {})
                if details:
                    print(f"  {name} ({details})")
                else:
                    print(f"  {name}")
        return 0

    delete_name = str(getattr(args, "delete_preset", "") or "").strip()
    if delete_name:
        values = load_batch_preset(delete_name)
        if delete_batch_preset(delete_name):
            details = describe_batch_task(values or {})
            if details:
                print(f"Deleted batch preset: {delete_name} ({details})")
            else:
                print(f"Deleted batch preset: {delete_name}")
            return 0
        print(f"Batch preset not found: {delete_name}", file=sys.stderr)
        return 2

    save_name = str(getattr(args, "save_preset", "") or "").strip()
    if save_name:
        if not getattr(args, "input_dir", None):
            print("Batch input directory is required to save a preset.", file=sys.stderr)
            return 2
        if not getattr(args, "technique", None):
            print("Batch technique is required to save a preset.", file=sys.stderr)
            return 2
        values = batch_preset_values_from_args(args)
        save_batch_preset(save_name, values)
        details = describe_batch_task(values)
        if details:
            print(f"Saved batch preset: {save_name} ({details})")
        else:
            print(f"Saved batch preset: {save_name}")
        return 0

    return None
