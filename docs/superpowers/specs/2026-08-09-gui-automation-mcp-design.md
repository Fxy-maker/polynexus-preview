# Local PolyNexus GUI Automation MCP Bridge Design

## Purpose

Provide Codex with a portable, user-flow-level way to operate PolyNexus on the
same Windows computer without relying on mouse coordinates or accessing the
user's existing application window. The first release supports one analysis
workflow only: launch, import a file, select a technique, run, wait, inspect,
capture, and close.

## Decision

The application will implement an automation mode that is unavailable in a
normal GUI launch. In that mode, a separately started visible `MainWindow`
hosts a small local bridge. An MCP server started through a console command
communicates with that bridge and exposes the fixed actions to Codex over
standard input/output.

The bridge must reuse the existing import-selection and run-lifecycle methods
on the Qt GUI thread. It may not duplicate analysis logic or bypass result
presentation. This keeps behavior aligned with what a user sees while avoiding
fragile coordinate-based desktop automation.

## Components and flow

1. `polynexus-mcp` starts an MCP stdio server and creates a random per-session
   secret.
2. The server starts a dedicated PolyNexus process with the automation flag,
   an ephemeral loopback port, and that secret. The window remains visible.
3. The GUI bridge accepts authenticated, schema-validated requests only from
   `127.0.0.1`, dispatching them on the Qt main thread.
4. MCP tools translate the seven permitted operations to bridge requests:
   `launch`, `import_file`, `select_technique`, `run_analysis`, `wait_for_run`,
   `get_result`, `capture_window`, and `close`.
5. Responses contain JSON-safe status, current workflow state, a bounded
   result summary, error diagnostics where present, and screenshot paths when
   requested.

The GUI bridge owns no persistent configuration and does not attach to an
already-running window. Closing the MCP session asks only the bridge-created
window to close.

## Security and failure behavior

Automation mode is opt-in at startup. Normal `polynexus --gui` has no listener.
The bridge binds to loopback only, rejects absent/incorrect secrets, validates
each action and path, and has no reflection, generic command, or code-execution
operation. The random secret is never written to logs or MCP responses.

Invalid actions, missing files, unavailable techniques, failed analysis, or
timeouts produce structured errors without changing an existing user window.
The server terminates the child process on session shutdown. A failed launch
leaves no listener running.

## Portability and installation

The implementation is packaged with PolyNexus. Each computer installs the
automation extra and registers the `polynexus-mcp` command as a local stdio MCP
server in Codex. Nothing is exposed between computers; each Codex installation
controls a GUI process on its own machine.

## Testing

Unit tests cover request validation, loopback/secret rejection, session
lifecycle, and JSON-safe summaries. Qt integration tests use the visible
`MainWindow` class with the bridge enabled, verify that import selection and
run completion take existing GUI routes, and assert that ordinary GUI mode does
not start a bridge. Tests use synthetic fixtures and do not require the
repository-external real datasets.

## Explicit first-release limits

Only a single-file main analysis workflow is supported. Batch analysis,
interactive file-picker dialogs, all editor surfaces, AI confirmation dialogs,
and direct control of pre-existing windows are deferred. Screenshots are
diagnostic evidence, not a replacement for structured results.
