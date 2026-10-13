"""Download and validate external public-data inputs for PolyNexus replay.

The repository stores only the source manifest and this utility. Archives are
kept under an external data root so third-party licensing and large files do
not become part of the source distribution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from urllib.parse import urlparse
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "docs" / "validation" / "public-validation-pack.json"
DEFAULT_DATA_ROOT = Path(os.environ.get("POLYNEXUS_VALIDATION_ROOT", "D:/PolyNexus-validation-data"))
ALGORITHMS = {"md5", "sha256"}
RAWNESS_LEVELS = {"acquisition_raw", "instrument_export", "processed_curve", "figure_or_reference_only"}
STATUSES = {"candidate", "downloaded", "inspected", "ready_for_replay", "reference_only", "license_unclear", "not_suitable"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def load_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"manifest is not valid JSON: {source}") from exc
    if not isinstance(payload, dict):
        raise ValueError("manifest root must be an object")
    return payload


def validate_manifest(payload: Mapping[str, Any], *, data_root: str | Path | None = None, require_local: bool = False) -> list[str]:
    """Return deterministic diagnostics; an empty list means valid metadata."""

    errors: list[str] = []
    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if _text(payload.get("pack_id")) == "":
        errors.append("pack_id is required")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        return errors + ["entries must be a non-empty list"]
    seen: set[str] = set()
    root = Path(data_root) if data_root is not None else None
    for index, entry in enumerate(entries):
        prefix = f"entries[{index}]"
        if not isinstance(entry, Mapping):
            errors.append(f"{prefix} must be an object")
            continue
        key = f"{_text(entry.get('dataset_id'))}:{_text(entry.get('file_name'))}"
        if key in seen:
            errors.append(f"{prefix} duplicates {key}")
        seen.add(key)
        required = ("dataset_id", "technique", "title", "record_url", "source_url", "license", "file_name", "local_relative_path", "expected_route", "rawness_level", "material_system", "status")
        for field in required:
            if _text(entry.get(field)) == "":
                errors.append(f"{prefix}.{field} is required")
        if _text(entry.get("license")) not in {"CC BY 4.0", "CC BY 3.0", "CC0 1.0", "MIT", "Apache-2.0"}:
            errors.append(f"{prefix}.license is not an allow-listed public license")
        if entry.get("license_verified") is not True:
            errors.append(f"{prefix}.license_verified must be true")
        if _text(entry.get("rawness_level")) not in RAWNESS_LEVELS:
            errors.append(f"{prefix}.rawness_level is invalid")
        if _text(entry.get("status")) not in STATUSES:
            errors.append(f"{prefix}.status is invalid")
        relative = PurePosixPath(_text(entry.get("local_relative_path")).replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"{prefix}.local_relative_path must stay below the data root")
        checksum = entry.get("source_checksum")
        if not isinstance(checksum, Mapping) or _text(checksum.get("algorithm")).lower() not in ALGORITHMS or len(_text(checksum.get("value"))) != (32 if _text(checksum.get("algorithm")).lower() == "md5" else 64):
            errors.append(f"{prefix}.source_checksum is invalid")
        if root is not None and (require_local or entry.get("status") in {"downloaded", "inspected", "ready_for_replay"}):
            local = root / Path(*relative.parts)
            if not local.is_file():
                errors.append(f"{prefix} local file is missing: {local}")
            else:
                expected_md5 = _text(checksum.get("value")).lower()
                if _md5(local) != expected_md5:
                    errors.append(f"{prefix} source MD5 does not match: {local}")
                expected_sha = _text(entry.get("local_sha256")).lower()
                if expected_sha and _sha256(local) != expected_sha:
                    errors.append(f"{prefix} local_sha256 does not match: {local}")
    return errors


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _local_path(root: Path, entry: Mapping[str, Any]) -> Path:
    relative = PurePosixPath(_text(entry["local_relative_path"]).replace("\\", "/"))
    return root.joinpath(*relative.parts)


def _download(url: str, destination: Path, expected_md5: str, retries: int = 4) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            offset = temporary.stat().st_size if temporary.exists() else 0
            request_url = _preferred_download_url(url)
            request = urllib.request.Request(
                request_url,
                headers={"Range": f"bytes={offset}-{offset + 64 * 1024 * 1024 - 1}"} if offset else {},
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                # Some mirrors ignore Range and return a complete 200 response.
                # Truncating in that case prevents duplicate bytes on resume.
                append = bool(offset and getattr(response, "status", 200) == 206)
                if not append:
                    offset = 0
                with temporary.open("ab" if append else "wb") as output:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        output.write(block)
            if expected_md5 and _md5(temporary) != expected_md5.lower():
                raise ValueError("downloaded file MD5 does not match Zenodo checksum")
            temporary.replace(destination)
            return {"status": "downloaded", "bytes": destination.stat().st_size, "local_sha256": _sha256(destination), "source_md5": _md5(destination)}
        except urllib.error.HTTPError as exc:
            if exc.code == 416 and temporary.exists():
                temporary.unlink()
                continue
            last_error = exc
            time.sleep(min(2 ** attempt, 10))
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last_error = exc
            time.sleep(min(2 ** attempt, 10))
    raise RuntimeError(f"download failed after {retries} attempts: {url}") from last_error


def _preferred_download_url(url: str) -> str:
    """Prefer Zenodo's browser download endpoint, which honors HTTP ranges."""

    parsed = urlparse(url)
    marker = "/api/records/"
    if parsed.netloc == "zenodo.org" and marker in parsed.path and parsed.path.endswith("/content"):
        parts = parsed.path.split("/")
        try:
            record_id = parts[3]
            file_name = parts[5]
        except IndexError:
            return url
        return f"https://zenodo.org/records/{record_id}/files/{file_name}?download=1"
    return url


def inspect_archive(path: Path, expected_md5: str = "") -> dict[str, Any]:
    if not path.is_file():
        return {"status": "missing", "path": str(path)}
    source_md5 = _md5(path)
    if expected_md5 and source_md5 != expected_md5.lower():
        return {"status": "checksum_mismatch", "path": str(path), "bytes": path.stat().st_size, "source_md5": source_md5, "sha256": _sha256(path)}
    if not zipfile.is_zipfile(path):
        return {"status": "non_zip", "path": str(path), "bytes": path.stat().st_size, "source_md5": source_md5, "sha256": _sha256(path)}
    with zipfile.ZipFile(path) as archive:
        members = []
        for info in archive.infolist():
            suffix = Path(info.filename).suffix.lower() or "<none>"
            members.append({"name": info.filename, "bytes": info.file_size, "suffix": suffix})
    suffix_counts: dict[str, int] = {}
    for member in members:
        suffix = str(member["suffix"])
        suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
    return {"status": "inspected", "path": str(path), "bytes": path.stat().st_size, "source_md5": source_md5, "sha256": _sha256(path), "member_count": len(members), "suffix_counts": dict(sorted(suffix_counts.items())), "members": members}


def command_validate(args: argparse.Namespace) -> int:
    payload = load_manifest(args.manifest)
    errors = validate_manifest(payload, data_root=args.data_root, require_local=args.require_local)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"valid: {len(payload['entries'])} manifest entries")
    return 0


def command_download(args: argparse.Namespace) -> int:
    payload = load_manifest(args.manifest)
    errors = validate_manifest(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    root = Path(args.data_root)
    reports = root / "public" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    report: list[dict[str, Any]] = []
    for entry in payload["entries"]:
        if args.dataset_id and entry["dataset_id"] not in args.dataset_id:
            continue
        if args.technique and entry["technique"] not in args.technique:
            continue
        destination = _local_path(root, entry)
        if destination.is_file() and _md5(destination) == _text(entry["source_checksum"]["value"]).lower():
            result = {"status": "already_present", "bytes": destination.stat().st_size, "local_sha256": _sha256(destination), "source_md5": _md5(destination)}
        else:
            print(f"download {entry['dataset_id']}/{entry['file_name']}", flush=True)
            result = _download(_text(entry["source_url"]), destination, _text(entry["source_checksum"]["value"]))
        result.update({"dataset_id": entry["dataset_id"], "file_name": entry["file_name"], "local_relative_path": entry["local_relative_path"]})
        report.append(result)
    (reports / "download-report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"downloaded/verified {len(report)} entries; report: {reports / 'download-report.json'}")
    return 0


def command_inspect(args: argparse.Namespace) -> int:
    payload = load_manifest(args.manifest)
    root = Path(args.data_root)
    reports = root / "public" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    output: list[dict[str, Any]] = []
    for entry in payload["entries"]:
        result = inspect_archive(_local_path(root, entry), _text(entry["source_checksum"]["value"]))
        result.update({"dataset_id": entry["dataset_id"], "technique": entry["technique"], "file_name": entry["file_name"]})
        output.append(result)
    target = reports / "archive-inspection.json"
    target.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(f"inspected {len(output)} entries; report: {target}")
    return 0 if all(item["status"] == "inspected" for item in output) else 1


def command_lock(args: argparse.Namespace) -> int:
    """Write an external lock manifest with local hashes and inspection summaries."""

    payload = load_manifest(args.manifest)
    root = Path(args.data_root)
    inspection_path = root / "public" / "reports" / "archive-inspection.json"
    inspection: dict[tuple[Any, Any], Mapping[str, Any]] = {}
    if inspection_path.is_file():
        raw = json.loads(inspection_path.read_text(encoding="utf-8"))
        inspection = {
            (item.get("dataset_id"), item.get("file_name")): item
            for item in raw
            if isinstance(item, Mapping)
        }
    locked = json.loads(json.dumps(payload))
    for entry in locked["entries"]:
        local = _local_path(root, entry)
        report = inspection.get((entry["dataset_id"], entry["file_name"]), {})
        if local.is_file() and _md5(local) == _text(entry["source_checksum"]["value"]).lower():
            entry["local_sha256"] = _sha256(local)
            entry["status"] = "inspected" if report.get("status") == "inspected" else "downloaded"
        else:
            entry.pop("local_sha256", None)
            entry["status"] = "candidate"
        if report:
            entry["inspection"] = {
                key: report[key]
                for key in ("status", "bytes", "member_count", "suffix_counts")
                if key in report
            }
    locked["lock_schema_version"] = 1
    locked["source_manifest_sha256"] = _sha256(Path(args.manifest))
    locked["data_root"] = str(root)
    target = root / "public" / "manifests" / "validation-manifest.lock.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(locked, indent=2, sort_keys=True), encoding="utf-8")
    errors = validate_manifest(locked, data_root=root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"wrote {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--require-local", action="store_true")
    validate.set_defaults(function=command_validate)
    download = subparsers.add_parser("download")
    download.add_argument("--dataset-id", action="append", help="download only selected dataset ids")
    download.add_argument("--technique", action="append", help="download only selected techniques")
    download.set_defaults(function=command_download)
    subparsers.add_parser("inspect").set_defaults(function=command_inspect)
    subparsers.add_parser("lock").set_defaults(function=command_lock)
    args = parser.parse_args(argv)
    return int(args.function(args))


if __name__ == "__main__":
    raise SystemExit(main())
