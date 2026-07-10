"""Read-only discovery and evidence classification for historical figures."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable


_RENDERED_EXTENSIONS = {".svg", ".png", ".pdf", ".jpg", ".jpeg", ".tif", ".tiff"}
_GENERIC_STEMS = {"figure", "preview", "plot"}
_SUPPORTED_TECHNIQUES = {"saxs", "waxs", "dsc", "ir", "nmr"}


class LegacyRecoveryKind(str, Enum):
    REBUILDABLE = "rebuildable"
    PARTIALLY_REPAIRABLE = "partially_repairable"
    STATIC_ONLY = "static_only"


@dataclass(frozen=True)
class LegacyFigureCandidate:
    candidate_id: str
    root: Path
    kind: LegacyRecoveryKind
    technique: str
    title: str
    assets: dict[str, Path]
    document_path: Path | None
    data_paths: tuple[Path, ...]
    recipe: dict[str, object]
    reason_code: str
    suggested_action: str


class LegacyFigureRecoveryService:
    """Discover legacy candidates without mutating runs or active pointers."""

    def __init__(self, legacy_root: str | Path) -> None:
        self.legacy_root = Path(legacy_root).resolve()

    def discover(self) -> tuple[LegacyFigureCandidate, ...]:
        if not self.legacy_root.is_dir():
            return ()
        files = tuple(self._candidate_files())
        project_roots = sorted(
            {
                path.parent
                for path in files
                if path.name == "recovery_context.json"
                or path.name.lower().endswith(".pnfig.json")
            },
            key=lambda item: item.as_posix(),
        )
        consumed_assets: set[Path] = set()
        candidates: list[LegacyFigureCandidate] = []
        for project_root in project_roots:
            project_assets = tuple(
                path
                for path in files
                if path.suffix.lower() in _RENDERED_EXTENSIONS
                and _is_relative_to(path, project_root)
            )
            consumed_assets.update(project_assets)
            candidates.append(self._classify(project_root, project_assets))

        grouped_assets: dict[tuple[Path, str], list[Path]] = {}
        for path in files:
            if path in consumed_assets or path.suffix.lower() not in _RENDERED_EXTENSIONS:
                continue
            grouped_assets.setdefault((path.parent, path.stem.lower()), []).append(path)
        for (candidate_root, _stem), assets in sorted(
            grouped_assets.items(),
            key=lambda item: (item[0][0].as_posix(), item[0][1]),
        ):
            candidates.append(self._classify(candidate_root, tuple(sorted(assets))))

        unique: dict[str, LegacyFigureCandidate] = {}
        for candidate in candidates:
            candidate_id = candidate.candidate_id
            if candidate_id in unique:
                candidate_id = f"{candidate_id}.{_asset_stem(candidate.assets)}"
                candidate = LegacyFigureCandidate(
                    candidate_id=candidate_id,
                    root=candidate.root,
                    kind=candidate.kind,
                    technique=candidate.technique,
                    title=candidate.title,
                    assets=candidate.assets,
                    document_path=candidate.document_path,
                    data_paths=candidate.data_paths,
                    recipe=candidate.recipe,
                    reason_code=candidate.reason_code,
                    suggested_action=candidate.suggested_action,
                )
            unique[candidate_id] = candidate
        return tuple(unique[key] for key in sorted(unique))

    def _candidate_files(self) -> Iterable[Path]:
        for path in self.legacy_root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(self.legacy_root)
            if _is_excluded_relative_path(relative):
                continue
            yield path.resolve()

    def _classify(
        self,
        candidate_root: Path,
        rendered_assets: tuple[Path, ...],
    ) -> LegacyFigureCandidate:
        candidate_root = candidate_root.resolve()
        context = _read_json(candidate_root / "recovery_context.json")
        document_path = next(
            iter(sorted(candidate_root.glob("*.pnfig.json"))),
            None,
        )
        document = _read_json(document_path) if document_path else {}
        context_recipe = context.get("recipe", {}) if isinstance(context, dict) else {}
        document_recipe = document.get("recipe", {}) if isinstance(document, dict) else {}
        selected_recipe = (
            context_recipe
            if _valid_recipe(context_recipe)
            else document_recipe
            if isinstance(document_recipe, dict)
            else {}
        )
        recipe = dict(selected_recipe)
        technique = str(
            context.get("technique")
            or document.get("technique")
            or ""
        ).strip().lower()
        context_sources = _resolve_declared_paths(
            candidate_root,
            context.get("source_paths", []),
        )
        document_sources = _resolve_document_data_paths(candidate_root, document)

        rebuildable = (
            technique in _SUPPORTED_TECHNIQUES
            and _valid_recipe(context_recipe)
            and bool(context_sources)
            and all(path.is_file() for path in context_sources)
        )
        partial = (
            bool(document_path)
            and str(document.get("mode") or "") == "object"
            and bool(document_sources)
            and all(path.is_file() for path in document_sources)
        )
        if rebuildable:
            kind = LegacyRecoveryKind.REBUILDABLE
            data_paths = context_sources
            reason_code = "source_recipe_context_complete"
            suggested_action = "rebuild_new_run"
        elif partial:
            kind = LegacyRecoveryKind.PARTIALLY_REPAIRABLE
            data_paths = document_sources
            reason_code = "portable_document_and_data_without_manifest"
            suggested_action = "repair_new_run"
        else:
            kind = LegacyRecoveryKind.STATIC_ONLY
            data_paths = tuple(path for path in document_sources if path.is_file())
            reason_code = "rendered_asset_only"
            suggested_action = "import_static_background"

        return LegacyFigureCandidate(
            candidate_id=self._candidate_id(candidate_root, rendered_assets),
            root=candidate_root,
            kind=kind,
            technique=technique,
            title=str(
                context.get("title")
                or document.get("title")
                or document.get("figure_id")
                or candidate_root.name
            ),
            assets=_asset_roles(rendered_assets),
            document_path=document_path.resolve() if document_path else None,
            data_paths=tuple(path.resolve() for path in data_paths),
            recipe=recipe,
            reason_code=reason_code,
            suggested_action=suggested_action,
        )

    def _candidate_id(
        self,
        candidate_root: Path,
        assets: tuple[Path, ...],
    ) -> str:
        relative = candidate_root.relative_to(self.legacy_root)
        base = ".".join(relative.parts) if relative.parts else self.legacy_root.name
        stem = next((path.stem.lower() for path in assets), "")
        if stem and stem not in _GENERIC_STEMS and not list(candidate_root.glob("*.pnfig.json")):
            base = f"{base}.{stem}"
        return base


def discover_legacy_figure_paths(
    root: str | Path,
    *,
    extensions: Iterable[str],
    subdir_hints: Iterable[str],
) -> list[str]:
    """Compatibility scan owned by the explicit legacy recovery boundary."""

    root = Path(root).resolve()
    if not root.is_dir():
        return []
    allowed = {str(item).lower() for item in extensions}
    hints = {str(item).lower() for item in subdir_hints}
    discovered = []
    root_level = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        relative = path.relative_to(root)
        if _is_excluded_relative_path(relative):
            continue
        resolved = str(path.resolve())
        if path.parent == root:
            root_level.append(resolved)
        elif any(part.lower() in hints for part in relative.parts[:-1]):
            discovered.append(resolved)
    return [*sorted(discovered), *sorted(root_level)]


def _is_excluded_relative_path(path: Path) -> bool:
    for part in path.parts:
        lowered = part.lower()
        if lowered in {"runs", "legacy_recovery"}:
            return True
        if lowered.startswith(".") and lowered.endswith(".staging"):
            return True
    return False


def _read_json(path: Path | None) -> dict[str, object]:
    if path is None or not Path(path).is_file():
        return {}
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _valid_recipe(payload: object) -> bool:
    return isinstance(payload, dict) and bool(
        str(payload.get("module") or "").strip()
        and str(payload.get("function") or "").strip()
    )


def _resolve_declared_paths(root: Path, values: object) -> tuple[Path, ...]:
    if not isinstance(values, list):
        return ()
    paths = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        path = Path(text)
        paths.append(path.resolve() if path.is_absolute() else (root / path).resolve())
    return tuple(paths)


def _resolve_document_data_paths(
    root: Path,
    document: dict[str, object],
) -> tuple[Path, ...]:
    sources = document.get("data_sources", [])
    if not isinstance(sources, list):
        return ()
    paths = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        text = str(source.get("path") or "").strip()
        if not text:
            continue
        path = Path(text)
        if path.is_absolute():
            paths.append(path.resolve())
        else:
            paths.append((root / path).resolve())
    return tuple(paths)


def _asset_roles(paths: tuple[Path, ...]) -> dict[str, Path]:
    assets: dict[str, Path] = {}
    for path in sorted(paths):
        suffix = path.suffix.lower().lstrip(".")
        role = "preview" if path.stem.lower() == "preview" else suffix
        if role == "jpeg":
            role = "jpg"
        assets.setdefault(role, path.resolve())
    return assets


def _asset_stem(assets: dict[str, Path]) -> str:
    return next((path.stem.lower() for path in assets.values()), "figure")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

