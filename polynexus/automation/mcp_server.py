"""Stdio MCP server for a dedicated, visible PolyNexus automation session."""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import AutomationClient


class AutomationSession:
    """Own exactly one GUI process and its authenticated loopback client."""

    def __init__(
        self,
        *,
        process_factory: Callable[..., Any] = subprocess.Popen,
        client_factory: Callable[..., AutomationClient] = AutomationClient,
    ) -> None:
        self._process_factory = process_factory
        self._client_factory = client_factory
        self._process: Any | None = None
        self._client: AutomationClient | None = None
        self._runtime_root: str | None = None

    def launch(self) -> dict[str, Any]:
        if self._process is not None and self._process.poll() is None and self._client is not None:
            return {"host": self._client.host, "port": self._client.port}

        secret = secrets.token_urlsafe(32)
        runtime_root = tempfile.mkdtemp(prefix="polynexus-automation-runtime-")
        environment = dict(os.environ)
        environment["POLYNEXUS_AUTOMATION_SECRET"] = secret
        environment["POLYNEXUS_RUNTIME_ROOT"] = runtime_root
        project_root = str(Path(__file__).resolve().parents[2])
        existing_pythonpath = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = os.pathsep.join(
            [project_root, *([existing_pythonpath] if existing_pythonpath else [])]
        )
        command = [
            sys.executable,
            "-c",
            (
                "import os; from polynexus.app import main; "
                "raise SystemExit(main(automation_port=0, "
                "automation_secret=os.environ['POLYNEXUS_AUTOMATION_SECRET']))"
            ),
        ]
        process = self._process_factory(
            command,
            cwd=project_root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        try:
            ready = self._read_ready_line(process)
            host = str(ready["host"])
            port = int(ready["port"])
            self._client = self._client_factory(host=host, port=port, secret=secret)
        except Exception:
            self._terminate(process)
            raise
        self._process = process
        self._runtime_root = runtime_root
        return {"host": host, "port": port}

    def request(self, action: str, **payload: Any) -> dict[str, Any]:
        if self._client is None or self._process is None or self._process.poll() is not None:
            raise RuntimeError("automation session is not running; call launch first")
        return self._client.request(action, **payload)

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.request("close")
            except (OSError, RuntimeError):
                pass
        if self._process is not None:
            self._terminate(self._process)
        self._process = None
        self._client = None

    @staticmethod
    def _read_ready_line(process: Any) -> dict[str, Any]:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            line = process.stdout.readline()
            if not line:
                break
            try:
                decoded = json.loads(line)
            except json.JSONDecodeError:
                continue
            if decoded.get("automation_ready") is True:
                if str(decoded.get("host")) != "127.0.0.1":
                    raise RuntimeError("automation GUI announced a non-loopback host")
                return decoded
        raise RuntimeError("automation GUI did not announce a ready loopback bridge")

    @staticmethod
    def _terminate(process: Any) -> None:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def create_mcp_server(session: AutomationSession | None = None) -> FastMCP:
    """Create the fixed local tool surface without exposing arbitrary actions."""
    active_session = session or AutomationSession()
    server = FastMCP("PolyNexus GUI Automation")

    @server.tool()
    def launch() -> dict[str, Any]:
        """Launch a dedicated visible PolyNexus window with local automation enabled."""
        return active_session.launch()

    @server.tool()
    def import_file(path: str, technique: str) -> dict[str, Any]:
        """Import one existing local file and select its analysis technique."""
        return active_session.request("import_file", path=path, technique=technique)

    @server.tool()
    def select_technique(technique: str) -> dict[str, Any]:
        """Select one supported analysis technique in the dedicated GUI."""
        return active_session.request("select_technique", technique=technique)

    @server.tool()
    def run_analysis() -> dict[str, Any]:
        """Run the currently selected single-file analysis through the GUI."""
        return active_session.request("run_analysis")

    @server.tool()
    def wait_for_run(timeout_seconds: float = 60.0) -> dict[str, Any]:
        """Wait up to 600 seconds for the current GUI analysis to leave running."""
        timeout = float(timeout_seconds)
        if not 0 < timeout <= 600:
            return {"ok": False, "error": {"code": "invalid_timeout"}}
        deadline = time.monotonic() + timeout
        while True:
            response = active_session.request("status")
            if not response.get("ok"):
                return response
            status = response.get("status", {})
            if str(status.get("run_status", "idle")) != "running":
                return response
            if time.monotonic() >= deadline:
                return {"ok": False, "error": {"code": "timeout"}}
            time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))

    @server.tool()
    def get_result() -> dict[str, Any]:
        """Return the current GUI analysis result in a JSON-safe form."""
        return active_session.request("get_result")

    @server.tool()
    def capture_window() -> dict[str, Any]:
        """Capture the dedicated PolyNexus window for visual verification."""
        return active_session.request("capture_window")

    @server.tool()
    def close() -> dict[str, Any]:
        """Close only the dedicated automation GUI session."""
        active_session.close()
        return {"ok": True}

    return server


def main() -> None:
    create_mcp_server().run(transport="stdio")
