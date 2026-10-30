from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from polynexus.cli.run_portable_export_service import run_portable_export


def _args(raw: Path, exported: Path, *, convert_only: bool, json_output: bool) -> SimpleNamespace:
    return SimpleNamespace(
        cmd="portable-export",
        raw_source=str(raw),
        export=str(exported),
        technique="tga",
        exporter="Proteus portable CSV",
        output="",
        convert_only=convert_only,
        json=json_output,
        mapping_proposal=None,
    )


def test_portable_export_cli_conversion_only_emits_bound_template(tmp_path: Path, capsys) -> None:
    raw = tmp_path / "sample.ngb-ds1"
    raw.write_bytes(b"Netzsch TA file\x00_db_format_1\x00opaque")
    exported = tmp_path / "sample.csv"
    exported.write_text("Temperature (C),Mass (%)\n25,100\n100,98\n", encoding="utf-8")

    assert run_portable_export(_args(raw, exported, convert_only=True, json_output=True)) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ready"
    assert "compute_run" not in payload
    binding = payload["canonical_template"]["payload"]["portable_export_binding"]
    assert binding["raw_source_sha256"] == payload["raw_artifact"]["sha256"]
    assert binding["export_sha256"] != binding["raw_source_sha256"]
    assert payload["canonical_template"]["source_artifact_id"] == payload["raw_artifact"]["artifact_id"]


def test_portable_export_cli_runs_shared_compute_projection(tmp_path: Path, capsys) -> None:
    raw = tmp_path / "sample.ngb-ds1"
    raw.write_bytes(b"Netzsch TA file\x00_db_format_1\x00opaque")
    exported = tmp_path / "sample.csv"
    exported.write_text("Temperature (C),Mass (%)\n25,100\n100,98\n", encoding="utf-8")

    assert run_portable_export(_args(raw, exported, convert_only=False, json_output=True)) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["compute_run"]["status"] == "completed"
    assert payload["compute_run"]["canonical_template"]["payload"]["portable_export_binding"]["raw_source_sha256"] == payload["raw_artifact"]["sha256"]
