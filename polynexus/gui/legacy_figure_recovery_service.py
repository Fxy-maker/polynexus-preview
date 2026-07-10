"""Map historical recovery candidates into a separate gallery surface."""

from __future__ import annotations

from pathlib import Path

from ..core.figure_document import OBJECT_MODE, STATIC_BACKGROUND_MODE
from ..core.figures.legacy_recovery import (
    LegacyFigureRecoveryService,
    LegacyRecoveryKind,
)
from .i18n import tr
from .plot_gallery_service import (
    FIGURE_STATE_OBJECT,
    FIGURE_STATE_STATIC,
    FIGURE_STATE_UNLINKED_EXPORT,
    FigureGalleryAsset,
    FigureGalleryEntry,
)


FIGURE_CATEGORY_LEGACY = "legacy"


def build_legacy_recovery_gallery_entries(
    legacy_root: str | Path,
) -> list[FigureGalleryEntry]:
    entries = []
    for candidate in LegacyFigureRecoveryService(legacy_root).discover():
        assets = tuple(
            FigureGalleryAsset(
                format=path.suffix.lower().lstrip("."),
                label=role.upper(),
                role=role,
                path=str(path),
            )
            for role, path in candidate.assets.items()
        )
        role_paths = {asset.role: asset.path for asset in assets}
        preview_path = (
            role_paths.get("preview")
            or role_paths.get("png")
            or role_paths.get("jpg")
            or role_paths.get("svg")
            or role_paths.get("pdf")
            or ""
        )
        primary_path = (
            role_paths.get("svg")
            or role_paths.get("png")
            or role_paths.get("pdf")
            or preview_path
        )
        if candidate.kind is LegacyRecoveryKind.PARTIALLY_REPAIRABLE:
            state = FIGURE_STATE_OBJECT
            document_mode = OBJECT_MODE
            editable_path = primary_path
        elif candidate.kind is LegacyRecoveryKind.STATIC_ONLY:
            state = FIGURE_STATE_STATIC
            document_mode = STATIC_BACKGROUND_MODE
            editable_path = preview_path
        else:
            state = FIGURE_STATE_UNLINKED_EXPORT
            document_mode = ""
            editable_path = ""
        entries.append(
            FigureGalleryEntry(
                figure_id=candidate.candidate_id,
                title=f"{candidate.title} — {_classification_text(candidate.kind)}",
                category=FIGURE_CATEGORY_LEGACY,
                state=state,
                preview_path=preview_path,
                primary_path=primary_path,
                editable_path=editable_path,
                document_mode=document_mode,
                asset_paths=tuple(asset.path for asset in assets),
                assets=assets,
                document_path=(
                    str(candidate.document_path) if candidate.document_path else ""
                ),
                capability_report=None,
                status=f"legacy:{candidate.kind.value}",
                error=candidate.reason_code,
            )
        )
    return entries


def _classification_text(kind: LegacyRecoveryKind) -> str:
    keys = {
        LegacyRecoveryKind.REBUILDABLE: "LEGACY_RECOVERY_REBUILDABLE",
        LegacyRecoveryKind.PARTIALLY_REPAIRABLE: "LEGACY_RECOVERY_PARTIAL",
        LegacyRecoveryKind.STATIC_ONLY: "LEGACY_RECOVERY_STATIC_ONLY",
    }
    return tr(keys[kind])
