"""Hash-bound replay of external public validation-pack members.

This module is intentionally an adapter around the existing canonical and
``ComputeRun`` contracts.  It never imports code from a validation manifest,
never writes extracted raw data into the repository, and never promotes a
diagnostic result.  Archives and members are treated as untrusted inputs and
are extracted only into a bounded temporary directory.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import tempfile
from typing import Any
import zipfile

from .artifacts import directory_manifest_sha256
from .compute import ComputeRun, ComputeRunService, RawArtifact
from .project_workflow.validation import (
    ProjectValidationBatch,
    ProjectValidationEntry,
    run_project_validation_batch,
)
from .validation_harness import ValidationCase, ValidationExpectation
from .ai_platform.contracts import canonical_json_hash


_SCHEMA_VERSION = "1"
_SHA256_LENGTH = 64
_MAX_MEMBER_COUNT = 4096
_MAX_MEMBER_BYTES = 512 * 1024 * 1024
_MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
_ALLOWED_STATUSES = frozenset({"completed", "needs_input", "failed"})
_ALLOWED_CASE_KINDS = frozenset({"regression", "standard", "negative_control"})


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value.strip()) != _SHA256_LENGTH:
        raise ValueError(f"{label} must be a 64-character SHA-256")
    normalized = value.strip().lower()
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a 64-character SHA-256") from exc
    return normalized


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value.strip()


def _relative_member(value: Any, label: str) -> str:
    text = _text(value, label).replace("\\", "/")
    relative = PurePosixPath(text)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"{label} must be a relative archive member")
    return "/".join(relative.parts)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool, float)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


@dataclass(frozen=True)
class PublicReplayCase:
    """One archive member and its expected public replay contract."""

    case_id: str
    technique: str
    source_archive: str
    source_archive_sha256: str
    source_member: str
    extracted_file_sha256: str
    source_format: str
    canonical_dataset_id: str
    canonical_template_id: str | None = None
    expected_run_status: str = "completed"
    expectations: tuple[ValidationExpectation, ...] = ()
    case_kind: str = "regression"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    limitations: str = ""
    case_hash: str = ""
    schema_version: str = _SCHEMA_VERSION

    def __post_init__(self) -> None:
        case_id = _text(self.case_id, "case_id")
        technique = _text(self.technique, "technique").lower()
        archive = _relative_member(self.source_archive, "source_archive")
        member = _relative_member(self.source_member, "source_member")
        archive_hash = _sha256(self.source_archive_sha256, "source_archive_sha256")
        extracted_hash = _sha256(self.extracted_file_sha256, "extracted_file_sha256")
        source_format = _text(self.source_format, "source_format").lower()
        if source_format != "directory" and any(char in source_format for char in "/\\."):
            raise ValueError("source_format must be a bare file format or directory")
        dataset_id = _text(self.canonical_dataset_id, "canonical_dataset_id")
        status = _text(self.expected_run_status, "expected_run_status")
        if status not in _ALLOWED_STATUSES:
            raise ValueError(f"unsupported expected_run_status: {status}")
        kind = _text(self.case_kind, "case_kind")
        if kind not in _ALLOWED_CASE_KINDS:
            raise ValueError(f"unsupported case_kind: {kind}")
        expectations = tuple(self.expectations)
        if not all(type(item) is ValidationExpectation for item in expectations):
            raise TypeError("expectations must contain ValidationExpectation values")
        if len({item.path for item in expectations}) != len(expectations):
            raise ValueError("public replay expectation paths must be unique")
        if self.schema_version != _SCHEMA_VERSION:
            raise ValueError("unsupported public replay case schema version")
        object.__setattr__(self, "case_id", case_id)
        object.__setattr__(self, "technique", technique)
        object.__setattr__(self, "source_archive", archive)
        object.__setattr__(self, "source_member", member)
        object.__setattr__(self, "source_archive_sha256", archive_hash)
        object.__setattr__(self, "extracted_file_sha256", extracted_hash)
        object.__setattr__(self, "source_format", source_format)
        object.__setattr__(self, "canonical_dataset_id", dataset_id)
        object.__setattr__(self, "canonical_template_id", None if self.canonical_template_id is None else _text(self.canonical_template_id, "canonical_template_id"))
        object.__setattr__(self, "expected_run_status", status)
        object.__setattr__(self, "expectations", expectations)
        object.__setattr__(self, "case_kind", kind)
        object.__setattr__(self, "metadata", _json_safe(dict(self.metadata)))
        object.__setattr__(self, "limitations", str(self.limitations or "").strip())
        expected_hash = canonical_json_hash(self._identity_payload())
        if self.case_hash and _sha256(self.case_hash, "case_hash") != expected_hash:
            raise ValueError("public replay case_hash does not match case content")
        object.__setattr__(self, "case_hash", expected_hash)

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "technique": self.technique,
            "source_archive": self.source_archive,
            "source_archive_sha256": self.source_archive_sha256,
            "source_member": self.source_member,
            "extracted_file_sha256": self.extracted_file_sha256,
            "source_format": self.source_format,
            "canonical_dataset_id": self.canonical_dataset_id,
            "canonical_template_id": self.canonical_template_id,
            "expected_run_status": self.expected_run_status,
            "expectations": [item.to_dict() for item in self.expectations],
            "case_kind": self.case_kind,
            "metadata": _json_safe(self.metadata),
            "limitations": self.limitations,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "case_hash": self.case_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PublicReplayCase":
        if not isinstance(value, Mapping):
            raise TypeError("public replay case must be a mapping")
        return cls(
            case_id=value.get("case_id", ""),
            technique=value.get("technique", ""),
            source_archive=value.get("source_archive", ""),
            source_archive_sha256=value.get("source_archive_sha256", ""),
            source_member=value.get("source_member", ""),
            extracted_file_sha256=value.get("extracted_file_sha256", ""),
            source_format=value.get("source_format", ""),
            canonical_dataset_id=value.get("canonical_dataset_id", ""),
            canonical_template_id=value.get("canonical_template_id"),
            expected_run_status=value.get("expected_run_status", "completed"),
            expectations=tuple(ValidationExpectation.from_dict(item) for item in value.get("expectations", ())),
            case_kind=value.get("case_kind", "regression"),
            metadata=value.get("metadata", {}),
            limitations=value.get("limitations", ""),
            case_hash=value.get("case_hash", ""),
            schema_version=value.get("schema_version", ""),
        )

    def validation_case(self, input_payload: Mapping[str, Any]) -> ValidationCase:
        expected_paths = {item.path for item in self.expectations}
        expectations = list(self.expectations)
        if "metrics.run_status" not in expected_paths:
            expectations.append(
                ValidationExpectation.create(
                    path="metrics.run_status",
                    expected=self.expected_run_status,
                    expected_status="computed",
                )
            )
        if self.expected_run_status == "completed" and "metrics.canonical_dataset_id" not in expected_paths:
            expectations.append(
                ValidationExpectation.create(
                    path="metrics.canonical_dataset_id",
                    expected=self.canonical_dataset_id,
                    expected_status="computed" if self.expected_run_status == "completed" else "unavailable",
                )
            )
        if "metrics.canonical_admission_dataset_id" not in expected_paths:
            expectations.append(
                ValidationExpectation.create(
                    path="metrics.canonical_admission_dataset_id",
                    expected=self.canonical_dataset_id,
                    expected_status="computed",
                )
            )
        if self.canonical_template_id is not None and "metrics.canonical_template_id" not in expected_paths:
            expectations.append(
                ValidationExpectation.create(
                    path="metrics.canonical_template_id",
                    expected=self.canonical_template_id,
                    expected_status="computed",
                )
            )
        return ValidationCase.create(
            case_id=self.case_id,
            technique=self.technique,
            canonical_dataset_id=self.canonical_dataset_id,
            input_payload=input_payload,
            expectations=tuple(expectations),
            case_kind=self.case_kind,
            raw_sha256=self.extracted_file_sha256,
            metadata={
                **dict(self.metadata),
                "source_archive": self.source_archive,
                "source_archive_sha256": self.source_archive_sha256,
                "source_member": self.source_member,
                "source_format": self.source_format,
                "canonical_template_id": self.canonical_template_id,
                "expected_run_status": self.expected_run_status,
                "limitations": self.limitations,
                "public_replay_case_hash": self.case_hash,
            },
        )


def _archive_path(data_root: Path, relative: str) -> Path:
    root = data_root.expanduser().resolve(strict=True)
    root_stat = root.lstat()
    if root.is_symlink() or (getattr(root_stat, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
        raise ValueError("validation data root must not be a symlink or reparse point")
    candidate = (root / Path(*PurePosixPath(relative).parts)).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("source archive must stay below the validation data root") from exc
    if not candidate.is_file():
        raise ValueError("source archive is not a regular file")
    candidate_stat = candidate.lstat()
    if candidate.is_symlink() or (getattr(candidate_stat, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
        raise ValueError("source archive must not be a symlink or reparse point")
    if candidate.stat().st_size > _MAX_ARCHIVE_BYTES:
        raise ValueError("source archive exceeds the replay size limit")
    return candidate


def _zip_member_names(archive: zipfile.ZipFile, requested: str) -> tuple[str, ...]:
    normalized = requested.rstrip("/")
    names: list[str] = []
    for info in archive.infolist():
        name = info.filename.replace("\\", "/")
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("archive contains an unsafe member path")
        if name.rstrip("/") == normalized or name.startswith(normalized + "/"):
            names.append(name)
    if not names:
        raise ValueError("source member is not present in archive")
    return tuple(sorted(set(names)))


def _extract_member(archive_path: Path, member: str, destination: Path) -> tuple[Path, str]:
    with zipfile.ZipFile(archive_path) as archive:
        names = _zip_member_names(archive, member)
        if len(names) > _MAX_MEMBER_COUNT:
            raise ValueError("source member contains too many files")
        files = [name for name in names if not name.endswith("/")]
        total = 0
        for name in files:
            info = archive.getinfo(name)
            if info.is_dir() or info.file_size > _MAX_MEMBER_BYTES:
                raise ValueError("source member contains an invalid or oversized file")
            total += info.file_size
            if total > _MAX_MEMBER_BYTES:
                raise ValueError("source member exceeds the replay size limit")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise ValueError("source member contains a symlink")
        prefix = member.rstrip("/")
        is_directory = len(files) != 1 or files[0] != prefix
        target = destination / (Path(*PurePosixPath(prefix).parts).name or "member")
        if is_directory:
            target.mkdir(parents=True, exist_ok=True)
            for name in files:
                relative = PurePosixPath(name).relative_to(PurePosixPath(prefix))
                output = target.joinpath(*relative.parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, output.open("wb") as sink:
                    sink.write(source.read())
            digest = directory_manifest_sha256(_directory_entries(target))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(files[0]) as source, target.open("wb") as sink:
                sink.write(source.read())
            digest = _sha256_file(target)
        return target, digest


def _directory_entries(root: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        entries.append({"path": path.relative_to(root).as_posix(), "sha256": _sha256_file(path)})
    if not entries:
        raise ValueError("source member directory contains no files")
    entries.sort(key=lambda item: item["path"])
    return entries


def _stable_source_artifact_id(case: PublicReplayCase) -> str:
    """Derive a path-independent source identity for an external case."""

    return public_source_artifact_id(
        source_archive=case.source_archive,
        source_archive_sha256=case.source_archive_sha256,
        source_member=case.source_member,
        extracted_file_sha256=case.extracted_file_sha256,
        source_format=case.source_format,
        technique=case.technique,
    )


def public_source_artifact_id(
    *,
    source_archive: str,
    source_archive_sha256: str,
    source_member: str,
    extracted_file_sha256: str,
    source_format: str,
    technique: str,
) -> str:
    """Derive the path-independent artifact identity used by replay cases."""

    return canonical_json_hash(
        {
            "kind": "public_validation_source_artifact",
            "source_archive": _relative_member(source_archive, "source_archive"),
            "source_archive_sha256": _sha256(source_archive_sha256, "source_archive_sha256"),
            "source_member": _relative_member(source_member, "source_member"),
            "extracted_file_sha256": _sha256(extracted_file_sha256, "extracted_file_sha256"),
            "source_format": _text(source_format, "source_format").lower(),
            "technique": _text(technique, "technique").lower(),
        }
    )


def public_canonical_dataset_id(
    *,
    source_archive: str,
    source_archive_sha256: str,
    source_member: str,
    extracted_file_sha256: str,
    source_format: str,
    technique: str,
) -> str:
    """Derive the direct canonical dataset ID expected by a replay case."""

    normalized_format = _text(source_format, "source_format").lower()
    if normalized_format != "directory" and any(char in normalized_format for char in "/\\."):
        raise ValueError("source_format must be a bare file format or directory")
    artifact = RawArtifact(
        artifact_id=public_source_artifact_id(
            source_archive=source_archive,
            source_archive_sha256=source_archive_sha256,
            source_member=source_member,
            extracted_file_sha256=extracted_file_sha256,
            source_format=normalized_format,
            technique=technique,
        ),
        path="<external-public-validation>",
        technique=_text(technique, "technique").lower(),
        format=normalized_format,
        sha256=_sha256(extracted_file_sha256, "extracted_file_sha256"),
    )
    from .compute import CanonicalDataset

    return CanonicalDataset.direct_envelope(artifact).dataset_id


def _projection(
    run: ComputeRun,
    *,
    extracted_hash: str,
    expected_status: str,
    template_id: str | None,
    admitted_dataset_id: str,
) -> dict[str, Any]:
    result = run.result
    metrics = dict(result.metrics) if result is not None else {}
    metrics["run_status"] = run.status
    metrics["canonical_dataset_id"] = run.dataset.dataset_id if run.dataset is not None else None
    metrics["canonical_admission_dataset_id"] = admitted_dataset_id
    metrics["canonical_template_id"] = run.canonical_template.template_id if run.canonical_template is not None else None
    metrics["expected_run_status"] = expected_status
    manifest = list(result.metric_manifest(source=run.artifact.path)) if result is not None else []
    manifest.extend(
        [
            {"path": "metrics.run_status", "kind": "scalar", "status": "computed", "value": run.status},
            {"path": "metrics.canonical_dataset_id", "kind": "scalar", "status": "computed" if run.dataset is not None else "unavailable", "value": metrics["canonical_dataset_id"]},
            {"path": "metrics.canonical_admission_dataset_id", "kind": "scalar", "status": "computed", "value": admitted_dataset_id},
            {"path": "metrics.canonical_template_id", "kind": "scalar", "status": "computed" if run.canonical_template is not None else "unavailable", "value": metrics["canonical_template_id"]},
            {"path": "metrics.expected_run_status", "kind": "scalar", "status": "computed", "value": expected_status},
        ]
    )
    return {
        "metrics": metrics,
        "metric_manifest": manifest,
        "metadata": {
            "expected_run_status": expected_status,
            "canonical_template_id": template_id,
            "run_status": run.status,
        },
        "provenance": {
            "source_artifact_id": run.artifact.artifact_id,
            "raw_sha256": extracted_hash,
            "canonical_dataset_id": metrics["canonical_dataset_id"],
            "canonical_admission_dataset_id": admitted_dataset_id,
            "canonical_template_id": metrics["canonical_template_id"],
        },
    }


def _binding_from_run(
    run: ComputeRun,
    case: PublicReplayCase,
    artifact: RawArtifact,
    expected_dataset_id: str,
) -> None:
    if run.dataset is not None:
        if run.dataset.dataset_id != expected_dataset_id:
            raise ValueError("canonical_dataset_id does not match replay run")
        if run.dataset.source_artifact_id != run.artifact.artifact_id:
            raise ValueError("replay dataset is not bound to the run artifact")
    elif case.expected_run_status == "completed":
        raise ValueError("completed replay must produce a CanonicalDataset")


def run_public_validation_case(
    case: PublicReplayCase,
    *,
    data_root: str | Path,
    compute_service: ComputeRunService | None = None,
) -> ProjectValidationEntry:
    """Extract and replay one case twice, returning a shared batch entry."""

    if type(case) is not PublicReplayCase:
        raise TypeError("public replay requires an exact PublicReplayCase")
    root = Path(data_root).expanduser().resolve(strict=True)
    archive_path = _archive_path(root, case.source_archive)
    if _sha256_file(archive_path) != case.source_archive_sha256:
        raise ValueError("source archive SHA-256 does not match manifest")
    service = compute_service or ComputeRunService()
    with tempfile.TemporaryDirectory(prefix="polynexus-public-replay-") as temporary:
        extracted, extracted_hash = _extract_member(archive_path, case.source_member, Path(temporary))
        if extracted_hash != case.extracted_file_sha256:
            raise ValueError("extracted member SHA-256 does not match manifest")
        artifact = RawArtifact.from_path(extracted, technique=case.technique)
        if artifact.format != case.source_format:
            raise ValueError("extracted source_format does not match manifest")
        stable_artifact_id = _stable_source_artifact_id(case)
        artifact = replace(artifact, artifact_id=stable_artifact_id)
        from .compute import CanonicalDataset

        expected_dataset_id = CanonicalDataset.direct_envelope(artifact).dataset_id
        if case.canonical_dataset_id != expected_dataset_id:
            raise ValueError("canonical_dataset_id does not match the hash-bound direct envelope")
        runs = [
            service.run_direct(
                technique=case.technique,
                path=extracted,
                output_dir="",
                source_artifact_id=stable_artifact_id,
            ),
            service.run_direct(
                technique=case.technique,
                path=extracted,
                output_dir="",
                source_artifact_id=stable_artifact_id,
            ),
        ]
        for run in runs:
            _binding_from_run(run, case, artifact, expected_dataset_id)
        projections = tuple(
            _projection(
                run,
                extracted_hash=extracted_hash,
                expected_status=case.expected_run_status,
                template_id=case.canonical_template_id,
                admitted_dataset_id=expected_dataset_id,
            )
            for run in runs
        )
        validation_case = case.validation_case(
            {
                "dataset_id": case.canonical_dataset_id,
                "source_archive": case.source_archive,
                "source_member": case.source_member,
                "source_format": case.source_format,
                "extracted_file_sha256": extracted_hash,
            }
        )
        return ProjectValidationEntry.create(
            case=validation_case,
            first_output=projections[0],
            second_output=projections[1],
            raw_hash_before=extracted_hash,
            raw_hash_after=extracted_hash,
        )


def run_public_validation_manifest(
    payload: Mapping[str, Any],
    *,
    data_root: str | Path,
    compute_service: ComputeRunService | None = None,
) -> ProjectValidationBatch:
    """Replay every manifest entry in stable case-ID order."""

    if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
        raise ValueError("public replay manifest schema_version must be 1")
    entries = payload.get("entries")
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes, bytearray)) or not entries:
        raise ValueError("public replay manifest requires a non-empty entries list")
    cases = tuple(PublicReplayCase.from_dict(item) for item in entries)
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("public replay case IDs must be unique")
    validation_entries = tuple(
        run_public_validation_case(case, data_root=data_root, compute_service=compute_service)
        for case in sorted(cases, key=lambda item: item.case_id)
    )
    return run_project_validation_batch(validation_entries)


def load_public_validation_manifest(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("public replay manifest is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("public replay manifest must be a JSON object")
    return value


__all__ = [
    "PublicReplayCase",
    "load_public_validation_manifest",
    "public_canonical_dataset_id",
    "public_source_artifact_id",
    "run_public_validation_case",
    "run_public_validation_manifest",
]
