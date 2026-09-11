from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from polynexus.core.public_validation import (
    PublicReplayCase,
    public_canonical_dataset_id,
    run_public_validation_case,
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _archive(tmp_path: Path, *, member: str, content: bytes) -> tuple[Path, str, str]:
    archive = tmp_path / "pack.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(member, content)
    archive_hash = _sha256(archive.read_bytes())
    content_hash = _sha256(content)
    return archive, archive_hash, content_hash


def _case(archive: Path, archive_hash: str, content_hash: str, *, member: str, technique: str = "ir", source_format: str = "csv", expected_run_status: str = "completed") -> PublicReplayCase:
    relative_archive = archive.name
    dataset_id = public_canonical_dataset_id(
        source_archive=relative_archive,
        source_archive_sha256=archive_hash,
        source_member=member,
        extracted_file_sha256=content_hash,
        source_format=source_format,
        technique=technique,
    )
    return PublicReplayCase(
        case_id="public_case",
        technique=technique,
        source_archive=relative_archive,
        source_archive_sha256=archive_hash,
        source_member=member,
        extracted_file_sha256=content_hash,
        source_format=source_format,
        canonical_dataset_id=dataset_id,
        expected_run_status=expected_run_status,
    )


def test_public_file_replay_uses_shared_compute_and_is_deterministic(tmp_path: Path) -> None:
    content = b"wavenumber,intensity\n1000,1\n1100,2\n1200,1\n"
    archive, archive_hash, content_hash = _archive(tmp_path, member="ir/sample.csv", content=content)
    case = _case(archive, archive_hash, content_hash, member="ir/sample.csv")

    entry = run_public_validation_case(case, data_root=tmp_path)

    assert entry.case.case_id == "public_case"
    assert entry.first_output["metrics"]["run_status"] == "completed"
    assert entry.first_output["metrics"]["canonical_dataset_id"] == case.canonical_dataset_id
    assert entry.first_output["metrics"]["canonical_admission_dataset_id"] == case.canonical_dataset_id
    assert entry.raw_hash_before == content_hash
    assert entry.raw_hash_after == content_hash


def test_public_replay_rejects_archive_and_extracted_hash_tampering(tmp_path: Path) -> None:
    content = b"wavenumber,intensity\n1000,1\n1100,2\n"
    archive, archive_hash, content_hash = _archive(tmp_path, member="ir/sample.csv", content=content)
    case = _case(archive, archive_hash, content_hash, member="ir/sample.csv")

    archive.write_bytes(archive.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="source archive SHA-256"):
        run_public_validation_case(case, data_root=tmp_path)

    archive.write_bytes(b"not-the-original-archive")
    with pytest.raises(ValueError, match="source archive SHA-256"):
        run_public_validation_case(case, data_root=tmp_path)


def test_public_replay_rejects_member_traversal_and_format_mismatch(tmp_path: Path) -> None:
    content = b"wavenumber,intensity\n1000,1\n1100,2\n"
    archive, archive_hash, content_hash = _archive(tmp_path, member="ir/sample.csv", content=content)
    with pytest.raises(ValueError, match="relative archive member"):
        PublicReplayCase(
            case_id="bad_path",
            technique="ir",
            source_archive="../pack.zip",
            source_archive_sha256=archive_hash,
            source_member="ir/sample.csv",
            extracted_file_sha256=content_hash,
            source_format="csv",
            canonical_dataset_id="dataset",
        )

    mismatched = _case(archive, archive_hash, content_hash, member="ir/sample.csv", source_format="txt")
    with pytest.raises(ValueError, match="extracted source_format"):
        run_public_validation_case(mismatched, data_root=tmp_path)


def test_public_unavailable_case_is_explicit_and_not_completed(tmp_path: Path) -> None:
    content = b"opaque vendor bytes"
    archive, archive_hash, content_hash = _archive(tmp_path, member="sec/sample.opju", content=content)
    case = _case(
        archive,
        archive_hash,
        content_hash,
        member="sec/sample.opju",
        technique="sec",
        source_format="opju",
        expected_run_status="failed",
    )

    entry = run_public_validation_case(case, data_root=tmp_path)

    assert entry.first_output["metrics"]["run_status"] == "failed"
    assert entry.first_output["metrics"]["canonical_admission_dataset_id"] == case.canonical_dataset_id
    assert entry.first_output["metrics"]["canonical_dataset_id"] == case.canonical_dataset_id


def test_public_case_round_trip_rejects_tampering(tmp_path: Path) -> None:
    content = b"wavenumber,intensity\n1000,1\n1100,2\n"
    archive, archive_hash, content_hash = _archive(tmp_path, member="ir/sample.csv", content=content)
    case = _case(archive, archive_hash, content_hash, member="ir/sample.csv")
    restored = PublicReplayCase.from_dict(case.to_dict())
    assert restored == case
    payload = json.loads(json.dumps(case.to_dict()))
    payload["source_format"] = "txt"
    with pytest.raises(ValueError, match="case_hash"):
        PublicReplayCase.from_dict(payload)
