# Local GUI Automation MCP Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Codex a local-only MCP interface that operates a dedicated visible PolyNexus GUI through the existing single-file import and analysis flow.

**Architecture:** A Qt-owned JSON-lines bridge is created only by an explicit automation launch. It binds an ephemeral `127.0.0.1` port and accepts a per-session secret. A stdio MCP server owns the child process and translates fixed tools into bridge requests; normal GUI startup creates no bridge.

**Tech Stack:** Python 3.10+, PySide6 `QTcpServer`/`QWidget.grab`, MCP Python SDK `FastMCP`, pytest, and existing `MainWindow`/`AnalysisResult` contracts.

---

## File structure

- Create: `polynexus/gui/automation_bridge.py` — Qt-thread request validation,
  fixed GUI actions, JSON-safe status/result responses, and screenshot capture.
- Create: `polynexus/automation/__init__.py` — package marker.
- Create: `polynexus/automation/client.py` — authenticated loopback
  JSON-lines client used by the MCP server.
- Create: `polynexus/automation/mcp_server.py` — lifecycle owner and fixed
  stdio MCP tools.
- Modify: `polynexus/app.py` — opt-in bridge startup and ready-line emission;
  normal startup remains unchanged.
- Modify: `pyproject.toml` — MCP dependency and `polynexus-mcp` script.
- Create: `tests/test_gui_automation_bridge.py` — Qt bridge security and GUI
  flow unit/integration tests.
- Create: `tests/test_gui_automation_mcp.py` — client/session/tool contract
  tests without real scientific datasets.
- Modify: `README.md` — local installation and Codex MCP registration example.
- Modify: task/spec/plan/memory documents — final acceptance evidence only.

### Task 1: Define the GUI bridge contract

**Files:**
- Create: `tests/test_gui_automation_bridge.py`
- Create: `polynexus/gui/automation_bridge.py`

- [x] **Step 1: Write failing bridge contract tests**

```python
def test_bridge_rejects_wrong_secret_without_calling_window() -> None:
    window = FakeWindow()
    bridge = GuiAutomationBridge(window, secret="expected")

    reply = bridge.handle_request({"secret": "wrong", "action": "status"})

    assert reply == {"ok": False, "error": {"code": "unauthorized"}}
    assert window.calls == []


def test_bridge_import_select_run_and_result_reuse_window_methods(tmp_path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("x,y\\n1,2\\n", encoding="utf-8")
    window = FakeWindow(result=AnalysisResult(technique="dsc", parameters={"tg": 50.0}))
    bridge = GuiAutomationBridge(window, secret="expected")

    assert bridge.handle_request({"secret": "expected", "action": "import_file", "path": str(source), "technique": "dsc"})["ok"]
    assert bridge.handle_request({"secret": "expected", "action": "run_analysis"})["ok"]
    assert bridge.handle_request({"secret": "expected", "action": "get_result"})["result"]["parameters"] == {"tg": 50.0}
```

- [x] **Step 2: Run the bridge tests and verify RED**

Run: `python -m pytest tests/test_gui_automation_bridge.py -q`

Expected: collection fails because `polynexus.gui.automation_bridge` does not
exist.

- [x] **Step 3: Implement the minimal fixed-action bridge**

```python
class GuiAutomationBridge(QObject):
    ALLOWED_ACTIONS = frozenset({
        "status", "import_file", "select_technique", "run_analysis",
        "get_result", "capture_window", "close",
    })

    def handle_request(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if not secrets.compare_digest(str(request.get("secret", "")), self._secret):
            return {"ok": False, "error": {"code": "unauthorized"}}
        # Dispatch only an action in ALLOWED_ACTIONS; never getattr from input.
```

Implement `start(port)` with `QTcpServer.listen(QHostAddress.LocalHost, port)`,
newline-delimited JSON decoding, a 64 KiB request limit, and one response per
request. `import_file` must require an existing file and a technique in
`{"dsc", "ir", "nmr", "saxs", "waxs"}`, then call
`MainWindow._apply_import_selection`. `run_analysis` must call
`MainWindow._run_analysis`. `get_result` may return only the current result's
existing `to_dict()` payload after recursively converting non-finite numbers
to `None` and limiting maps/lists to 100 items. `capture_window` saves
`window.grab()` beneath a fresh `tempfile.mkdtemp(prefix="polynexus-automation-")`
directory. `close` schedules `window.close()` and closes the server.

- [x] **Step 4: Run the bridge tests and verify GREEN**

Run: `python -m pytest tests/test_gui_automation_bridge.py -q`

Expected: all bridge tests pass.

### Task 2: Add automation-only application startup

**Files:**
- Modify: `polynexus/app.py`
- Modify: `tests/test_gui_automation_bridge.py`

- [x] **Step 1: Add failing application-boundary tests**

```python
def test_normal_app_startup_does_not_create_automation_bridge(monkeypatch) -> None:
    created = []
    monkeypatch.setattr("polynexus.gui.automation_bridge.GuiAutomationBridge", lambda *a, **k: created.append(a))
    assert main(startup_probe=True) == 0
    assert created == []


def test_automation_startup_starts_loopback_bridge_and_closes_with_probe(monkeypatch) -> None:
    bridge = FakeServerBridge(port=43123)
    monkeypatch.setattr("polynexus.app.GuiAutomationBridge", lambda *a, **k: bridge)
    assert main(startup_probe=True, automation_port=0, automation_secret="expected") == 0
    assert bridge.started_port == 0
    assert bridge.closed is True
```

- [x] **Step 2: Run the startup tests and verify RED**

Run: `python -m pytest tests/test_gui_automation_bridge.py -q`

Expected: tests fail because `main` has no automation parameters and no bridge
lifecycle.

- [x] **Step 3: Implement opt-in startup**

```python
def main(argv=None, *, startup_probe=False, automation_port: int | None = None,
         automation_secret: str | None = None):
    ...
    bridge = None
    if automation_port is not None:
        if not automation_secret:
            raise ValueError("automation_secret is required when automation_port is set")
        from polynexus.gui.automation_bridge import GuiAutomationBridge
        bridge = GuiAutomationBridge(window, secret=automation_secret)
        ready = bridge.start(automation_port)
        print(json.dumps({"automation_ready": True, **ready}), flush=True)
```

Close the bridge in `finally` for startup probes and after `app.exec()` exits.
Do not change `polynexus.__main__`; the automation server starts the app by
importing `polynexus.app.main`, keeping normal CLI parsing unchanged.

- [x] **Step 4: Run the startup tests and verify GREEN**

Run: `python -m pytest tests/test_gui_startup.py tests/test_gui_automation_bridge.py -q`

Expected: all selected tests pass.

### Task 3: Provide the portable MCP server

**Files:**
- Create: `polynexus/automation/__init__.py`
- Create: `polynexus/automation/client.py`
- Create: `polynexus/automation/mcp_server.py`
- Modify: `pyproject.toml`
- Create: `tests/test_gui_automation_mcp.py`

- [x] **Step 1: Write failing session/client tests**

```python
def test_loopback_client_sends_secret_and_rejects_non_loopback() -> None:
    client = AutomationClient(host="127.0.0.1", port=1234, secret="token")
    assert client.build_request("status") == {"secret": "token", "action": "status"}
    with pytest.raises(ValueError, match="loopback"):
        AutomationClient(host="10.0.0.4", port=1234, secret="token")


def test_session_close_terminates_only_its_child_process() -> None:
    process = FakeProcess()
    session = AutomationSession(process_factory=lambda *_: process)
    session.close()
    assert process.terminated is True
```

- [x] **Step 2: Run the MCP tests and verify RED**

Run: `python -m pytest tests/test_gui_automation_mcp.py -q`

Expected: collection fails because `polynexus.automation` is absent.

- [x] **Step 3: Implement the local client and MCP tools**

```python
mcp = FastMCP("PolyNexus GUI Automation")

@mcp.tool()
def import_file(path: str, technique: str) -> dict[str, Any]:
    return _require_session().request("import_file", path=path, technique=technique)
```

`AutomationClient` must reject every host except `127.0.0.1` and `::1`, set a
finite socket timeout, send one JSON request plus newline, and reject oversized
or malformed replies. `AutomationSession.launch` generates `secrets.token_urlsafe`,
starts `sys.executable -c "from polynexus.app import main; ..."` with
`PYTHONPATH` pointed to the installed project, consumes exactly one ready JSON
line, and keeps only the child it created. Expose fixed MCP tools: `launch`,
`import_file`, `select_technique`, `run_analysis`, `wait_for_run`,
`get_result`, `capture_window`, and `close`. `wait_for_run` polls `status` with
a caller-provided bounded timeout (default 60 seconds, maximum 600 seconds).
Add `mcp>=1.0` to the `automation` optional dependency and
`polynexus-mcp = "polynexus.automation.mcp_server:main"` to project scripts.

- [x] **Step 4: Run the MCP tests and verify GREEN**

Run: `python -m pytest tests/test_gui_automation_mcp.py -q`

Expected: all selected tests pass without starting a real visible GUI.

### Task 4: Document, verify, and checkpoint

**Files:**
- Modify: `README.md`
- Modify: `docs/agent/tasks/2026-08-09-gui-automation-mcp.md`
- Modify: `docs/superpowers/specs/2026-08-09-gui-automation-mcp-design.md`
- Modify: `docs/superpowers/plans/2026-08-09-gui-automation-mcp.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Write the installation documentation assertion**

Add a README section that shows the exact local install and Codex MCP command
configuration, including that no network listener is created by ordinary GUI
launch and each computer must install/register its own local server.

- [x] **Step 2: Run focused integration verification**

Run: `python -m pytest tests/test_gui_startup.py tests/test_gui_automation_bridge.py tests/test_gui_automation_mcp.py -q`

Expected: all selected tests pass.

- [x] **Step 3: Run the repository verifier**

Run: `python scripts/verify.py --task docs/agent/tasks/2026-08-09-gui-automation-mcp.md --changed --types`

Expected: exit code 0. Record its exact summary in the task and active-work
memory; retain the known external-real-data baseline limitation.

- [x] **Step 4: Create the local checkpoint**

Run:

```powershell
python scripts/auto_commit.py `
  --message "feat(gui): add local automation MCP bridge" `
  --files pyproject.toml README.md polynexus/app.py polynexus/gui/automation_bridge.py polynexus/automation/__init__.py polynexus/automation/client.py polynexus/automation/mcp_server.py tests/test_gui_automation_bridge.py tests/test_gui_automation_mcp.py docs/agent/tasks/2026-08-09-gui-automation-mcp.md docs/superpowers/specs/2026-08-09-gui-automation-mcp-design.md docs/superpowers/plans/2026-08-09-gui-automation-mcp.md docs/agent/memory/active-work.md
```

Expected: one local commit containing only the explicit task allowlist; no push,
merge, deployment, or external message.

## Plan self-review

- Spec coverage: Tasks 1-3 implement the listener, secret, fixed actions,
  visible child, stdio MCP server, capture, and closure; Task 4 covers portable
  installation, focused verification, task evidence, and checkpointing.
- No-placeholder check: the plan has concrete source/test paths, request
  shapes, actions, error behavior, and commands; no deferred implementation
  placeholders remain.
- Type consistency: `GuiAutomationBridge`, `AutomationClient`, and
  `AutomationSession` are the only cross-task interfaces, and their stated
  action names match the MCP tool names and task acceptance criteria.
