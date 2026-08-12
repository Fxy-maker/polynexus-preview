"""Immutable ARS-facing evidence package materialization."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import os
import re
import shutil
import tempfile
from typing import Any, Iterable, Mapping

from polynexus.core.agent_workflow.models import AnalysisRun

from .evidence import ProjectWorkflowRun
from .models import EvidenceItem, canonical_json
from .workspace import ProjectWorkspace


_VERSION_RE = re.compile(r"^(?P<name>.+)-v(?P<version>\d{3,})$")
_FIGURE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".svg", ".pdf", ".tif", ".tiff"})
_TABLE_SUFFIXES = frozenset({".csv", ".tsv", ".xlsx", ".xls", ".json"})


@dataclass(frozen=True)
class ResearchEvidencePackage:
    """Materialized package snapshot and its stable identity."""

    package_id: str
    version: int
    path: Path
    status: str
    package_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "version": self.version,
            "path": str(self.path),
            "status": self.status,
            "package_hash": self.package_hash,
        }


class ProjectEvidencePackager:
    """Create versioned snapshots from validated project workflow runs."""

    def __init__(self, workspace: ProjectWorkspace) -> None:
        self.workspace = workspace

    def create(
        self,
        runs: Iterable[ProjectWorkflowRun],
        *,
        relations: Iterable[Mapping[str, Any]] = (),
        package_id: str = "pa6-crystallization",
    ) -> ResearchEvidencePackage:
        run_values = tuple(runs)
        if not run_values:
            raise ValueError("at least one run is required")
        if not package_id or "/" in package_id or "\\" in package_id or package_id in {".", ".."}:
            raise ValueError("package_id must be a simple name")

        manifests: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        copied_assets: list[dict[str, str]] = []
        statuses: list[str] = []
        limitations: list[str] = []
        for run in run_values:
            manifest = self._validate_run(run)
            manifests.append(manifest)
            statuses.append(run.status)
            evidence.extend(item.to_dict() for item in run.evidence_items)
            limitations.extend(run.reason_codes)
            for item in run.evidence_items:
                limitations.extend(item.limitations)

            copied_assets.extend(self._asset_descriptors(run, package_id))

        copied_assets = self._disambiguate_assets(copied_assets)

        relation_values = [dict(value) for value in relations]
        if not relation_values:
            relation_values = [
                {
                    "type": "run_part_of_request",
                    "run_id": run.run_id,
                    "request_hash": run.request_hash,
                    "evidence_scope": "explicit_project_request",
                }
                for run in run_values
            ]
        status = "review_required" if any(value == "review_required" for value in statuses) else "completed"
        if any(value not in {"completed", "review_required"} for value in statuses):
            raise ValueError("only completed or review_required runs may be packaged")
        limitations = list(dict.fromkeys(str(value) for value in limitations if value))
        version = self._next_version(package_id)
        package_path = self.workspace.evidence_dir / f"{package_id}-v{version:03d}"
        package_path.mkdir(parents=True, exist_ok=False)
        try:
            (package_path / "figures").mkdir()
            (package_path / "tables").mkdir()
            package_manifest = {
                "package_id": package_id,
                "version": version,
                "status": status,
                "run_ids": [run.run_id for run in run_values],
                "run_manifests": [str(run.manifest_path) for run in run_values],
                "source_hashes": sorted({str(value) for manifest in manifests for value in manifest.get("source_hashes", ())}),
                "canonical_template_hashes": sorted({str(value) for manifest in manifests for value in manifest.get("canonical_template_hashes", ())}),
                "conversion_hashes": sorted({str(value) for manifest in manifests for value in manifest.get("conversion_hashes", ())}),
                "evidence_count": len(evidence),
                "asset_count": len(copied_assets),
                "evidence_item_hashes": [
                    str(item.get("item_hash", "")) for item in evidence
                ],
                "relations_hash": hashlib.sha256(
                    canonical_json({"relations": relation_values}).encode("utf-8")
                ).hexdigest(),
                "asset_hashes": self._asset_hashes(copied_assets),
                "limitations": limitations,
            }
            package_hash = hashlib.sha256(canonical_json(package_manifest).encode("utf-8")).hexdigest()
            package_manifest["package_hash"] = package_hash
            self._write_json(package_path / "manifest.json", package_manifest)
            self._write_json(package_path / "evidence.json", {"items": evidence})
            self._write_json(package_path / "relations.json", {"relations": relation_values})
            self._write_json(package_path / "limitations.json", {"limitations": limitations})
            self._copy_assets(copied_assets, package_path)
            self._write_text(package_path / "writing-input.md", self._writing_input(package_manifest, evidence, limitations))
        except Exception:
            shutil.rmtree(package_path, ignore_errors=True)
            raise
        return ResearchEvidencePackage(package_id, version, package_path, status, package_hash)

    def _validate_run(self, run: ProjectWorkflowRun) -> dict[str, Any]:
        if run.status == "blocked":
            raise ValueError("blocked run cannot be packaged")
        if run.status not in {"completed", "review_required"}:
            raise ValueError(f"run status {run.status!r} is not packageable")
        if not run.manifest_path:
            raise ValueError("run manifest is missing")
        manifest_path = Path(run.manifest_path).expanduser().resolve()
        try:
            manifest_path.relative_to(self.workspace.derived_root.resolve())
        except ValueError as exc:
            raise ValueError("run manifest must be inside .polynexus") from exc
        if not manifest_path.is_file():
            raise ValueError("run manifest is missing")
        import json
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("run manifest is invalid") from exc
        if not isinstance(manifest, dict):
            raise ValueError("run manifest is invalid")
        for key, expected in (("run_id", run.run_id), ("request_hash", run.request_hash), ("plan_hash", run.plan_hash), ("recipe_hash", run.recipe_hash), ("status", run.status)):
            if manifest.get(key) != expected:
                raise ValueError("run manifest does not match run")
        manifest_items = manifest.get("evidence_items", ())
        if not isinstance(manifest_items, list):
            raise ValueError("run manifest evidence is invalid")
        expected_hashes = {item.item_hash for item in run.evidence_items}
        actual_hashes = set()
        for value in manifest_items:
            try:
                actual_hashes.add(EvidenceItem.from_dict(value).item_hash)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("run manifest evidence is invalid") from exc
        if actual_hashes != expected_hashes:
            raise ValueError("run manifest evidence does not match run")
        analysis_payload = manifest.get("analysis_run")
        if not isinstance(analysis_payload, Mapping):
            raise ValueError("run manifest analysis record is missing")
        try:
            analysis_run = AnalysisRun.from_dict(analysis_payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("run manifest analysis record is invalid") from exc
        if analysis_run.recipe.recipe_hash != run.recipe_hash or not analysis_run.validated:
            raise ValueError("run manifest analysis record does not match run")
        if run.analysis_run is not None and analysis_run.to_dict() != run.analysis_run.to_dict():
            raise ValueError("run manifest analysis record does not match run")
        source_hashes = sorted(str(value) for value in manifest.get("source_hashes", ()))
        recipe_hashes = sorted(str(item.sha256) for item in analysis_run.recipe.artifacts if item.sha256)
        if source_hashes != recipe_hashes:
            raise ValueError("run manifest source hashes do not match recipe")
        for artifact in analysis_run.recipe.artifacts:
            if not artifact.sha256:
                raise ValueError("run manifest source hash is missing")
            source = Path(artifact.path).expanduser()
            if source.is_file():
                current_hash = _sha256_file(source)
            elif source.is_dir():
                current_hash = _sha256_directory(source)
            else:
                current_hash = None
            if current_hash != artifact.sha256:
                raise ValueError("run manifest source hash no longer matches")
        return manifest

    def _next_version(self, package_id: str) -> int:
        versions = []
        if self.workspace.evidence_dir.exists():
            for child in self.workspace.evidence_dir.iterdir():
                if not child.is_dir():
                    continue
                match = _VERSION_RE.match(child.name)
                if match and match.group("name") == package_id:
                    try:
                        versions.append(int(match.group("version")))
                    except ValueError:
                        pass
        return max(versions, default=0) + 1

    def _asset_descriptors(self, run: ProjectWorkflowRun, package_id: str) -> list[dict[str, str]]:
        assets: list[dict[str, str]] = []
        for output in run.outputs:
            source = Path(output).expanduser().resolve()
            if not source.is_file() or source.name.endswith(".json") and source.name == f"{run.run_id}.json":
                continue
            try:
                relative = source.relative_to(self.workspace.derived_root.resolve())
            except ValueError:
                continue
            lower_parts = {part.lower() for part in relative.parts}
            suffix = source.suffix.lower()
            if suffix in _FIGURE_SUFFIXES or "figures" in lower_parts or "figure" in source.stem.lower():
                kind = "figures"
            elif suffix in _TABLE_SUFFIXES or "tables" in lower_parts or "table" in source.stem.lower():
                kind = "tables"
            else:
                continue
            assets.append({"source": str(source), "kind": kind, "name": source.name})
        return assets

    @staticmethod
    def _asset_hashes(assets: list[dict[str, str]]) -> list[dict[str, str]]:
        values: list[dict[str, str]] = []
        destinations: set[tuple[str, str]] = set()
        for asset in assets:
            destination = (asset["kind"], asset["name"])
            if destination in destinations:
                raise ValueError("package asset destination collides")
            destinations.add(destination)
            values.append({
                "kind": asset["kind"],
                "name": asset["name"],
                "sha256": _sha256_file(Path(asset["source"])),
            })
        return values

    @staticmethod
    def _disambiguate_assets(assets: list[dict[str, str]]) -> list[dict[str, str]]:
        """Give same-named derived assets stable names instead of overwriting."""
        grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
        for asset in assets:
            grouped.setdefault((asset["kind"], asset["name"]), []).append(asset)
        result: list[dict[str, str]] = []
        for (_, original_name), values in grouped.items():
            sources = {value["source"] for value in values}
            if len(sources) == 1:
                result.append(dict(values[0]))
                continue
            for value in values:
                source = Path(value["source"])
                digest = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:10]
                updated = dict(value)
                updated["name"] = f"{source.stem}-{digest}{source.suffix}"
                result.append(updated)
        return result

    @staticmethod
    def _copy_assets(assets: list[dict[str, str]], package_path: Path) -> None:
        for asset in assets:
            destination = package_path / asset["kind"] / asset["name"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(asset["source"], destination)

    @staticmethod
    def _writing_input(manifest: Mapping[str, Any], evidence: list[Mapping[str, Any]], limitations: list[str]) -> str:
        lines = [
            "# Research evidence package",
            "",
            f"Package: {manifest['package_id']}-v{int(manifest['version']):03d}",
            f"Status: {manifest['status']}",
            f"Runs: {', '.join(manifest['run_ids'])}",
            "",
            "## Evidence",
        ]
        for item in evidence:
            lines.append(f"- [{item.get('status', 'unknown')}] {item.get('technique', 'unknown')}: {item.get('claim_scope', '')}")
            for interpretation in item.get("supported_interpretations", ()):
                lines.append(f"  Supported: {interpretation}")
            for conclusion in item.get("disallowed_conclusions", ()):
                lines.append(f"  Do not conclude: {conclusion}")
        lines.extend(("", "## Limitations"))
        lines.extend(f"- {value}" for value in limitations)
        return "\n".join(lines) + "\n"

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
        handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False)
        try:
            with handle:
                handle.write(canonical_json(payload))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            Path(handle.name).replace(path)
        finally:
            temporary = Path(handle.name)
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _write_text(path: Path, content: str) -> None:
        handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False)
        try:
            with handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            Path(handle.name).replace(path)
        finally:
            temporary = Path(handle.name)
            if temporary.exists():
                temporary.unlink()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_directory(path: Path) -> str:
    """Hash a directory by sorted relative file names and file digests."""
    entries: list[dict[str, str]] = []
    for candidate in sorted(path.rglob("*"), key=lambda item: item.relative_to(path).as_posix()):
        if candidate.is_symlink():
            raise ValueError("directory source contains symlink")
        if not candidate.is_file():
            continue
        entries.append({
            "path": candidate.relative_to(path).as_posix(),
            "sha256": _sha256_file(candidate),
        })
    if not entries:
        return ""
    return hashlib.sha256(canonical_json(entries).encode("utf-8")).hexdigest()


__all__ = ["ProjectEvidencePackager", "ResearchEvidencePackage"]
