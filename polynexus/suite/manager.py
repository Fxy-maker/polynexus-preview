"""Safe discovery and transactional installation of optional Suite skills."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from polynexus import __version__
from polynexus.utils.config import get_user_config_dir

from .contracts import SuiteComponent, SuiteComponentStatus, SuiteManifest, SuiteStatus
from .manifest import load_lock, load_manifest, write_lock


def _hash_path(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    if not path.is_dir():
        return ""
    for child in sorted((item for item in path.rglob("*") if item.is_file()), key=lambda item: item.relative_to(path).as_posix()):
        relative = child.relative_to(path).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        with child.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _compatible_core(core_version: str, core_range: str) -> bool:
    requirement = str(core_range or "").strip()
    if not requirement or requirement in {"*", "any"}:
        return True
    major = str(core_version).split(".", 1)[0]
    if requirement.endswith(".x"):
        return requirement[:-2] == major
    return requirement == core_version


def _safe_destination(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError("suite destination escapes Codex skills directory")
    return candidate


class SuiteManager:
    """Own Suite component discovery, install/update, and rollback operations."""

    def __init__(
        self,
        *,
        manifest_path: str | Path | None = None,
        codex_skills_dir: str | Path | None = None,
        lock_path: str | Path | None = None,
        core_version: str | None = None,
        backup_dir: str | Path | None = None,
    ) -> None:
        default_manifest = Path(__file__).resolve().parents[2] / "config" / "suite_manifest.json"
        self.manifest_path = Path(manifest_path or default_manifest).expanduser()
        self.codex_skills_dir = Path(codex_skills_dir or self._default_codex_skills_dir()).expanduser()
        self.lock_path = Path(lock_path or (get_user_config_dir() / "suite-lock.json")).expanduser()
        self.core_version = str(core_version or __version__)
        self.backup_dir = Path(backup_dir or (get_user_config_dir() / "suite-backups")).expanduser()

    @staticmethod
    def _default_codex_skills_dir() -> Path:
        configured = os.getenv("CODEX_HOME", "").strip()
        if configured:
            return Path(configured).expanduser() / "skills"
        return Path.home() / ".codex" / "skills"

    def _manifest(self) -> SuiteManifest:
        return load_manifest(self.manifest_path)

    def doctor(self) -> SuiteStatus:
        try:
            manifest = self._manifest()
        except ValueError as exc:
            return SuiteStatus("invalid", str(self.codex_skills_dir), self.core_version, reason_codes=("manifest_invalid", str(exc)))
        statuses: list[SuiteComponentStatus] = []
        for component in manifest.components:
            target = _safe_destination(self.codex_skills_dir, component.destination)
            if not target.is_dir():
                statuses.append(SuiteComponentStatus(component.component_id, "missing", component.version, str(target), ("component_missing",)))
                continue
            reasons: list[str] = []
            if any(not (target / relative).is_file() for relative in component.required_files):
                reasons.append("required_file_missing")
            installed = load_lock(self.lock_path).get("components", {})
            recorded = installed.get(component.component_id) if isinstance(installed, dict) else None
            if recorded and str(recorded.get("version", recorded) if isinstance(recorded, dict) else recorded) != component.version:
                reasons.append("version_mismatch")
            statuses.append(SuiteComponentStatus(component.component_id, "installed" if not reasons else "invalid", component.version, str(target), tuple(reasons)))
        overall = "ready" if statuses and all(item.status == "installed" for item in statuses) else "component_missing"
        if not self.codex_skills_dir.exists():
            overall = "codex_not_found"
        return SuiteStatus(overall, str(self.codex_skills_dir), self.core_version, tuple(statuses), () if overall == "ready" else (overall,))

    def install(self, component_id: str, *, confirm: bool = False, source_override: str | Path | None = None) -> SuiteStatus:
        if not confirm:
            return SuiteStatus("confirmation_required", str(self.codex_skills_dir), self.core_version, reason_codes=("user_confirmation_required",))
        try:
            component = next(item for item in self._manifest().components if item.component_id == component_id)
        except (ValueError, StopIteration) as exc:
            reason = "manifest_invalid" if isinstance(exc, ValueError) else "component_unknown"
            return SuiteStatus("failed", str(self.codex_skills_dir), self.core_version, reason_codes=(reason,))
        if not _compatible_core(self.core_version, component.core_range):
            return SuiteStatus("incompatible_component", str(self.codex_skills_dir), self.core_version, reason_codes=("incompatible_component",))
        staging: Path | None = None
        backup: Path | None = None
        target = _safe_destination(self.codex_skills_dir, component.destination)
        try:
            staging = self._stage_source(component, source_override)
            if _hash_path(staging) != component.sha256:
                raise _InstallFailure("integrity_check_failed")
            self._validate_staged(staging, component)
            if target.exists():
                self.backup_dir.mkdir(parents=True, exist_ok=True)
                backup = self.backup_dir / f"{component.component_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
                shutil.move(str(target), str(backup))
            self._activate_staged(staging, target)
            self._write_component_lock(component)
            staging = None
            return SuiteStatus("installed", str(self.codex_skills_dir), self.core_version, (SuiteComponentStatus(component.component_id, "installed", component.version, str(target)),))
        except _InstallFailure as exc:
            self._restore(target, backup)
            return SuiteStatus("failed", str(self.codex_skills_dir), self.core_version, reason_codes=(exc.reason,))
        except Exception:
            self._restore(target, backup)
            return SuiteStatus("activation_rolled_back", str(self.codex_skills_dir), self.core_version, reason_codes=("activation_rolled_back",))
        finally:
            if staging is not None and staging.exists():
                shutil.rmtree(staging, ignore_errors=True)

    def update(self, component_id: str | None = None, *, confirm: bool = False) -> SuiteStatus:
        manifest = self._manifest()
        selected = [item.component_id for item in manifest.components if component_id is None or item.component_id == component_id]
        if not selected:
            return SuiteStatus("failed", str(self.codex_skills_dir), self.core_version, reason_codes=("component_unknown",))
        results = [self.install(item, confirm=confirm) for item in selected]
        failed = next((item for item in results if item.status not in {"installed"}), None)
        return failed or results[0]

    def rollback(self, component_id: str | None = None) -> SuiteStatus:
        if not self.backup_dir.is_dir():
            return SuiteStatus("failed", str(self.codex_skills_dir), self.core_version, reason_codes=("backup_missing",))
        candidates = sorted((item for item in self.backup_dir.iterdir() if item.is_dir() and (component_id is None or item.name.startswith(f"{component_id}-"))), reverse=True)
        if not candidates:
            return SuiteStatus("failed", str(self.codex_skills_dir), self.core_version, reason_codes=("backup_missing",))
        backup = candidates[0]
        target = self.codex_skills_dir / backup.name.split("-", 1)[0]
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(backup), str(target))
        return SuiteStatus("rolled_back", str(self.codex_skills_dir), self.core_version, reason_codes=())

    def _stage_source(self, component: SuiteComponent, source_override: str | Path | None) -> Path:
        source = str(source_override or component.source)
        parsed = urllib.parse.urlparse(source)
        # Keep staging on the same volume as the Codex destination so the final
        # activation can use an atomic ``os.replace`` on Windows as well.
        staging_parent = self.codex_skills_dir.parent
        staging_parent.mkdir(parents=True, exist_ok=True)
        staging_root = Path(tempfile.mkdtemp(prefix=".polynexus-suite-", dir=staging_parent))
        downloaded = staging_root / "source"
        if parsed.scheme in {"http", "https"}:
            urllib.request.urlretrieve(source, downloaded)
            source_path = downloaded
        else:
            source_path = Path(parsed.path if parsed.scheme == "file" else source).expanduser()
            if not source_path.exists():
                raise _InstallFailure("source_unavailable")
        staged = staging_root / "payload"
        if source_path.is_dir():
            shutil.copytree(source_path, staged)
        elif zipfile.is_zipfile(source_path):
            staged.mkdir()
            with zipfile.ZipFile(source_path) as archive:
                for info in archive.infolist():
                    member = Path(info.filename)
                    if member.is_absolute() or ".." in member.parts:
                        raise _InstallFailure("integrity_check_failed")
                archive.extractall(staged)
            children = list(staged.iterdir())
            if len(children) == 1 and children[0].is_dir() and (children[0] / "SKILL.md").is_file():
                nested = children[0]
                flattened = staged.with_name("payload-flat")
                shutil.move(str(nested), str(flattened))
                shutil.rmtree(staged)
                staged = flattened
        else:
            raise _InstallFailure("source_format_unsupported")
        return staged

    @staticmethod
    def _validate_staged(staged: Path, component: SuiteComponent) -> None:
        for required in component.required_files:
            candidate = (staged / required).resolve()
            if staged.resolve() not in candidate.parents or not candidate.is_file():
                raise _InstallFailure("required_file_missing")

    @staticmethod
    def _activate_staged(staged: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged, target)

    def _write_component_lock(self, component: SuiteComponent) -> None:
        lock = load_lock(self.lock_path)
        lock.update({"schema_version": 1, "core_version": self.core_version, "adapter_version": "1", "handoff_schema": component.handoff_schema})
        components = lock.setdefault("components", {})
        components[component.component_id] = {"version": component.version, "sha256": component.sha256, "destination": component.destination, "source": component.source}
        write_lock(self.lock_path, lock)

    @staticmethod
    def _restore(target: Path, backup: Path | None) -> None:
        if backup is None or not backup.exists():
            return
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(backup), str(target))


class _InstallFailure(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


__all__ = ["SuiteManager"]
