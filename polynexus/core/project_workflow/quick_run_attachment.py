"""Project-local references to standalone quick-analysis runs."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from .workspace import ProjectWorkspace


@dataclass(frozen=True)
class QuickRunAttachment:
    quick_run_id: str
    technique: str
    source_file: str
    source_sha256: str
    output_dir: str
    manifest_path: Path


def attach_quick_run(
    workspace: ProjectWorkspace,
    *,
    quick_run_id: str,
    technique: str,
    source_file: str | Path,
    output_dir: str | Path = "",
) -> QuickRunAttachment:
    """Attach existing quick-run provenance without copying or rerunning it."""
    run_id = str(quick_run_id or "").strip()
    technique_key = str(technique or "").strip().lower()
    source = Path(source_file).expanduser().resolve()
    if not run_id or not technique_key or not source.is_file():
        raise ValueError("quick run attachment requires an existing run, technique, and source file")
    resolved_output = Path(output_dir).expanduser().resolve() if output_dir else None
    if resolved_output is not None and not resolved_output.is_dir():
        raise ValueError("quick run output directory is invalid")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest_path = workspace.runs_dir / "quick-attachments" / f"{run_id}.json"
    payload = {
        "version": 1,
        "quick_run_id": run_id,
        "technique": technique_key,
        "source_file": str(source),
        "source_sha256": source_hash,
        "output_dir": str(resolved_output) if resolved_output is not None else "",
        "attachment_kind": "reference_only",
    }
    existing = workspace.read_json(manifest_path)
    if existing is not None:
        if existing != payload:
            raise ValueError("quick run attachment conflicts with existing provenance")
    else:
        workspace.write_json(manifest_path, payload)
    return QuickRunAttachment(
        quick_run_id=run_id,
        technique=technique_key,
        source_file=str(source),
        source_sha256=source_hash,
        output_dir=payload["output_dir"],
        manifest_path=manifest_path,
    )


__all__ = ["QuickRunAttachment", "attach_quick_run"]
