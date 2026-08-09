---
task_id: 2026-08-09-gui-automation-mcp
kind: architecture
status: ready-for-checkpoint
date: 2026-08-09
title: Provide a local-only MCP bridge for the visible PolyNexus GUI main flow
---

# Local GUI automation MCP bridge

## Goal

Allow Codex on the same Windows machine to launch and operate a dedicated,
visible PolyNexus window through a constrained MCP tool surface: import one
file, select a technique, run analysis, wait for completion, inspect
structured results, capture the window, and close it.

## Non-goals

- No remote, LAN, or Internet listener.
- No control of an already-open user GUI window.
- No arbitrary Python evaluation, arbitrary QObject invocation, generic file
  browsing, or editor/page automation.
- No scientific algorithm, persistence schema, or analysis-result contract
  change.

## Affected boundaries

- GUI startup in `polynexus.app` and `polynexus.__main__`.
- A new automation-only GUI bridge owned by the Qt main thread.
- A local MCP stdio server and portable installation/configuration guidance.
- Main-flow GUI integration tests and security-boundary tests.

## Acceptance criteria

- [x] Normal GUI startup opens no automation listener.
- [x] Automation startup binds only `127.0.0.1`, requires a per-session
  random secret, and launches one visible dedicated window.
- [x] The MCP server exposes only fixed main-flow actions and cannot invoke
  arbitrary methods or evaluate arbitrary code.
- [x] A valid file/technique workflow reaches the existing GUI run path and
  reports the real completion/error state plus a JSON-safe result summary.
- [x] The MCP server can capture the dedicated window and close only its own
  session.
- [x] Focused regression tests cover both the happy path and denied access.

## Implementation plan

1. Add failing bridge and MCP regressions for authentication, fixed actions,
   loopback-only transport, child-process ownership, and tool discovery.
2. Implement the Qt-owned fixed-action bridge and explicit automation startup
   without changing the ordinary GUI launch path.
3. Implement the stdio MCP session/client, portable packaging command, and
   local installation guidance.
4. Run focused GUI/MCP tests, a real local lifecycle smoke test, the structured
   verifier, durable-memory update, and an explicit allowlist checkpoint.

## Verification

```powershell
python -m pytest tests/test_gui_automation_bridge.py tests/test_gui_automation_mcp.py -q
python scripts/verify.py --task docs/agent/tasks/2026-08-09-gui-automation-mcp.md --changed --types
```

## Evidence

- TDD RED/GREEN bridge and MCP tests: `9 passed in 7.83s`.
- Focused startup/bridge/MCP matrix: `15 passed in 7.46s`.
- Real local lifecycle smoke: a dedicated GUI returned a `127.0.0.1` ephemeral
  port, reported `run_status: idle`, and closed through its owned session.
- Structured verification on 2026-08-09 passed task-card validation, agent
  memory validation, changed-file Ruff and compilation, quality `303 passed`,
  preprocessing `157 passed`, and whitespace checks.

## Environment limitation

The clean isolated worktree lacks repository-external real DSC/SAXS fixtures.
On 2026-08-09, a baseline `python -m pytest` stopped during collection with
three `StopIteration` errors in real-data walkthrough tests. Those failures
must remain distinguished from bridge regressions.

The smoke test intentionally did not run a scientific analysis because a GUI
run creates output beside its selected input. The focused bridge test instead
uses a temporary file and verifies that import and run invoke the existing
`MainWindow` route, then reads that route's result contract. A caller who wants
scientific-output evidence must explicitly provide a disposable sample path.
