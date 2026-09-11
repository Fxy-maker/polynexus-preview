from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

from polynexus.cli.parser import parse_args
from polynexus.cli.run_public_validation_service import run_public_validation_cli
from polynexus.core.public_validation import PublicReplayCase, public_canonical_dataset_id


def test_public_validate_cli_emits_one_json_and_persists_report(tmp_path: Path, capsys) -> None:
    content = b"wavenumber,intensity\n1000,1\n1100,2\n1200,1\n"
    archive = tmp_path / "pack.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("ir/sample.csv", content)
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    content_hash = hashlib.sha256(content).hexdigest()
    dataset_id = public_canonical_dataset_id(
        source_archive="pack.zip",
        source_archive_sha256=archive_hash,
        source_member="ir/sample.csv",
        extracted_file_sha256=content_hash,
        source_format="csv",
        technique="ir",
    )
    case = PublicReplayCase(
        case_id="cli_public_case",
        technique="ir",
        source_archive="pack.zip",
        source_archive_sha256=archive_hash,
        source_member="ir/sample.csv",
        extracted_file_sha256=content_hash,
        source_format="csv",
        canonical_dataset_id=dataset_id,
    )
    manifest = tmp_path / "public-replay.json"
    manifest.write_text(json.dumps({"schema_version": 1, "entries": [case.to_dict()]}), encoding="utf-8")
    project = tmp_path / "project"
    project.mkdir()
    args = parse_args(
        [
            "public-validate",
            "--manifest",
            str(manifest),
            "--data-root",
            str(tmp_path),
            "--project-root",
            str(project),
            "--json",
        ]
    )

    assert run_public_validation_cli(args) == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["status"] == "passed"
    assert Path(payload["report_path"]).is_file()
