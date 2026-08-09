from __future__ import annotations

import asyncio
import io

import pytest

from polynexus.automation.client import AutomationClient
from polynexus.automation.mcp_server import AutomationSession, create_mcp_server


def test_loopback_client_builds_authenticated_request_and_rejects_remote_host() -> None:
    client = AutomationClient(host="127.0.0.1", port=1234, secret="token")

    assert client.build_request("status") == {"secret": "token", "action": "status"}
    with pytest.raises(ValueError, match="loopback"):
        AutomationClient(host="10.0.0.4", port=1234, secret="token")


def test_session_launches_child_from_ready_line_and_terminates_that_child() -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO('{"automation_ready":true,"host":"127.0.0.1","port":43123}\n')
            self.terminated = False

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout: float) -> int:
            return 0

    process = FakeProcess()
    created_clients: list[AutomationClient] = []
    session = AutomationSession(
        process_factory=lambda *args, **kwargs: process,
        client_factory=lambda **kwargs: created_clients.append(AutomationClient(**kwargs)) or created_clients[-1],
    )

    assert session.launch() == {"host": "127.0.0.1", "port": 43123}
    session.close()

    assert created_clients[0].secret
    assert process.terminated is True


def test_mcp_server_exposes_only_the_fixed_main_flow_tools() -> None:
    server = create_mcp_server(AutomationSession())

    tool_names = {tool.name for tool in asyncio.run(server.list_tools())}

    assert tool_names == {
        "launch",
        "import_file",
        "select_technique",
        "run_analysis",
        "wait_for_run",
        "get_result",
        "capture_window",
        "close",
    }
