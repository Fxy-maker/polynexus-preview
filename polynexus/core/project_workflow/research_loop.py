"""Small, append-only orchestration shell for Codex and ARS research tasks.

This module deliberately stores references to the existing project/run/evidence
contracts instead of copying scientific values.  It is safe to use from a CLI,
Codex adapter, or a future GUI task view; all deterministic work remains owned
by :class:`ProjectWorkflowService`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence
from uuid import uuid4

from .models import _freeze, _public, canonical_json
from .workspace import ProjectWorkspace


RESEARCH_SCHEMA_VERSION = 1

TASK_STATES = frozenset(
    {
        "draft",
        "awaiting_mapping_confirmation",
        "ready",
        "running",
        "checkpointed",
        "ars_in_progress",
        "awaiting_human",
        "revision_required",
        "export_ready",
        "completed",
        "blocked",
    }
)

_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"draft", "awaiting_mapping_confirmation", "blocked"}),
    "awaiting_mapping_confirmation": frozenset(
        {"awaiting_mapping_confirmation", "ready", "blocked"}
    ),
    "ready": frozenset({"ready", "running", "awaiting_mapping_confirmation", "blocked"}),
    "running": frozenset({"running", "checkpointed", "awaiting_human", "blocked"}),
    "checkpointed": frozenset(
        {"checkpointed", "ars_in_progress", "revision_required", "awaiting_human", "blocked"}
    ),
    "ars_in_progress": frozenset(
        {"ars_in_progress", "revision_required", "awaiting_human", "export_ready", "blocked"}
    ),
    "awaiting_human": frozenset(
        {"awaiting_human", "ready", "checkpointed", "ars_in_progress", "revision_required", "export_ready", "blocked"}
    ),
    "revision_required": frozenset(
        {"revision_required", "running", "awaiting_human", "ars_in_progress", "export_ready", "blocked"}
    ),
    "export_ready": frozenset({"export_ready", "completed", "revision_required", "blocked"}),
    "completed": frozenset({"completed"}),
    "blocked": frozenset({"blocked", "awaiting_mapping_confirmation", "ready"}),
}

ACTION_KINDS = frozenset({"edit", "recompute", "ask_human"})
ACTION_STATES = frozenset({"pending", "resolved", "rejected"})
_SAFE_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
_HANDOFF_RECORD_VERSION = 1
_ARS_COMPLETION_RECORD_VERSION = 1
_ARS_COMPLETION_STATES = frozenset(
    {"passed", "pass", "complete", "completed", "verified", "finalized"}
)


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _strings(values: Iterable[Any]) -> tuple[str, ...]:
    return tuple(str(value) for value in values)


@dataclass(frozen=True)
class ResearchTask:
    """One immutable snapshot of a project research task."""

    task_id: str
    project_id: str
    research_question: str
    data_scope: tuple[str, ...] = ()
    target_journal: str | None = None
    status: str = "draft"
    stage: str = "created"
    revision: int = 0
    parent_revision: int | None = None
    parent_hash: str | None = None
    mapping_proposal: Mapping[str, Any] = field(default_factory=dict)
    mapping_confirmation: Mapping[str, Any] = field(default_factory=dict)
    confirmed_mapping: Mapping[str, Any] = field(default_factory=dict)
    graph_hash: str | None = None
    run_ids: tuple[str, ...] = ()
    package_paths: tuple[str, ...] = ()
    handoff_ids: tuple[str, ...] = ()
    action_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    version: int = RESEARCH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.version != RESEARCH_SCHEMA_VERSION:
            raise ValueError("research task version is invalid")
        if (
            not _SAFE_IDENTIFIER.fullmatch(str(self.task_id))
            or not self.project_id
            or not self.research_question.strip()
        ):
            raise ValueError("research task identity and question are required")
        if self.status not in TASK_STATES:
            raise ValueError(f"research task status is invalid: {self.status}")
        if self.revision < 0:
            raise ValueError("research task revision is invalid")
        object.__setattr__(self, "data_scope", _strings(self.data_scope))
        object.__setattr__(self, "run_ids", _strings(self.run_ids))
        object.__setattr__(self, "package_paths", _strings(self.package_paths))
        object.__setattr__(self, "handoff_ids", _strings(self.handoff_ids))
        object.__setattr__(self, "action_ids", _strings(self.action_ids))
        for name in (
            "mapping_proposal",
            "mapping_confirmation",
            "confirmed_mapping",
            "metadata",
        ):
            object.__setattr__(self, name, _freeze(getattr(self, name)))
        object.__setattr__(self, "target_journal", None if self.target_journal is None else str(self.target_journal))
        expected = _digest(self._content_payload())
        if self.content_hash and self.content_hash != expected:
            raise ValueError("research task content hash does not match its content")
        object.__setattr__(self, "content_hash", expected)

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        research_question: str,
        data_scope: Sequence[str] = (),
        target_journal: str | None = None,
        task_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "ResearchTask":
        return cls(
            task_id=str(task_id or f"task-{uuid4().hex[:16]}"),
            project_id=str(project_id),
            research_question=str(research_question),
            data_scope=tuple(data_scope),
            target_journal=target_journal,
            metadata=metadata or {},
        )

    def _content_payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "research_question": self.research_question,
            "data_scope": list(self.data_scope),
            "target_journal": self.target_journal,
            "status": self.status,
            "stage": self.stage,
            "revision": self.revision,
            "parent_revision": self.parent_revision,
            "parent_hash": self.parent_hash,
            "mapping_proposal": _public(self.mapping_proposal),
            "mapping_confirmation": _public(self.mapping_confirmation),
            "confirmed_mapping": _public(self.confirmed_mapping),
            "graph_hash": self.graph_hash,
            "run_ids": list(self.run_ids),
            "package_paths": list(self.package_paths),
            "handoff_ids": list(self.handoff_ids),
            "action_ids": list(self.action_ids),
            "metadata": _public(self.metadata),
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._content_payload()
        payload["content_hash"] = self.content_hash
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchTask":
        if int(payload.get("version", -1)) != RESEARCH_SCHEMA_VERSION:
            raise ValueError("research task version is invalid")
        return cls(
            task_id=str(payload["task_id"]),
            project_id=str(payload["project_id"]),
            research_question=str(payload["research_question"]),
            data_scope=payload.get("data_scope", ()),
            target_journal=payload.get("target_journal"),
            status=str(payload.get("status", "draft")),
            stage=str(payload.get("stage", "created")),
            revision=int(payload.get("revision", 0)),
            parent_revision=(None if payload.get("parent_revision") is None else int(payload["parent_revision"])),
            parent_hash=payload.get("parent_hash"),
            mapping_proposal=payload.get("mapping_proposal", {}),
            mapping_confirmation=payload.get("mapping_confirmation", {}),
            confirmed_mapping=payload.get("confirmed_mapping", {}),
            graph_hash=payload.get("graph_hash"),
            run_ids=payload.get("run_ids", ()),
            package_paths=payload.get("package_paths", ()),
            handoff_ids=payload.get("handoff_ids", ()),
            action_ids=payload.get("action_ids", ()),
            metadata=payload.get("metadata", {}),
            content_hash=str(payload.get("content_hash", "")),
            version=int(payload.get("version", RESEARCH_SCHEMA_VERSION)),
        )

    def evolve(self, *, revision: int | None = None, parent: "ResearchTask" | None = None, **changes: Any) -> "ResearchTask":
        if {"task_id", "project_id", "research_question"}.intersection(changes):
            raise ValueError("research task identity is immutable")
        next_status = str(changes.get("status", self.status))
        if next_status not in _TRANSITIONS[self.status]:
            raise ValueError(f"invalid research task transition: {self.status} -> {next_status}")
        base = {
            "revision": self.revision + 1 if revision is None else int(revision),
            "parent_revision": self.revision if parent is None else parent.revision,
            "parent_hash": self.content_hash if parent is None else parent.content_hash,
            "content_hash": "",
        }
        base.update(changes)
        return replace(self, **base)


@dataclass(frozen=True)
class ResearchAction:
    """A typed action returned by ARS and routed by Codex."""

    action_id: str
    task_id: str
    kind: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    status: str = "pending"
    resolution: Mapping[str, Any] = field(default_factory=dict)
    revision: int = 1
    parent_hash: str | None = None
    content_hash: str = ""
    version: int = RESEARCH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.version != RESEARCH_SCHEMA_VERSION:
            raise ValueError("research action version is invalid")
        if not _SAFE_IDENTIFIER.fullmatch(str(self.action_id)):
            raise ValueError("research action id is invalid")
        if not _SAFE_IDENTIFIER.fullmatch(str(self.task_id)) or self.kind not in ACTION_KINDS:
            raise ValueError("research action kind or task id is invalid")
        if self.status not in ACTION_STATES:
            raise ValueError("research action status is invalid")
        if not isinstance(self.payload, Mapping) or not isinstance(self.resolution, Mapping):
            raise ValueError("research action payload must be a mapping")
        object.__setattr__(self, "payload", _freeze(self.payload))
        object.__setattr__(self, "resolution", _freeze(self.resolution))
        expected = _digest(self._content_payload())
        if self.content_hash and self.content_hash != expected:
            raise ValueError("research action content hash does not match its content")
        object.__setattr__(self, "content_hash", expected)

    @classmethod
    def create(cls, *, task_id: str, kind: str, payload: Mapping[str, Any] | None = None, action_id: str | None = None) -> "ResearchAction":
        kind = str(kind)
        if kind not in ACTION_KINDS:
            raise ValueError(f"unsupported research action kind: {kind}")
        return cls(
            action_id=str(action_id or f"action-{uuid4().hex[:16]}"),
            task_id=str(task_id),
            kind=kind,
            payload={} if payload is None else payload,
        )

    def _content_payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "action_id": self.action_id,
            "task_id": self.task_id,
            "kind": self.kind,
            "payload": _public(self.payload),
            "status": self.status,
            "resolution": _public(self.resolution),
            "revision": self.revision,
            "parent_hash": self.parent_hash,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._content_payload()
        payload["content_hash"] = self.content_hash
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchAction":
        return cls(
            action_id=str(payload["action_id"]),
            task_id=str(payload["task_id"]),
            kind=str(payload["kind"]),
            payload=payload.get("payload", {}),
            status=str(payload.get("status", "pending")),
            resolution=payload.get("resolution", {}),
            revision=int(payload.get("revision", 1)),
            parent_hash=payload.get("parent_hash"),
            content_hash=str(payload.get("content_hash", "")),
            version=int(payload.get("version", RESEARCH_SCHEMA_VERSION)),
        )


class ResearchTaskStore:
    """Persist task snapshots and actions in an append-only project area."""

    def __init__(self, workspace: ProjectWorkspace) -> None:
        self.workspace = workspace
        self.root = workspace.research_dir
        self.tasks_root = self.root / "tasks"
        self.index_path = self.root / "index.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.tasks_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def open(cls, root: str | Path) -> "ResearchTaskStore":
        return cls(ProjectWorkspace.open(root))

    def create_task(self, **kwargs: Any) -> ResearchTask:
        task = ResearchTask.create(**kwargs)
        task_dir = self._task_dir(task.task_id)
        if task_dir.exists():
            raise ValueError("research task already exists")
        task_dir.mkdir(parents=True)
        (task_dir / "revisions").mkdir()
        (task_dir / "actions").mkdir()
        (task_dir / "handoffs").mkdir()
        stored = task.evolve(revision=1, parent_revision=None, parent_hash=None)
        self._write_revision(stored)
        self._update_index(stored)
        return stored

    def list_tasks(self) -> tuple[ResearchTask, ...]:
        values: list[ResearchTask] = []
        if not self.tasks_root.exists():
            return ()
        for task_dir in sorted(self.tasks_root.iterdir(), key=lambda p: p.name):
            if task_dir.is_dir():
                try:
                    values.append(self.load(task_dir.name))
                except (OSError, TypeError, ValueError, json.JSONDecodeError):
                    continue
        return tuple(values)

    def load(self, task_id: str) -> ResearchTask:
        task_dir = self._task_dir(task_id)
        revision_dir = task_dir / "revisions"
        files = sorted(revision_dir.glob("task-*.json"), key=lambda p: p.name)
        if not files:
            raise ValueError("research task has no revisions")
        pointer_revision: int | None = None
        pointer_hash: str | None = None
        if self.index_path.is_file():
            try:
                index = json.loads(self.index_path.read_text(encoding="utf-8"))
                entry = index.get("tasks", {}).get(task_id, {}) if isinstance(index, dict) else {}
                if isinstance(entry, Mapping):
                    if entry.get("revision") is not None:
                        pointer_revision = int(entry["revision"])
                    if entry.get("content_hash"):
                        pointer_hash = str(entry["content_hash"])
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                pointer_revision = pointer_hash = None
        valid: list[ResearchTask] = []
        for path in files:
            match = re.fullmatch(r"task-(\d{6})\.json", path.name)
            if not match:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, Mapping) or not payload.get("content_hash"):
                    raise ValueError("research task content hash is missing")
                current = ResearchTask.from_dict(payload)
            except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
                if pointer_revision is not None and int(match.group(1)) > pointer_revision:
                    continue
                if pointer_revision is None and valid:
                    continue
                raise ValueError(f"research revision is invalid: {path.name}") from exc
            if current.task_id != task_id or current.revision != int(match.group(1)):
                raise ValueError("research revision filename is invalid")
            if not valid:
                if current.revision != 1 or current.parent_revision is not None or current.parent_hash is not None:
                    raise ValueError("first research revision is invalid")
            else:
                previous = valid[-1]
                if (current.revision != previous.revision + 1
                        or current.parent_revision != previous.revision
                        or current.parent_hash != previous.content_hash):
                    if pointer_revision is not None and current.revision <= pointer_revision:
                        raise ValueError("research revision parent link is invalid")
                    continue
            valid.append(current)
        if not valid:
            raise ValueError("research task has no valid revisions")
        latest = valid[-1]
        if pointer_revision is not None:
            pointed = next((item for item in valid if item.revision == pointer_revision), None)
            if pointed is None or (pointer_hash and pointed.content_hash != pointer_hash):
                raise ValueError("research task index pointer is invalid")
        return latest

    def transition(self, task_id: str, status: str, **changes: Any) -> ResearchTask:
        current = self.load(task_id)
        immutable = {
            "task_id",
            "project_id",
            "research_question",
            "version",
            "content_hash",
            # A transition always derives these from the loaded head.  Letting
            # callers supply them would create a revision whose filename or
            # parent link no longer describes the append-only lineage.
            "revision",
            "parent_revision",
            "parent_hash",
            "parent",
        }
        if immutable.intersection(changes):
            raise ValueError("research task identity is immutable")
        next_task = current.evolve(status=str(status), **changes)
        self._write_revision(next_task)
        self._update_index(next_task)
        return next_task

    def append(self, task: ResearchTask) -> ResearchTask:
        current = self.load(task.task_id)
        if (
            task.project_id != current.project_id
            or task.research_question != current.research_question
            or task.version != current.version
        ):
            raise ValueError("research task identity is immutable")
        if task.revision != current.revision + 1:
            raise ValueError("research revision must append exactly one step")
        if task.parent_revision != current.revision or task.parent_hash != current.content_hash:
            raise ValueError("research revision parent does not match latest")
        self._write_revision(task)
        self._update_index(task)
        return task

    def save_action(self, action: ResearchAction) -> ResearchAction:
        task_dir = self._task_dir(action.task_id)
        if not task_dir.is_dir():
            raise ValueError("research action task does not exist")
        destination = task_dir / "actions" / f"{action.action_id}.json"
        if destination.exists():
            existing_payload = json.loads(destination.read_text(encoding="utf-8"))
            if not isinstance(existing_payload, Mapping) or not existing_payload.get("content_hash"):
                raise ValueError("research action content hash is missing")
            existing = ResearchAction.from_dict(existing_payload)
            if existing.action_id != action.action_id or existing.task_id != action.task_id:
                raise ValueError("research action identity is invalid")
            if existing != action:
                raise ValueError("research action is immutable")
            return existing
        self._write_once(destination, action.to_dict())
        return action

    def load_action(self, task_id: str, action_id: str) -> ResearchAction:
        # Validate both components before constructing a filesystem path.  A
        # malformed ARS response must never escape this task's action folder.
        self._task_dir(task_id)
        if not isinstance(action_id, str) or not _SAFE_IDENTIFIER.fullmatch(action_id):
            raise ValueError("research action id is invalid")
        action_dir = self._task_dir(task_id) / "actions"
        path = action_dir / f"{action_id}.json"
        if not path.is_file():
            raise ValueError("research action is missing")
        try:
            base_payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(base_payload, Mapping) or not base_payload.get("content_hash"):
                raise ValueError("research action content hash is missing")
            if str(base_payload.get("action_id", "")) != action_id or str(base_payload.get("task_id", "")) != task_id:
                raise ValueError("research action identity is invalid")
            latest = ResearchAction.from_dict(base_payload)
            if (
                latest.revision != 1
                or latest.parent_hash is not None
                or latest.status != "pending"
                or latest.resolution
            ):
                raise ValueError("research action base lineage is invalid")

            # Resolution siblings are immutable append records.  Validate the
            # filename as well as the JSON payload so a valid record cannot be
            # hidden behind an ambiguous or mismatched path.
            resolution_files: list[tuple[int, Path]] = []
            for resolution_path in sorted(action_dir.glob(f"{action_id}-r*.json"), key=lambda item: item.name):
                match = re.fullmatch(rf"{re.escape(action_id)}-r([0-9]+)\.json", resolution_path.name)
                if match is None:
                    raise ValueError("research action resolution filename is invalid")
                resolution_files.append((int(match.group(1)), resolution_path))
            for revision_number, resolution_path in sorted(resolution_files, key=lambda item: item[0]):
                resolution_payload = json.loads(resolution_path.read_text(encoding="utf-8"))
                if not isinstance(resolution_payload, Mapping) or not resolution_payload.get("content_hash"):
                    raise ValueError("research action content hash is missing")
                candidate = ResearchAction.from_dict(resolution_payload)
                if candidate.action_id != action_id or candidate.task_id != task_id:
                    raise ValueError("research action lineage is invalid")
                if (
                    revision_number != candidate.revision
                    or candidate.revision != latest.revision + 1
                    or candidate.parent_hash != latest.content_hash
                    or candidate.kind != latest.kind
                    or candidate.payload != latest.payload
                    or candidate.status not in {"resolved", "rejected"}
                    or not candidate.resolution
                ):
                    raise ValueError("research action lineage is invalid")
                latest = candidate
            return latest
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("research action is invalid") from exc

    def _task_dir(self, task_id: str) -> Path:
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", task_id):
            raise ValueError("research task id is invalid")
        return self.tasks_root / task_id

    def _write_revision(self, task: ResearchTask) -> None:
        destination = self._task_dir(task.task_id) / "revisions" / f"task-{task.revision:06d}.json"
        self._write_once(destination, task.to_dict())

    def _update_index(self, task: ResearchTask) -> None:
        payload: dict[str, Any] = {"version": RESEARCH_SCHEMA_VERSION, "tasks": {}}
        if self.index_path.is_file():
            try:
                loaded = json.loads(self.index_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict) and isinstance(loaded.get("tasks"), dict):
                    payload["tasks"] = dict(loaded["tasks"])
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                pass
        payload["tasks"][task.task_id] = {
            "revision": task.revision,
            "content_hash": task.content_hash,
        }
        self.workspace.write_json(self.index_path, payload)

    @staticmethod
    def _write_once(destination: Path, payload: Mapping[str, Any]) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise ValueError(f"immutable research file already exists: {destination.name}")
        handle = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False
        )
        temporary = Path(handle.name)
        try:
            with handle:
                handle.write(canonical_json(payload))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, destination)
            except (FileExistsError, OSError):
                if destination.exists():
                    raise ValueError(f"immutable research file already exists: {destination.name}")
                temporary.replace(destination)
        finally:
            if temporary.exists():
                temporary.unlink()


class ResearchLoopService:
    """Codex-facing explicit research stages over existing project services."""

    def __init__(self, store: ResearchTaskStore, project_service: Any | None = None) -> None:
        self.store = store
        if project_service is None:
            from .service import ProjectWorkflowService

            project_service = ProjectWorkflowService(store.workspace)
        self.project_service = project_service
        self._run_cache: dict[str, Any] = {}

    @classmethod
    def open(cls, root: str | Path, *, project_service: Any | None = None) -> "ResearchLoopService":
        return cls(ResearchTaskStore.open(root), project_service=project_service)

    def create_task(self, **kwargs: Any) -> ResearchTask:
        return self.store.create_task(**kwargs)

    def resume(self, task_id: str) -> ResearchTask:
        task = self.store.load(task_id)
        self._validate_restart_integrity(task)
        # A checkpoint after a recompute intentionally retains the historical
        # handoff IDs until a new package is handed off.  Such a checkpoint is
        # not yet an ARS stage, so only validate a pinned handoff when resuming
        # a stage that is allowed to consume it.
        if task.status in {
            "ars_in_progress",
            "awaiting_human",
            "revision_required",
            "export_ready",
            "completed",
        }:
            handoff = self._require_validated_handoff(task)
            if task.metadata.get("ars_completion_id") is not None:
                self._require_ars_completion(task, handoff)
        return task

    def _validate_restart_integrity(self, task: ResearchTask) -> None:
        """Validate persisted bindings before using a task after a restart.

        A task revision only contains references to immutable project objects.
        The references therefore have to be checked against their on-disk
        manifests before a resumed process can route work or export a paper.
        A result held in this service's short-lived cache is accepted only for
        an empty manifest path; a newly opened service has an empty cache and
        consequently fails closed for the same incomplete record.
        """
        metadata = task.metadata
        raw_refs = metadata.get("run_refs", ())
        if raw_refs is None:
            raw_refs = ()
        if isinstance(raw_refs, (str, bytes, bytearray)) or not isinstance(raw_refs, (list, tuple)):
            raise ValueError("research run references are invalid")

        run_refs: list[Mapping[str, Any]] = []
        for raw_ref in raw_refs:
            if not isinstance(raw_ref, Mapping):
                raise ValueError("research run reference is invalid")
            # ``checkpoint`` historically placed a package-only reference in
            # this list.  It has no run manifest and is not an analysis run;
            # keep it out of the run binding set while validating its shape.
            if "run_id" not in raw_ref:
                if (
                    set(raw_ref).issubset({"package_path", "package_hash"})
                    and isinstance(raw_ref.get("package_path"), str)
                    and isinstance(raw_ref.get("package_hash"), str)
                    and raw_ref.get("package_path")
                    and raw_ref.get("package_hash")
                ):
                    continue
                raise ValueError("research run reference is missing run id")
            run_refs.append(raw_ref)

        expected_run_ids = tuple(str(value) for value in task.run_ids if str(value))
        if task.status in {
            "running",
            "checkpointed",
            "ars_in_progress",
            "awaiting_human",
            "revision_required",
            "export_ready",
            "completed",
        } and not expected_run_ids:
            raise ValueError("research run binding is missing")
        if len(expected_run_ids) != len(task.run_ids) or len(set(expected_run_ids)) != len(expected_run_ids):
            raise ValueError("research run IDs are invalid")
        if tuple(str(ref.get("run_id", "")) for ref in run_refs) != expected_run_ids:
            raise ValueError("research run references do not match task runs")

        for ref in run_refs:
            run_id = str(ref.get("run_id", ""))
            manifest_value = ref.get("manifest_path")
            if not isinstance(manifest_value, str) or not manifest_value.strip():
                # Older in-process fakes do not persist a manifest.  Never
                # carry that exception across a real service restart.
                if run_id in self._run_cache and not manifest_value:
                    continue
                raise ValueError("research run manifest is missing")
            manifest_path = Path(manifest_value).expanduser().resolve()
            if not manifest_path.is_file():
                raise ValueError("research run manifest is missing")
            try:
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError("research run manifest is invalid") from exc
            if not isinstance(payload, Mapping):
                raise ValueError("research run manifest is invalid")
            if str(payload.get("run_id", "")) != run_id:
                raise ValueError("research run manifest run id does not match")
            expected_request_hash = str(ref.get("request_hash", ""))
            manifest_request_hash = str(payload.get("request_hash", ""))
            if not expected_request_hash or not manifest_request_hash or expected_request_hash != manifest_request_hash:
                raise ValueError("research run manifest request hash does not match")
            for field_name in ("plan_hash", "recipe_hash", "status"):
                expected = ref.get(field_name)
                if expected not in (None, "") and str(payload.get(field_name, "")) != str(expected):
                    raise ValueError(f"research run manifest {field_name} does not match")

        seen_actions: set[str] = set()
        for action_id in task.action_ids:
            if not isinstance(action_id, str) or not _SAFE_IDENTIFIER.fullmatch(action_id):
                raise ValueError("research action id is invalid")
            if action_id in seen_actions:
                raise ValueError("research action ids are duplicated")
            seen_actions.add(action_id)
            action = self.store.load_action(task.task_id, action_id)
            if action.task_id != task.task_id:
                raise ValueError("research action belongs to another task")

        route = self._recompute_route(task)
        if route is not None:
            routed_action = self.store.load_action(task.task_id, route["action_id"])
            if (
                routed_action.kind != "recompute"
                or routed_action.status not in {"pending", "resolved"}
                or route["action_id"] not in seen_actions
            ):
                raise ValueError("recompute route action is invalid")

        if task.status == "completed":
            self._validate_export_artifacts(task)

    @staticmethod
    def _artifact_binding(path: Path) -> dict[str, Any]:
        """Return the immutable file facts recorded for a formal export."""
        digest = hashlib.sha256()
        size = 0
        try:
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    size += len(chunk)
                    digest.update(chunk)
        except OSError as exc:
            raise ValueError("export artifact is missing") from exc
        return {"path": str(path.resolve()), "sha256": digest.hexdigest(), "size": size}

    def _validate_export_artifacts(self, task: ResearchTask) -> None:
        raw_artifacts = task.metadata.get("export_artifacts")
        if isinstance(raw_artifacts, (str, bytes, bytearray)) or not isinstance(raw_artifacts, (list, tuple)):
            raise ValueError("export artifact integrity metadata is missing")
        if not raw_artifacts:
            raise ValueError("export artifact integrity metadata is missing")
        observed: list[dict[str, Any]] = []
        for raw_artifact in raw_artifacts:
            if not isinstance(raw_artifact, Mapping):
                raise ValueError("export artifact integrity metadata is invalid")
            raw_path = raw_artifact.get("path")
            raw_hash = raw_artifact.get("sha256")
            raw_size = raw_artifact.get("size")
            if (
                not isinstance(raw_path, str)
                or not raw_path.strip()
                or not isinstance(raw_hash, str)
                or not re.fullmatch(r"[0-9a-fA-F]{64}", raw_hash)
                or isinstance(raw_size, bool)
                or not isinstance(raw_size, int)
                or raw_size < 0
            ):
                raise ValueError("export artifact integrity metadata is invalid")
            candidate = Path(raw_path).expanduser().resolve()
            if not candidate.is_file():
                raise ValueError("export artifact integrity is invalid")
            actual = self._artifact_binding(candidate)
            expected = {
                "path": str(candidate),
                "sha256": raw_hash.lower(),
                "size": raw_size,
            }
            if actual != expected:
                raise ValueError("export artifact integrity is invalid")
            observed.append(actual)
        raw_paths = task.metadata.get("export_paths")
        if raw_paths is not None:
            if isinstance(raw_paths, (str, bytes, bytearray)) or not isinstance(raw_paths, (list, tuple)):
                raise ValueError("export paths are invalid")
            if tuple(str(Path(value).expanduser().resolve()) for value in raw_paths) != tuple(item["path"] for item in observed):
                raise ValueError("export artifact paths do not match")

    def inspect(self, task_id: str) -> ResearchTask:
        task = self.store.load(task_id)
        paths = tuple(path for path in task.data_scope if ".polynexus" not in Path(path).parts)
        graph = self.project_service.inspect(paths)
        metadata = dict(task.metadata)
        metadata["discovered_paths"] = list(paths)
        metadata["graph_hash"] = str(getattr(graph, "graph_hash", ""))
        return self.store.transition(
            task_id,
            "awaiting_mapping_confirmation",
            stage="inspect",
            graph_hash=str(getattr(graph, "graph_hash", "")) or None,
            metadata=metadata,
        )

    def propose_mapping(self, task_id: str, mapping: Mapping[str, Any]) -> ResearchTask:
        task = self.store.load(task_id)
        if task.status not in {"draft", "awaiting_mapping_confirmation", "ready", "blocked"}:
            raise ValueError("mapping can only be proposed before formal analysis")
        proposal = dict(mapping)
        confirmation = {
            "confirmation_id": f"mapping-{_digest(proposal)[:16]}",
            "kind": "data_mapping",
            "status": "pending",
        }
        return self.store.transition(
            task_id,
            "awaiting_mapping_confirmation",
            stage="mapping",
            mapping_proposal=proposal,
            mapping_confirmation=confirmation,
        )

    def confirm_mapping(self, task_id: str, *, approved: bool, approver: str, note: str = "") -> ResearchTask:
        task = self.store.load(task_id)
        if not task.mapping_proposal or task.status != "awaiting_mapping_confirmation":
            raise ValueError("mapping confirmation is not pending")
        if type(approved) is not bool:
            raise ValueError("mapping confirmation decision must be a boolean")
        if not str(approver).strip():
            raise ValueError("mapping confirmation approver is required")
        confirmation = dict(task.mapping_confirmation)
        confirmation.update({"status": "approved" if approved else "rejected", "approver": str(approver), "note": str(note)})
        if not approved:
            return self.store.transition(
                task_id,
                "blocked",
                stage="mapping",
                mapping_confirmation=confirmation,
            )
        return self.store.transition(
            task_id,
            "ready",
            stage="mapping_confirmed",
            mapping_confirmation=confirmation,
            confirmed_mapping=dict(task.mapping_proposal),
        )

    def run(
        self,
        task_id: str,
        *,
        requested_outputs: Sequence[str] = ("figures", "tables", "writing_input"),
        request_parameters: Mapping[str, Any] | None = None,
    ) -> ResearchTask:
        task = self.store.load(task_id)
        if task.status == "revision_required":
            raise ValueError("formal run requires the pending recompute action route")
        if task.status != "ready" or not task.confirmed_mapping:
            raise ValueError("formal run requires mapping confirmation")
        if self._recompute_route(task) is not None:
            raise ValueError("formal run requires the pending recompute action route")

        try:
            request = self._analysis_request(
                task,
                requested_outputs=requested_outputs,
                request_parameters=request_parameters,
            )
        except (TypeError, ValueError) as exc:
            self.store.transition(
                task_id,
                "blocked",
                stage="analysis",
                metadata={**dict(task.metadata), "run_error": str(exc)},
            )
            raise
        running = self.store.transition(task_id, "running", stage="analysis")
        return self._execute_prepared_run(running, request)

    def _analysis_request(
        self,
        task: ResearchTask,
        *,
        requested_outputs: Sequence[str],
        request_parameters: Mapping[str, Any] | None,
    ) -> Any:
        """Build the immutable Core request before advancing the task head."""
        from .models import AnalysisRequest

        confirmed = _public(task.confirmed_mapping)
        # A confirmed mapping may be wrapped with explicit request parameters
        # (for example ``nmr.liquid_h``).  Keep the complete envelope in task
        # provenance, but pass only its canonical mapping and user-confirmed
        # parameters through the existing AnalysisRequest contract.
        mapping_proposal: Any = confirmed
        effective_parameters: dict[str, Any] = {}
        if request_parameters is not None:
            if not isinstance(request_parameters, Mapping):
                raise ValueError("request_parameters must be a mapping")
            effective_parameters.update(_public(request_parameters))
        if isinstance(confirmed, Mapping):
            candidate_mapping = confirmed.get("mapping_proposal")
            if isinstance(candidate_mapping, Mapping):
                mapping_proposal = candidate_mapping
            candidate_parameters = confirmed.get("request_parameters", {})
            if candidate_parameters is not None:
                if not isinstance(candidate_parameters, Mapping):
                    raise ValueError("confirmed mapping request_parameters must be a mapping")
                effective_parameters.update(_public(candidate_parameters))
        # Internal bindings are authoritative and cannot be replaced by a
        # user-supplied parameter with the same name.
        effective_parameters.update(
            {
                "research_task_id": task.task_id,
                # This orchestration revision is deliberately part of the
                # request identity.  A recompute therefore cannot reuse and
                # overwrite the immutable run manifest from an earlier pass.
                "research_task_revision": task.revision + 1,
                "mapping_proposal": _public(mapping_proposal),
                "confirmed_mapping": confirmed,
            }
        )
        return AnalysisRequest.create(
            question=task.research_question,
            requested_outputs=tuple(requested_outputs),
            data_scope=task.data_scope,
            parameters=effective_parameters,
        )

    def _execute_prepared_run(self, running: ResearchTask, request: Any) -> ResearchTask:
        """Delegate a prevalidated request to the shared workflow service."""
        try:
            result = self.project_service.run(request)
        except Exception as exc:
            return self.store.transition(
                running.task_id,
                "blocked",
                stage="analysis",
                metadata={**dict(running.metadata), "run_error": str(exc)},
            )
        result_status = str(getattr(result, "status", "blocked"))
        run_id = str(getattr(result, "run_id", ""))
        if result_status in {"completed", "review_required"} and not run_id:
            return self.store.transition(
                running.task_id,
                "blocked",
                stage="analysis",
                metadata={**dict(running.metadata), "run_status": result_status, "run_error": "run_id_missing"},
            )
        if run_id and run_id in running.run_ids:
            return self.store.transition(
                running.task_id,
                "blocked",
                stage="analysis",
                run_ids=running.run_ids,
                metadata={
                    **dict(running.metadata),
                    "run_status": result_status,
                    "run_error": "run_id_reused",
                },
            )
        if run_id:
            self._run_cache[run_id] = result
        run_ref = {
            "run_id": run_id,
            "manifest_path": str(getattr(result, "manifest_path", "") or ""),
            "request_hash": str(getattr(result, "request_hash", request.request_hash)),
            "plan_hash": str(getattr(result, "plan_hash", "")),
            "recipe_hash": getattr(result, "recipe_hash", None),
        }
        if result_status not in {"completed", "review_required"}:
            return self.store.transition(
                running.task_id,
                "blocked",
                stage="analysis",
                run_ids=tuple((*running.run_ids, run_id)) if run_id else running.run_ids,
                metadata={**dict(running.metadata), "run_status": result_status,
                          "run_reasons": list(getattr(result, "reason_codes", ())),
                          "run_refs": [*dict(running.metadata).get("run_refs", []), run_ref]},
            )
        return self.store.transition(
            running.task_id,
            "checkpointed",
            stage="analysis_complete",
            run_ids=tuple((*running.run_ids, run_id)) if run_id else running.run_ids,
            metadata={
                **{
                    key: value
                    for key, value in dict(running.metadata).items()
                    if key != "recompute_route"
                },
                "run_status": result_status,
                "run_refs": [*dict(running.metadata).get("run_refs", []), run_ref],
            },
        )

    def recompute(
        self,
        task_id: str,
        *,
        requested_outputs: Sequence[str] = ("figures", "tables", "writing_input"),
    ) -> ResearchTask:
        """Consume one pending ARS recompute action and create a new run.

        The existing run is never edited.  Resolving the action first records
        why the branch was accepted, then the ordinary ``run`` stage delegates
        the actual deterministic computation to ``ProjectWorkflowService``.
        """
        task = self.store.load(task_id)
        self._require_validated_handoff(task)
        if task.status != "revision_required":
            raise ValueError("recompute requires a pending revision")
        route = self._recompute_route(task)
        if route is None:
            pending = self._pending_recompute_action(task)
            route = self._recompute_route_for_action(pending, requested_outputs)
            task = self.store.transition(
                task_id,
                "revision_required",
                stage="recompute_routed",
                metadata={**dict(task.metadata), "recompute_route": route},
            )
        action = self.store.load_action(task_id, route["action_id"])
        if action.kind != "recompute":
            raise ValueError("recompute route action is invalid")
        if action.status == "pending":
            task = self.resolve_action(
                task_id,
                action.action_id,
                approved=True,
                note="routed to PolyNexus run",
            )
            action = self.store.load_action(task_id, action.action_id)
        if (
            action.status != "resolved"
            or action.resolution.get("approved") is not True
        ):
            raise ValueError("recompute route action is not approved")
        return self._execute_recompute_run(task, route)

    def _recompute_route(self, task: ResearchTask) -> dict[str, Any] | None:
        """Load one durable recompute route, rejecting malformed task state."""
        route = task.metadata.get("recompute_route")
        if route is None:
            return None
        if not isinstance(route, Mapping):
            raise ValueError("recompute route is invalid")
        action_id = route.get("action_id")
        parameters = route.get("request_parameters")
        outputs = route.get("requested_outputs")
        if (
            not isinstance(action_id, str)
            or not _SAFE_IDENTIFIER.fullmatch(action_id)
            or not isinstance(parameters, Mapping)
            or isinstance(outputs, (str, bytes, bytearray))
            or not isinstance(outputs, (list, tuple))
        ):
            raise ValueError("recompute route is invalid")
        normalized = {
            "action_id": action_id,
            "request_parameters": _public(parameters),
            "requested_outputs": [str(value) for value in outputs],
        }
        try:
            canonical_json(normalized)
        except (TypeError, ValueError) as exc:
            raise ValueError("recompute route is invalid") from exc
        return normalized

    def _pending_recompute_action(self, task: ResearchTask) -> ResearchAction:
        for action_id in task.action_ids:
            action = self.store.load_action(task.task_id, action_id)
            if action.kind == "recompute" and action.status == "pending":
                return action
        raise ValueError("no pending recompute action")

    @staticmethod
    def _recompute_route_for_action(
        action: ResearchAction,
        requested_outputs: Sequence[str],
    ) -> dict[str, Any]:
        payload = _public(action.payload)
        if not isinstance(payload, Mapping):
            raise ValueError("recompute action payload is invalid")
        parameters: dict[str, Any] = {
            "recompute_action_id": action.action_id,
            "recompute_payload": payload,
        }
        candidate = payload.get("request_parameters")
        if candidate is not None:
            if not isinstance(candidate, Mapping):
                raise ValueError("recompute request_parameters must be a mapping")
            parameters.update(_public(candidate))
        route = {
            "action_id": action.action_id,
            "request_parameters": parameters,
            "requested_outputs": [str(value) for value in requested_outputs],
        }
        try:
            canonical_json(route)
        except (TypeError, ValueError) as exc:
            raise ValueError("recompute request parameters are invalid") from exc
        return route

    def _execute_recompute_run(
        self,
        task: ResearchTask,
        route: Mapping[str, Any],
    ) -> ResearchTask:
        """Run only a durable, approved ARS recompute route."""
        if task.status != "revision_required" or not task.confirmed_mapping:
            raise ValueError("recompute requires a pending revision")
        try:
            request = self._analysis_request(
                task,
                requested_outputs=tuple(route["requested_outputs"]),
                request_parameters=route["request_parameters"],
            )
        except (TypeError, ValueError) as exc:
            self.store.transition(
                task.task_id,
                "blocked",
                stage="recompute",
                metadata={**dict(task.metadata), "run_error": str(exc)},
            )
            raise
        running = self.store.transition(task.task_id, "running", stage="recompute")
        return self._execute_prepared_run(running, request)

    def checkpoint(self, task_id: str, *, package_path: str | Path | None = None) -> ResearchTask:
        task = self.store.load(task_id)
        self._validate_restart_integrity(task)
        if task.status not in {"checkpointed", "running", "revision_required"}:
            raise ValueError("checkpoint requires an analysis result")
        paths = list(task.package_paths)
        refs = list(task.metadata.get("run_refs", ()))
        # ProjectWorkflowService is the sole producer of working evidence.
        # Reconstruct the public run envelope from its immutable manifest so a
        # resumed process cannot fabricate a package reference.
        if refs and hasattr(self.project_service, "upsert_working_run"):
            from .evidence import ProjectWorkflowRun
            from .models import EvidenceItem
            from polynexus.core.agent_workflow.models import AnalysisRun
            for ref in refs:
                manifest_path = ref.get("manifest_path") if isinstance(ref, Mapping) else None
                run_id = str(ref.get("run_id", "")) if isinstance(ref, Mapping) else ""
                cached = self._run_cache.get(run_id)
                if cached is not None:
                    self.project_service.upsert_working_run(cached)
                    continue
                if not manifest_path:
                    continue
                payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
                analysis_payload = payload.get("analysis_run")
                if not isinstance(analysis_payload, Mapping):
                    continue
                run = ProjectWorkflowRun(
                    run_id=str(payload.get("run_id", ref.get("run_id", ""))),
                    request_hash=str(payload.get("request_hash", ref.get("request_hash", ""))),
                    plan_hash=str(payload.get("plan_hash", ref.get("plan_hash", ""))),
                    recipe_hash=payload.get("recipe_hash", ref.get("recipe_hash")),
                    status=str(payload.get("status", "")),
                    outputs=tuple(str(v) for v in payload.get("outputs", ())),
                    evidence_items=tuple(EvidenceItem.from_dict(v) for v in payload.get("evidence_items", ())),
                    manifest_path=str(manifest_path),
                    analysis_run=AnalysisRun.from_dict(analysis_payload),
                    reason_codes=tuple(str(v) for v in payload.get("reason_codes", ())),
                )
                self.project_service.upsert_working_run(run)
            freeze_working_evidence = getattr(self.project_service, "freeze_working_evidence", None)
            if callable(freeze_working_evidence):
                # A project working set may contain runs from several
                # ResearchTask instances.  Restrict this package to IDs that
                # belong to the current task and are still present after the
                # upserts above (a recompute can replace an older source-keyed
                # entry).  If the project service exposes no status method,
                # the explicit task IDs remain the narrowest safe boundary;
                # the freeze API itself validates them against its index.
                selected_run_ids = tuple(
                    dict.fromkeys(
                        str(run_id)
                        for run_id in task.run_ids
                        if str(run_id).strip()
                    )
                )
                if not selected_run_ids:
                    raise ValueError("current task run IDs are empty")
                status_method = getattr(self.project_service, "working_evidence_status", None)
                if callable(status_method):
                    status = status_method()
                    available_raw = (
                        status.get("run_ids")
                        if isinstance(status, Mapping)
                        else getattr(status, "run_ids", None)
                    )
                    if isinstance(available_raw, (str, bytes, bytearray)):
                        raise ValueError("current working evidence run IDs are invalid")
                    if available_raw is None:
                        raise ValueError("current working evidence run IDs are unavailable")
                    try:
                        available_run_ids = {str(run_id) for run_id in available_raw}
                    except TypeError as exc:
                        raise ValueError("current working evidence run IDs are invalid") from exc
                    selected_run_ids = tuple(
                        run_id for run_id in selected_run_ids if run_id in available_run_ids
                    )
                if not selected_run_ids:
                    raise ValueError("no current task run IDs remain in working evidence")
                frozen = freeze_working_evidence(
                    package_id=f"research-{task.task_id}",
                    selected_run_ids=selected_run_ids,
                )
                paths.append(str(getattr(frozen, "path", "")))
                refs.append({"package_path": str(getattr(frozen, "path", "")), "package_hash": str(getattr(frozen, "package_hash", ""))})
        if package_path is not None:
            paths.append(str(Path(package_path).expanduser().absolute()))
        return self.store.transition(
            task_id,
            "checkpointed",
            stage="checkpoint",
            package_paths=tuple(dict.fromkeys(path for path in paths if path)),
            metadata={**dict(task.metadata), "run_refs": refs},
        )

    def handoff_to_ars(self, task_id: str, package_path: str | Path) -> ResearchTask:
        from polynexus.suite.handoff import build_suite_handoff

        task = self.store.load(task_id)
        self._validate_restart_integrity(task)
        if task.status != "checkpointed":
            raise ValueError("ARS handoff requires a checkpoint")
        resolved_package = str(Path(package_path).expanduser().resolve())
        known = {str(Path(p).expanduser().resolve()) for p in task.package_paths}
        if resolved_package not in known:
            raise ValueError("handoff package belongs to another task")
        payload = build_suite_handoff(package_path, task_id=task_id)
        declared_task_id = str(payload.get("task_id", ""))
        if declared_task_id and declared_task_id != task_id:
            raise ValueError("handoff belongs to another task")
        package_payload = payload.get("package")
        if not isinstance(package_payload, Mapping):
            raise ValueError("handoff package binding is missing")
        package_payload_path = package_payload.get("path")
        if not isinstance(package_payload_path, str) or not package_payload_path.strip():
            raise ValueError("handoff package path binding is missing")
        if str(Path(package_payload_path).expanduser().resolve()) != resolved_package:
            raise ValueError("handoff package path does not match task package")
        raw_run_ids = payload.get("run_ids")
        if isinstance(raw_run_ids, (str, bytes)) or not isinstance(raw_run_ids, (list, tuple, set, frozenset)):
            raise ValueError("handoff package run ids are missing")
        package_run_ids = tuple(dict.fromkeys(str(value) for value in raw_run_ids if str(value)))
        if not package_run_ids:
            raise ValueError("handoff package run ids are missing")
        task_run_ids = set(task.run_ids)
        if not set(package_run_ids).issubset(task_run_ids) or task.run_ids[-1] not in package_run_ids:
            raise ValueError("handoff package run does not belong to the latest task run")
        # A package generated by the project packager carries copied run
        # manifests.  Bind those manifests back to this task whenever the
        # producer recorded the task parameter; legacy packages without that
        # optional field remain readable but cannot claim a conflicting task.
        package_root = Path(resolved_package)
        package_manifest_path = package_root / "manifest.json"
        if not package_manifest_path.is_file():
            raise ValueError("handoff package manifest is missing")
        if package_manifest_path.is_file():
            try:
                package_manifest = json.loads(package_manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError("handoff package manifest is invalid") from exc
            if not isinstance(package_manifest, Mapping):
                raise ValueError("handoff package manifest is invalid")
            manifest_package_hash = str(package_manifest.get("package_hash", "")).strip().lower()
            payload_package_hash = str(package_payload.get("package_hash", "")).strip().lower()
            if (
                len(manifest_package_hash) != 64
                or any(char not in "0123456789abcdef" for char in manifest_package_hash)
                or payload_package_hash != manifest_package_hash
            ):
                raise ValueError("handoff package hash is missing or does not match its manifest")
            declared_ids = tuple(str(value) for value in package_manifest.get("run_ids", ()))
            if set(declared_ids) != set(package_run_ids):
                raise ValueError("handoff package run IDs do not match its manifest")
            raw_run_manifests = package_manifest.get("run_manifests")
            if isinstance(raw_run_manifests, (str, bytes)) or not isinstance(
                raw_run_manifests, (list, tuple, set, frozenset)
            ):
                raise ValueError("handoff package run manifest bindings are missing")
            declared_manifest_paths = {
                str(value).replace("\\", "/") for value in raw_run_manifests
            }
            expected_manifest_paths = {f"runs/{run_id}.json" for run_id in package_run_ids}
            if declared_manifest_paths != expected_manifest_paths:
                raise ValueError("handoff package run manifest bindings do not cover all runs")
            for run_id in package_run_ids:
                run_path = package_root / "runs" / f"{run_id}.json"
                if not run_path.is_file():
                    raise ValueError("handoff package run manifest is missing")
                try:
                    run_payload = json.loads(run_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                    raise ValueError("handoff package run manifest is invalid") from exc
                if not isinstance(run_payload, Mapping) or str(run_payload.get("run_id", "")) != run_id:
                    raise ValueError("handoff package run manifest is invalid")
                request_parameters = run_payload.get("request_parameters", {})
                if not isinstance(request_parameters, Mapping):
                    raise ValueError("handoff package run ownership is missing")
                owner = request_parameters.get("research_task_id")
                if owner is None or str(owner) != task_id:
                    raise ValueError("handoff package run belongs to another task")
        if payload.get("status") != "ready":
            return self.store.transition(task_id, "blocked", stage="ars_handoff", metadata={**dict(task.metadata), "handoff_error": payload})
        handoff_id = str(payload.get("handoff_id") or f"handoff-{_digest(payload)[:16]}")
        if not _SAFE_IDENTIFIER.fullmatch(handoff_id):
            raise ValueError("handoff id is invalid")
        destination = self.store._task_dir(task_id) / "handoffs" / f"{handoff_id}.json"
        record = self._handoff_record(
            task_id=task_id,
            handoff_id=handoff_id,
            payload=payload,
            package_root=package_root,
            package_run_ids=package_run_ids,
        )
        if destination.exists():
            try:
                existing = json.loads(destination.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError("handoff record is invalid") from exc
            if existing != record:
                raise ValueError("handoff record is immutable")
        else:
            self.store._write_once(destination, record)
        handoffs = list(task.handoff_ids)
        handoffs.append(handoff_id)
        metadata = dict(task.metadata)
        metadata.pop("ars_completion_id", None)
        metadata.pop("ars_completion_binding", None)
        bindings = metadata.get("handoff_bindings", {})
        if not isinstance(bindings, Mapping):
            raise ValueError("task handoff bindings are invalid")
        next_bindings = dict(bindings)
        next_bindings[handoff_id] = self._handoff_binding(record)
        metadata["handoff_bindings"] = next_bindings
        return self.store.transition(
            task_id,
            "ars_in_progress",
            stage="ars_handoff",
            handoff_ids=tuple(dict.fromkeys(handoffs)),
            package_paths=tuple(dict.fromkeys((*task.package_paths, resolved_package))),
            metadata=metadata,
        )

    def _handoff_record(
        self,
        *,
        task_id: str,
        handoff_id: str,
        payload: Mapping[str, Any],
        package_root: Path,
        package_run_ids: Sequence[str],
    ) -> dict[str, Any]:
        """Freeze a handoff response with independently checkable bindings.

        The suite's response is a transport projection, not its own durable
        object.  This wrapper makes it an append-only task record while keeping
        the original top-level fields readable by existing clients.
        """
        record = _public(payload)
        if not isinstance(record, Mapping):
            raise ValueError("handoff record is invalid")
        record = dict(record)
        package = record.get("package")
        if not isinstance(package, Mapping):
            raise ValueError("handoff package binding is missing")
        bound_package = dict(_public(package))
        bound_package["path"] = str(package_root.resolve())
        record.update(
            {
                "handoff_record_version": _HANDOFF_RECORD_VERSION,
                "handoff_id": handoff_id,
                "task_id": task_id,
                "package": bound_package,
                "run_ids": list(package_run_ids),
                "file_hashes": self._handoff_file_hashes(package_root, record.get("files")),
            }
        )
        record.pop("content_hash", None)
        record["content_hash"] = _digest(record)
        return record

    @staticmethod
    def _handoff_file_hashes(package_root: Path, files: Any) -> dict[str, dict[str, str]]:
        """Hash every suite input named by the handoff's file projection."""
        if files is None:
            # Compatibility-only mocked handoffs remain storable, but cannot
            # later open an ARS action channel because there is no file binding
            # to validate.
            return {}
        if not isinstance(files, Mapping):
            raise ValueError("handoff file binding is invalid")
        result: dict[str, dict[str, str]] = {}
        root = package_root.resolve()
        for name, relative in files.items():
            key = str(name).strip()
            if not key or not isinstance(relative, str) or not relative.strip():
                raise ValueError("handoff file binding is invalid")
            candidate = (root / relative).resolve()
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise ValueError("handoff file path escapes package") from exc
            if not candidate.is_file():
                raise ValueError("handoff file is missing")
            result[key] = {
                "path": str(candidate.relative_to(root)).replace("\\", "/"),
                "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            }
        return result

    @staticmethod
    def _handoff_binding(record: Mapping[str, Any]) -> dict[str, Any]:
        """Project only immutable fields also pinned by the task revision."""
        package = record.get("package")
        if not isinstance(package, Mapping):
            raise ValueError("handoff package binding is invalid")
        return {
            "record_content_hash": str(record.get("content_hash", "")),
            "package_path": str(package.get("path", "")),
            "package_hash": str(package.get("package_hash", "")),
            "run_ids": list(record.get("run_ids", ())),
            "file_hashes": _public(record.get("file_hashes", {})),
        }

    def _require_validated_handoff(self, task: ResearchTask) -> Mapping[str, Any]:
        """Validate the latest task-pinned handoff before a formal ARS stage.

        A task revision pins the record hash and package/run/file bindings.  On
        every resumed or consuming stage the immutable record and the package
        on disk are both rechecked.  This prevents a caller from substituting
        arbitrary ARS JSON after a checkpoint.
        """
        from polynexus.suite.handoff import build_suite_handoff

        self._validate_restart_integrity(task)
        if not task.handoff_ids:
            raise ValueError("validated ARS handoff is required")
        handoff_id = task.handoff_ids[-1]
        path = self.store._task_dir(task.task_id) / "handoffs" / f"{handoff_id}.json"
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("validated ARS handoff record is missing or invalid") from exc
        if not isinstance(record, Mapping):
            raise ValueError("validated ARS handoff record is invalid")
        content_hash = str(record.get("content_hash", ""))
        unsigned = dict(record)
        unsigned.pop("content_hash", None)
        if not content_hash or content_hash != _digest(unsigned):
            raise ValueError("validated ARS handoff record integrity is invalid")
        if (
            int(record.get("handoff_record_version", -1)) != _HANDOFF_RECORD_VERSION
            or str(record.get("handoff_id", "")) != handoff_id
            or str(record.get("task_id", "")) != task.task_id
            or record.get("status") != "ready"
        ):
            raise ValueError("validated ARS handoff record binding is invalid")
        bindings = task.metadata.get("handoff_bindings")
        binding = bindings.get(handoff_id) if isinstance(bindings, Mapping) else None
        if not isinstance(binding, Mapping):
            raise ValueError("validated ARS handoff task binding is missing")
        expected_binding = self._handoff_binding(record)
        if canonical_json(_public(binding)) != canonical_json(expected_binding):
            raise ValueError("validated ARS handoff task binding is invalid")

        package = record.get("package")
        if not isinstance(package, Mapping):
            raise ValueError("validated ARS handoff package binding is invalid")
        package_path = package.get("path")
        package_hash = str(package.get("package_hash", ""))
        if not isinstance(package_path, str) or not package_path.strip() or not package_hash:
            raise ValueError("validated ARS handoff package binding is invalid")
        root = Path(package_path).expanduser().resolve()
        known = {str(Path(item).expanduser().resolve()) for item in task.package_paths}
        if str(root) not in known:
            raise ValueError("validated ARS handoff package belongs to another task")
        raw_run_ids = record.get("run_ids")
        if isinstance(raw_run_ids, (str, bytes)) or not isinstance(raw_run_ids, (list, tuple)):
            raise ValueError("validated ARS handoff run binding is invalid")
        run_ids = tuple(dict.fromkeys(str(value) for value in raw_run_ids if str(value)))
        if not run_ids or not set(run_ids).issubset(set(task.run_ids)) or not task.run_ids or task.run_ids[-1] not in run_ids:
            raise ValueError("validated ARS handoff run binding is invalid")

        files = record.get("files")
        file_hashes = record.get("file_hashes")
        if not isinstance(files, Mapping) or not files or not isinstance(file_hashes, Mapping) or not file_hashes:
            raise ValueError("validated ARS handoff file binding is missing")
        captured_hashes = self._handoff_file_hashes(root, files)
        if canonical_json(_public(file_hashes)) != canonical_json(captured_hashes):
            raise ValueError("validated ARS handoff file binding is invalid")

        live = build_suite_handoff(root, task_id=task.task_id)
        if not isinstance(live, Mapping) or live.get("status") != "ready":
            raise ValueError("validated ARS handoff package integrity is invalid")
        live_package = live.get("package")
        if not isinstance(live_package, Mapping):
            raise ValueError("validated ARS handoff package binding is invalid")
        if (
            str(Path(str(live_package.get("path", ""))).expanduser().resolve()) != str(root)
            or str(live_package.get("package_hash", "")) != package_hash
        ):
            raise ValueError("validated ARS handoff package binding is invalid")
        live_run_ids = live.get("run_ids")
        if isinstance(live_run_ids, (str, bytes)) or not isinstance(live_run_ids, (list, tuple, set, frozenset)):
            raise ValueError("validated ARS handoff run binding is invalid")
        if tuple(dict.fromkeys(str(value) for value in live_run_ids if str(value))) != run_ids:
            raise ValueError("validated ARS handoff run binding is invalid")
        live_files = live.get("files")
        if not isinstance(live_files, Mapping) or canonical_json(_public(live_files)) != canonical_json(_public(files)):
            raise ValueError("validated ARS handoff file binding is invalid")
        return record

    def record_ars_actions(self, task_id: str, actions: Sequence[ResearchAction | Mapping[str, Any]]) -> tuple[ResearchAction, ...]:
        from polynexus.suite.handoff import validate_ars_actions

        task = self.store.load(task_id)
        if task.status not in {"checkpointed", "ars_in_progress", "revision_required", "awaiting_human"}:
            raise ValueError("ARS actions require a checkpoint or active handoff")
        self._require_validated_handoff(task)
        raw_actions = tuple(
            value.to_dict() if isinstance(value, ResearchAction) else value
            for value in actions
        )
        normalized = validate_ars_actions(raw_actions, task_id=task_id)
        persisted: list[ResearchAction] = []
        for value in normalized:
            if value.get("status", "pending") != "pending":
                raise ValueError("new ARS actions must be pending")
            action = ResearchAction.create(
                task_id=task_id,
                kind=value["kind"],
                payload=value["payload"],
                action_id=value.get("action_id"),
            )
            if action.task_id != task_id:
                raise ValueError("ARS action belongs to another task")
            persisted.append(self.store.save_action(action))
        ids = tuple(dict.fromkeys((*task.action_ids, *(action.action_id for action in persisted))))
        all_actions = [self.store.load_action(task_id, item) for item in ids]
        status = "ars_in_progress"
        if any(action.kind == "ask_human" and action.status == "pending" for action in all_actions):
            status = "awaiting_human"
        elif any(action.kind == "recompute" and action.status == "pending" for action in all_actions):
            status = "revision_required"
        metadata = dict(task.metadata)
        # A new ARS action means the previously recorded completion no longer
        # covers the full review response.  Keep the immutable record on disk
        # for audit, but require a fresh completion before formal preflight.
        metadata.pop("ars_completion_id", None)
        metadata.pop("ars_completion_binding", None)
        self.store.transition(
            task_id,
            status,
            stage="ars_actions",
            action_ids=ids,
            metadata=metadata,
        )
        return tuple(persisted)

    def record_ars_completion(
        self,
        task_id: str,
        completion: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Persist one completed ARS return bound to the current handoff.

        The record proves that this project has durably recorded a structured
        ARS completion for the exact handoff and package.  It does not claim
        cryptographic authentication of an external ARS runtime; installations
        that need that property must add a separately trusted transport.
        """
        task = self.store.load(task_id)
        handoff = self._require_validated_handoff(task)
        if task.status != "ars_in_progress":
            raise ValueError("ARS completion requires an active ARS stage")
        pending = [
            self.store.load_action(task_id, action_id)
            for action_id in task.action_ids
            if self.store.load_action(task_id, action_id).status == "pending"
        ]
        if pending:
            raise ValueError("ARS completion requires all ARS actions to be resolved")
        normalized = self._normalize_ars_completion(completion)
        action_hashes = {
            action_id: self.store.load_action(task_id, action_id).content_hash
            for action_id in task.action_ids
        }
        package = handoff.get("package")
        if not isinstance(package, Mapping):
            raise ValueError("validated ARS handoff package binding is invalid")
        identity = {
            "task_id": task_id,
            "handoff_id": handoff.get("handoff_id"),
            "handoff_content_hash": handoff.get("content_hash"),
            "package_hash": package.get("package_hash"),
            "completion": normalized,
            "action_hashes": action_hashes,
        }
        completion_id = f"ars-completion-{_digest(identity)[:16]}"
        record = {
            "ars_completion_record_version": _ARS_COMPLETION_RECORD_VERSION,
            "completion_id": completion_id,
            "task_id": task_id,
            "handoff_id": str(handoff.get("handoff_id", "")),
            "handoff_content_hash": str(handoff.get("content_hash", "")),
            "package": {
                "path": str(package.get("path", "")),
                "package_hash": str(package.get("package_hash", "")),
            },
            "action_hashes": action_hashes,
            "ars_completion": normalized,
        }
        record["content_hash"] = _digest(record)
        destination = self.store._task_dir(task_id) / "handoffs" / f"{completion_id}.json"
        if destination.exists():
            try:
                existing = json.loads(destination.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError("ARS completion record is invalid") from exc
            if existing != record:
                raise ValueError("ARS completion record is immutable")
        else:
            self.store._write_once(destination, record)
        binding = {
            "record_content_hash": record["content_hash"],
            "handoff_id": record["handoff_id"],
            "handoff_content_hash": record["handoff_content_hash"],
            "package_hash": record["package"]["package_hash"],
            "action_hashes": action_hashes,
        }
        metadata = {
            **dict(task.metadata),
            "ars_completion_id": completion_id,
            "ars_completion_binding": binding,
        }
        self.store.transition(
            task_id,
            "ars_in_progress",
            stage="ars_completion",
            metadata=metadata,
        )
        return record

    @staticmethod
    def _normalize_ars_completion(completion: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(completion, Mapping):
            raise ValueError("ARS completion is invalid")
        try:
            normalized = _public(completion)
            canonical_json(normalized)
        except (TypeError, ValueError) as exc:
            raise ValueError("ARS completion is invalid") from exc
        if not isinstance(normalized, Mapping):
            raise ValueError("ARS completion is invalid")
        result = dict(normalized)
        status = result.get("status", result.get("state", result.get("verdict")))
        integrity = result.get("integrity")
        if (
            not isinstance(status, str)
            or status.strip().lower() not in _ARS_COMPLETION_STATES
            or not isinstance(integrity, str)
            or integrity.strip().lower() not in _ARS_COMPLETION_STATES
        ):
            raise ValueError("ARS completion is incomplete")
        result["status"] = status.strip().lower()
        result["integrity"] = integrity.strip().lower()
        return result

    def _require_ars_completion(
        self,
        task: ResearchTask,
        handoff: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Load and validate the completion record pinned by the task head."""
        completion_id = task.metadata.get("ars_completion_id")
        binding = task.metadata.get("ars_completion_binding")
        if not isinstance(completion_id, str) or not _SAFE_IDENTIFIER.fullmatch(completion_id):
            raise ValueError("persisted ARS completion is required")
        if not isinstance(binding, Mapping):
            raise ValueError("persisted ARS completion binding is missing")
        path = self.store._task_dir(task.task_id) / "handoffs" / f"{completion_id}.json"
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("persisted ARS completion record is missing or invalid") from exc
        if not isinstance(record, Mapping):
            raise ValueError("persisted ARS completion record is invalid")
        content_hash = str(record.get("content_hash", ""))
        unsigned = dict(record)
        unsigned.pop("content_hash", None)
        if not content_hash or content_hash != _digest(unsigned):
            raise ValueError("persisted ARS completion record integrity is invalid")
        if (
            int(record.get("ars_completion_record_version", -1))
            != _ARS_COMPLETION_RECORD_VERSION
            or str(record.get("completion_id", "")) != completion_id
            or str(record.get("task_id", "")) != task.task_id
            or str(record.get("handoff_id", "")) != str(handoff.get("handoff_id", ""))
            or str(record.get("handoff_content_hash", ""))
            != str(handoff.get("content_hash", ""))
        ):
            raise ValueError("persisted ARS completion record binding is invalid")
        package = record.get("package")
        handoff_package = handoff.get("package")
        if (
            not isinstance(package, Mapping)
            or not isinstance(handoff_package, Mapping)
            or str(package.get("path", "")) != str(handoff_package.get("path", ""))
            or str(package.get("package_hash", ""))
            != str(handoff_package.get("package_hash", ""))
        ):
            raise ValueError("persisted ARS completion package binding is invalid")
        action_hashes = record.get("action_hashes")
        if not isinstance(action_hashes, Mapping):
            raise ValueError("persisted ARS completion action binding is invalid")
        current_hashes = {
            action_id: self.store.load_action(task.task_id, action_id).content_hash
            for action_id in task.action_ids
        }
        if canonical_json(_public(action_hashes)) != canonical_json(current_hashes):
            raise ValueError("persisted ARS completion action binding is invalid")
        expected_binding = {
            "record_content_hash": content_hash,
            "handoff_id": record["handoff_id"],
            "handoff_content_hash": record["handoff_content_hash"],
            "package_hash": package["package_hash"],
            "action_hashes": current_hashes,
        }
        if canonical_json(_public(binding)) != canonical_json(expected_binding):
            raise ValueError("persisted ARS completion task binding is invalid")
        normalized = self._normalize_ars_completion(record.get("ars_completion"))
        return {**dict(record), "ars_completion": normalized}

    @staticmethod
    def _package_reference_ids(handoff: Mapping[str, Any]) -> dict[str, set[str]]:
        """Read the formal package's evidence, metric, and figure identities.

        These are authoritative package artifacts already hash-bound by the
        validated handoff.  The manuscript may repeat their projections for
        rendering, but it may not introduce an otherwise self-consistent ID.
        """
        package = handoff.get("package")
        files = handoff.get("files")
        if not isinstance(package, Mapping) or not isinstance(files, Mapping):
            raise ValueError("validated ARS handoff file binding is invalid")
        root = Path(str(package.get("path", ""))).expanduser().resolve()
        if not root.is_dir():
            raise ValueError("validated ARS handoff package is missing")

        def load(relative: Any, label: str) -> Any:
            if not isinstance(relative, str) or not relative.strip():
                raise ValueError(f"package {label} reference is missing")
            candidate = (root / relative).resolve()
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"package {label} reference escapes package") from exc
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"package {label} reference is invalid") from exc
            return payload

        writing = load(files.get("writing_evidence"), "writing evidence")
        metrics = load(files.get("citation_metrics"), "citation metrics")
        evidence = load(files.get("evidence"), "evidence")
        figures = load(files.get("figure_index"), "figure index")
        allowed = {"evidence": set(), "metric": set(), "figure": set()}

        def walk(value: Any, field: str, bucket: set[str]) -> None:
            if isinstance(value, Mapping):
                raw = value.get(field)
                if raw is not None and not isinstance(raw, (Mapping, list, tuple, set, frozenset)):
                    text = str(raw).strip()
                    if text:
                        bucket.add(text)
                for child in value.values():
                    walk(child, field, bucket)
            elif isinstance(value, (list, tuple, set, frozenset)):
                for child in value:
                    walk(child, field, bucket)

        walk(writing, "evidence_id", allowed["evidence"])
        walk(evidence, "evidence_id", allowed["evidence"])
        walk(metrics, "metric_id", allowed["metric"])
        if isinstance(figures, Mapping):
            entries = figures.get("figures", ())
        else:
            entries = ()
        if not isinstance(entries, (list, tuple)):
            raise ValueError("package figure index reference is invalid")
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            for identifier_field in ("id", "figure_id", "svg", "png", "preview"):
                raw = entry.get(identifier_field)
                if raw is not None and not isinstance(raw, (Mapping, list, tuple, set, frozenset)):
                    text = str(raw).strip()
                    if text:
                        allowed["figure"].add(text)
        return allowed

    @staticmethod
    def _package_traceability_report(report: Any, manuscript: Mapping[str, Any], allowed: Mapping[str, set[str]]) -> Any:
        """Add formal-package ID checks to the existing Suite report DTO."""
        from polynexus.suite.paper_contracts import PreflightReport

        errors = list(report.errors)
        claims = manuscript.get("claims", ())
        if not isinstance(claims, (list, tuple)) or not claims:
            errors.append("data_research_claims_missing")
        else:
            for claim in claims:
                if not isinstance(claim, Mapping):
                    errors.append("package_claim_invalid")
                    continue
                for category, field in (
                    ("evidence", "evidence_ids"),
                    ("metric", "metric_ids"),
                    ("figure", "figure_ids"),
                ):
                    values = claim.get(field, ())
                    if isinstance(values, (str, bytes)):
                        values = (values,)
                    if not isinstance(values, (list, tuple, set, frozenset)):
                        errors.append(f"package_{category}_unbound")
                        continue
                    for value in values:
                        identifier = str(value).strip()
                        if identifier and identifier not in allowed.get(category, set()):
                            errors.append(f"package_{category}_unbound:{identifier}")
        errors = list(dict.fromkeys(errors))
        checks = dict(report.checks)
        checks["package_traceability"] = "failed" if errors != list(report.errors) else "passed"
        checks["submission"] = "failed" if errors else (
            "review_required" if report.warnings else "passed"
        )
        return PreflightReport.create(
            source_id=report.source_id,
            errors=tuple(errors),
            warnings=report.warnings,
            checks=checks,
        )

    def submission_preflight(self, task_id: str, manuscript: Mapping[str, Any], **gates: Any) -> Any:
        """Run the Suite's formal-only gate and reflect its result in task state."""
        from polynexus.suite.preflight import submission_preflight

        task = self.store.load(task_id)
        handoff = self._require_validated_handoff(task)
        if task.status != "ars_in_progress":
            raise ValueError("formal preflight requires an ARS-stage task")
        pending_actions = tuple(
            self.store.load_action(task_id, action_id)
            for action_id in task.action_ids
            if self.store.load_action(task_id, action_id).status == "pending"
        )
        if pending_actions:
            report = submission_preflight(
                manuscript,
                **{**dict(gates), "ars_state": {"status": "incomplete"}},
            )
        else:
            completion = self._require_ars_completion(task, handoff)
            trusted_gates = dict(gates)
            trusted_gates["ars_state"] = completion["ars_completion"]
            report = submission_preflight(manuscript, **trusted_gates)
        report = self._package_traceability_report(
            report,
            manuscript,
            self._package_reference_ids(handoff),
        )
        if pending_actions:
            from polynexus.suite.paper_contracts import PreflightReport

            report = PreflightReport.create(
                source_id=report.source_id,
                errors=tuple((*report.errors, "ars_actions_pending")),
                warnings=report.warnings,
                checks={**dict(report.checks), "ars_actions": "failed", "submission": "failed"},
            )
        if report.status == "passed":
            status = "export_ready"
        elif report.status == "review_required":
            status = "awaiting_human"
        else:
            status = "revision_required"
        self.store.transition(
            task_id,
            status,
            stage="submission_preflight",
            metadata={**dict(task.metadata), "submission_preflight": report.to_dict()},
        )
        return report

    def complete_export(self, task_id: str, export_paths: Sequence[str | Path]) -> ResearchTask:
        """Close a task only after the formal submission gate has passed."""
        task = self.store.load(task_id)
        handoff = self._require_validated_handoff(task)
        self._require_ars_completion(task, handoff)
        if task.status != "export_ready":
            raise ValueError("export completion requires a passed submission preflight")
        if isinstance(export_paths, (str, bytes)):
            raise ValueError("export paths are required")
        values_list: list[str] = []
        artifacts: list[dict[str, Any]] = []
        for path in export_paths:
            candidate = Path(path).expanduser()
            if not candidate.is_absolute():
                candidate = self.store.workspace.root / candidate
            candidate = candidate.resolve()
            if not candidate.is_file():
                raise ValueError(f"export artifact is missing: {candidate}")
            values_list.append(str(candidate))
            artifacts.append(self._artifact_binding(candidate))
        values = tuple(values_list)
        if not values:
            raise ValueError("export paths are required")
        return self.store.transition(
            task_id,
            "completed",
            stage="export_complete",
            metadata={
                **dict(task.metadata),
                "export_paths": values,
                "export_artifacts": artifacts,
            },
        )

    def resolve_action(self, task_id: str, action_id: str, *, approved: bool, note: str = "") -> ResearchTask:
        task = self.store.load(task_id)
        self._require_validated_handoff(task)
        if type(approved) is not bool:
            raise ValueError("research action decision must be a boolean")
        action = self.store.load_action(task_id, action_id)
        requested_resolution = {"approved": approved, "note": str(note)}
        if action.status != "pending":
            # Resolution and task-head updates are two separate append-only
            # writes.  A process can therefore die after the resolution
            # sibling is durable but before the task transition is written.
            # Treat an identical replay as a recovery request: repair the task
            # head instead of reporting a misleading "already resolved" error.
            existing_resolution = dict(action.resolution)
            if (
                action.status not in {"resolved", "rejected"}
                or existing_resolution.get("approved") != requested_resolution["approved"]
                or str(existing_resolution.get("note", "")) != requested_resolution["note"]
            ):
                raise ValueError("research action is already resolved with a different decision")
            last_action = task.metadata.get("last_action")
            if (
                isinstance(last_action, Mapping)
                and canonical_json(last_action) == canonical_json(action.to_dict())
            ):
                # The task transition completed before a client/process crash;
                # returning the current immutable head makes the operation
                # idempotent and avoids another no-op revision.
                return task
            next_status = self._status_after_action(task, action)
            return self.store.transition(
                task_id,
                next_status,
                stage="action_resolved",
                metadata={**dict(task.metadata), "last_action": action.to_dict()},
            )
        resolved = replace(action, status="resolved" if approved else "rejected", resolution={"approved": approved, "note": note}, revision=action.revision + 1, parent_hash=action.content_hash, content_hash="")
        # Action files are immutable; retain the resolution as a sibling record.
        self.store._write_once(self.store._task_dir(task_id) / "actions" / f"{action_id}-r{resolved.revision:04d}.json", resolved.to_dict())
        next_status = self._status_after_action(task, resolved)
        return self.store.transition(task_id, next_status, stage="action_resolved", metadata={**dict(task.metadata), "last_action": resolved.to_dict()})

    def _status_after_action(self, task: ResearchTask, action: ResearchAction) -> str:
        """Derive the task state after one action resolution.

        Keeping this decision in one helper is important for crash recovery:
        the normal path and an idempotent replay must choose the same state
        from the same latest action siblings.
        """
        remaining = [
            self.store.load_action(task.task_id, item)
            for item in task.action_ids
            if item != action.action_id
        ]
        approved = action.status == "resolved" and action.resolution.get("approved") is True
        if not approved and action.kind == "ask_human":
            return "blocked"
        if any(item.kind == "ask_human" and item.status == "pending" for item in remaining):
            return "awaiting_human"
        if any(item.kind == "recompute" and item.status == "pending" for item in remaining):
            return "revision_required"
        if approved and action.kind == "recompute":
            return "revision_required"
        return "ars_in_progress"

    def advance(self, task_id: str, *, mapping: Mapping[str, Any] | None = None, approve_mapping: bool = False, approver: str = "") -> ResearchTask:
        """Convenience facade that delegates to the same explicit stages."""
        task = self.store.load(task_id)
        if task.status == "draft":
            task = self.inspect(task_id)
        if mapping is not None and not task.mapping_proposal:
            task = self.propose_mapping(task_id, mapping)
        if task.status == "awaiting_mapping_confirmation" and approve_mapping:
            task = self.confirm_mapping(task_id, approved=True, approver=approver or "user")
        if task.status == "ready" and task.confirmed_mapping and self._recompute_route(task) is None:
            task = self.run(task_id)
        return task


__all__ = [
    "ACTION_KINDS",
    "ACTION_STATES",
    "RESEARCH_SCHEMA_VERSION",
    "TASK_STATES",
    "ResearchAction",
    "ResearchLoopService",
    "ResearchTask",
    "ResearchTaskStore",
]
