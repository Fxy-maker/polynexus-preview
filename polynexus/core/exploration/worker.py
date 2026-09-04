"""Process-isolated execution for non-core exploration executors.

This is a bounded worker boundary, not a claim of a hostile-kernel sandbox.
Production deployments should place the worker in a container/VM with OS-level
network, filesystem and resource controls.  The Python-level policy here still
fails closed for network access, clears inherited secrets, limits wall time and
serialized output, and never runs code in the Core process.
"""

from __future__ import annotations

from dataclasses import dataclass
import builtins
import json
import math
import multiprocessing
import os
from pathlib import Path
import socket
import shutil
import tempfile
from typing import Any

from polynexus.core.project_workflow.models import canonical_json

from .contracts import ExplorationRequest, ExplorationRun
from .runner import ExplorationRunner


@dataclass(frozen=True)
class ExplorationWorkerLimits:
    wall_time_s: float = 60.0
    max_output_bytes: int = 4 * 1024 * 1024
    max_memory_bytes: int = 512 * 1024 * 1024
    max_cpu_time_s: float | None = None
    allow_network: bool = False
    allowed_read_roots: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.wall_time_s, (int, float))
            or isinstance(self.wall_time_s, bool)
            or not math.isfinite(float(self.wall_time_s))
            or self.wall_time_s <= 0
            or not isinstance(self.max_output_bytes, int)
            or isinstance(self.max_output_bytes, bool)
            or self.max_output_bytes <= 0
        ):
            raise ValueError("worker limits must be positive")
        if (
            not isinstance(self.max_memory_bytes, int)
            or isinstance(self.max_memory_bytes, bool)
            or self.max_memory_bytes <= 0
        ):
            raise ValueError("max_memory_bytes must be a positive integer")
        if self.max_cpu_time_s is not None and (
            not isinstance(self.max_cpu_time_s, (int, float))
            or isinstance(self.max_cpu_time_s, bool)
            or not math.isfinite(float(self.max_cpu_time_s))
            or self.max_cpu_time_s <= 0
        ):
            raise ValueError("max_cpu_time_s must be positive or null")
        if not isinstance(self.allow_network, bool):
            raise TypeError("allow_network must be boolean")
        object.__setattr__(
            self,
            "allowed_read_roots",
            tuple(os.path.normcase(str(Path(root).resolve())) for root in self.allowed_read_roots),
        )


def _deny_network() -> None:
    def denied(*_args: Any, **_kwargs: Any) -> Any:
        raise PermissionError("exploration worker network access is disabled")

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]


def _restrict_filesystem(allowed_roots: tuple[str, ...], writable_root: str):
    original_open = builtins.open
    original_os_open = os.open
    original_path_open = Path.open
    writable_root = os.path.normcase(os.path.realpath(writable_root))

    def in_root(path: Path, roots: tuple[str, ...]) -> bool:
        rendered = str(path)
        return any(rendered == root or rendered.startswith(root + os.sep) for root in roots)

    def check(path_value: Any, mode: str = "r") -> Path:
        try:
            rendered = os.fspath(path_value)
        except TypeError as exc:
            raise TypeError("filesystem path must be path-like") from exc
        path = Path(os.path.normcase(os.path.realpath(os.path.expanduser(rendered))))
        write_requested = any(flag in mode for flag in ("w", "a", "x", "+"))
        if write_requested:
            if not in_root(path, (writable_root,)):
                raise PermissionError("exploration worker writes are limited to its temporary directory")
        elif not in_root(path, (*allowed_roots, writable_root)):
            raise PermissionError("exploration worker filesystem access is outside allowed roots")
        return path

    def guarded_open(file: Any, *args: Any, **kwargs: Any):
        mode = args[0] if args else kwargs.get("mode", "r")
        check(file, str(mode))
        return original_open(file, *args, **kwargs)

    def guarded_os_open(file: Any, flags: int, *args: Any, **kwargs: Any):
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
        check(file, "w" if flags & write_flags else "r")
        return original_os_open(file, flags, *args, **kwargs)

    def guarded_path_open(self: Path, mode: str = "r", *args: Any, **kwargs: Any):
        check(self, str(mode))
        return original_path_open(self, mode, *args, **kwargs)

    builtins.open = guarded_open  # type: ignore[assignment]
    os.open = guarded_os_open  # type: ignore[assignment]
    Path.open = guarded_path_open  # type: ignore[assignment]
    return original_open, original_os_open, original_path_open


def _apply_resource_limits(limits: ExplorationWorkerLimits) -> None:
    """Apply portable best-effort process limits where the host supports them."""

    try:
        import resource
    except ImportError:
        return
    try:
        resource.setrlimit(resource.RLIMIT_AS, (limits.max_memory_bytes, limits.max_memory_bytes))
        if limits.max_cpu_time_s is not None:
            seconds = max(1, int(limits.max_cpu_time_s))
            resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds))
    except (OSError, ValueError):
        # Windows has no resource module and constrained hosts may reject a
        # limit.  The parent wall-clock and output bounds remain enforced.
        return


def _worker_entry(
    executor: Any,
    request_payload: dict[str, Any],
    limits: ExplorationWorkerLimits,
    connection: Any,
) -> None:
    root: str | None = None
    original_open: Any = None
    original_os_open: Any = None
    original_path_open: Any = None
    try:
        os.environ.clear()
        root = tempfile.mkdtemp(prefix="polynexus-exploration-worker-")
        os.chdir(root)
        _apply_resource_limits(limits)
        if not limits.allow_network:
            _deny_network()
        original_open, original_os_open, original_path_open = _restrict_filesystem(
            limits.allowed_read_roots, root
        )
        request = ExplorationRequest.from_dict(request_payload)
        raw_result = executor(request)
        if isinstance(raw_result, ExplorationRun):
            result = raw_result.to_dict()
        else:
            result = raw_result.to_dict() if hasattr(raw_result, "to_dict") else raw_result
        encoded = canonical_json(result).encode("utf-8")
        if len(encoded) > limits.max_output_bytes:
            raise ValueError("exploration worker output exceeds configured limit")
        connection.send_bytes(encoded)
    except Exception as exc:
        payload = {"error_type": type(exc).__name__, "error": str(exc)[:512]}
        try:
            connection.send_bytes(canonical_json(payload).encode("utf-8"))
        except Exception:
            pass
    finally:
        if original_open is not None:
            builtins.open = original_open
        if original_os_open is not None:
            os.open = original_os_open
        if original_path_open is not None:
            Path.open = original_path_open
        if root is not None:
            shutil.rmtree(root, ignore_errors=True)
        connection.close()


class IsolatedExplorationRunner:
    """Run a registered executor outside the Core process with bounded policy."""

    def __init__(
        self,
        runner: ExplorationRunner,
        limits: ExplorationWorkerLimits | None = None,
    ) -> None:
        if type(runner) is not ExplorationRunner:
            raise TypeError("IsolatedExplorationRunner requires an ExplorationRunner")
        self.runner = runner
        self.limits = limits or ExplorationWorkerLimits()

    def run(self, request: ExplorationRequest) -> ExplorationRun:
        if type(request) is not ExplorationRequest:
            raise TypeError("isolated exploration requires an ExplorationRequest")
        entry, preflight = self.runner._preflight(request)
        if preflight is not None:
            return preflight
        assert entry is not None
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe(duplex=False)
        process = context.Process(
            target=_worker_entry,
            args=(entry.executor, request.to_dict(), self.limits, child),
            daemon=True,
        )
        started = False
        try:
            process.start()
            started = True
            child.close()
            if not parent.poll(self.limits.wall_time_s):
                process.terminate()
                process.join(timeout=2)
                return ExplorationRun.failed(
                    request,
                    "exploration_worker_timeout",
                    {"wall_time_s": self.limits.wall_time_s},
                )
            encoded = parent.recv_bytes()
            if len(encoded) > self.limits.max_output_bytes:
                return ExplorationRun.failed(request, "exploration_worker_output_limit")
            payload = json.loads(encoded.decode("utf-8"))
            if isinstance(payload, dict) and "error_type" in payload:
                if payload.get("error_type") == "ValueError" and "output exceeds" in str(
                    payload.get("error", "")
                ):
                    return ExplorationRun.failed(
                        request, "exploration_worker_output_limit", payload
                    )
                return ExplorationRun.failed(request, "exploration_worker_failed", payload)
            return self._validate_result(request, payload)
        except (
            EOFError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
            AttributeError,
            RuntimeError,
        ) as exc:
            return ExplorationRun.failed(
                request,
                "exploration_worker_start_failed" if not started else "exploration_worker_invalid_output",
                {"error_type": type(exc).__name__},
            )
        finally:
            if not started:
                child.close()
            if started:
                process.join(timeout=2)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=2)
            parent.close()

    def _validate_result(self, request: ExplorationRequest, payload: Any) -> ExplorationRun:
        entry = self.runner.registry.resolve(request.executor_id, request.executor_version)
        if entry is None:
            return ExplorationRun.needs_input(request, "exploration_executor_unregistered")
        # Reuse the Core runner's complete validation path; no worker result is
        # accepted without rechecking source, canonical admission, contracts
        # and implementation identity in the parent process.
        return self.runner._complete_from_result(request, entry.descriptor, payload)


__all__ = ["ExplorationWorkerLimits", "IsolatedExplorationRunner"]
