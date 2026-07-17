# Optional OriginLab Integration and Adapter Chain Design

**Date:** 2026-07-17  
**Status:** Draft for user review

## Goal

Keep PolyNexus fully usable as a standalone Python/PySide6 desktop
application, while providing a one-click export to OriginLab when a supported
Origin installation is available. The integration must cover three situations:

- Origin is not installed;
- a newer Origin installation exposes the high-level Python integration;
- an older or otherwise limited Origin installation exposes COM automation and
  LabTalk.

The integration must be optional at runtime. Importing or launching PolyNexus
must not require Origin, `originpro`, `pywin32`, or any Origin SDK.

## Problem

PolyNexus already owns a technique-neutral figure document, data snapshots,
render plans, editable chart state, and publication assets. These are suitable
inputs for an external export boundary, but the application currently has no
OriginLab adapter or capability probe.

Putting Origin-specific checks directly into the GUI or a single export method
would make version support brittle and would force future interface changes to
modify the central service. The integration needs a stable adapter contract and
a responsibility chain with explicit fallback behavior.

## Selected approach

Use an injected, priority-ordered adapter chain:

```text
OriginProAdapter       priority 100   newer high-level Python integration
        |
        | unavailable or unsupported
        v
ComLabTalkAdapter      priority 80    broad legacy/direct automation path
        |
        | unavailable or unsupported
        v
PackageExporter        priority 10    always-available Origin-compatible bundle
```

`OriginExportService` knows only the adapter protocol and result semantics. It
does not contain Origin-version conditionals or COM-specific logic. The default
adapter list is assembled by a registry/factory outside the service so that a
future adapter can be added without changing the dispatch algorithm.

The first successful direct adapter wins. An adapter that reports
`UNAVAILABLE` or an explicitly recoverable capability mismatch yields to the
next adapter. An actual export failure after work has started is returned to the
user rather than being silently hidden by a second attempt. The package exporter
remains the safe final fallback.

## Scope

### In scope

- A common `OriginAdapter` Protocol in `adapter_base.py`.
- Immutable request, capability, warning, and result contracts.
- Non-invasive detection of Origin installation, version, license/API
  availability, and optional Python/COM dependencies.
- A high-level Python adapter for supported newer Origin installations.
- A COM/LabTalk adapter for older or high-level-API-incompatible installations.
- An Origin-compatible package exporter that works without Origin installed.
- Direct export of supported data sources, plot series, axes, basic styles,
  legends, titles, and supported annotations.
- A visual-fidelity export path using the existing SVG/PDF/PNG assets.
- Graceful fallback, user-facing warnings, logging, and test seams.

### Out of scope

- Reimplementing Origin's analysis, fitting, workbook, or statistics engines.
- Hand-authoring or reverse-engineering `.opju` files.
- Guaranteeing that every Matplotlib artist, transform, font, clipping rule, or
  custom annotation becomes an editable Origin object.
- Making Origin a required dependency of PolyNexus.
- Supporting non-Windows Origin automation in the first delivery.
- Running arbitrary user-provided LabTalk as part of export.

## Package layout

```text
polynexus/origin/
|- adapter_base.py          # OriginAdapter Protocol and shared adapter metadata
|- contracts.py             # ExportRequest, Capability, ExportResult, warnings
|- capability_probe.py      # Installation and interface detection
|- originpro_adapter.py     # Optional newer high-level integration
|- com_labtalk_adapter.py   # Optional COM + LabTalk integration
|- package_exporter.py      # No-Origin compatible bundle export
`- service.py               # Responsibility-chain orchestration
```

The adapters consume a stable figure/export contract. They do not import or
call `ChartEditor`, Qt widgets, or GUI mixins. The GUI supplies the current
figure document and receives an `ExportResult`.

## Adapter contract

`adapter_base.py` should expose a structural Protocol so test doubles and
future third-party adapters can conform without inheriting from PolyNexus:

```python
class OriginAdapter(Protocol):
    adapter_id: str
    priority: int

    def can_handle(self, request: ExportRequest) -> bool:
        ...

    def export(self, request: ExportRequest) -> ExportResult:
        ...
```

`can_handle()` remains deliberately small, but it receives a request because
availability may depend on the requested mode, data type, output directory, or
whether the caller requested an editable Origin graph. Rich probe details are
returned through the capability contract and included in the result or service
diagnostics; they do not need to leak into the dispatch loop.

The shared contracts should include:

- `ExportRequest`: normalized figure document, data manifest, output root,
  export mode, preferred adapter policy, and whether Origin may be opened.
- `ExportMode`: `editable_origin`, `visual_fidelity`, or `package`.
- `AdapterCapability`: adapter ID, availability, detected Origin version,
  supported modes, and human-readable reason.
- `ExportResult`: status, adapter ID, generated artifacts, warnings, message,
  capability details, and whether the result is recoverable.
- `ExportStatus`: `SUCCESS`, `UNAVAILABLE`, `FAILED`, or `PARTIAL`.

Paths in contracts must be normalized and resolved by the service boundary.
Adapters may create files only below the request's approved output root.

## Capability detection

`capability_probe.py` performs cheap checks before an adapter claims a request:

1. Confirm the platform is Windows for direct Origin automation.
2. Detect an installed Origin executable and/or registered automation server.
3. Determine the Origin version when available.
4. Check whether the optional Python package or COM bridge is importable.
5. Avoid opening Origin during the cheap probe unless the user explicitly
   requested a live connection check.

Detection must be best-effort. Missing registry entries, localized install
paths, a closed license session, or a busy Origin process must produce a
negative capability result rather than an application startup error.

The probe must not claim that a version is supported solely from its number.
It should combine version information with the interface actually available.
This avoids hard-coding a fragile version boundary as Origin's automation
capabilities vary by installation and license.

## Adapter behavior

### OriginProAdapter

This adapter is preferred when the external `originpro` integration and a
usable Origin installation are available. It should:

- open or attach to an Origin session according to the request;
- create or reuse a workbook and worksheet for each data source;
- transfer numeric data and column labels with units where supported;
- create editable plots from the normalized plot recipe;
- apply supported axis, legend, title, line, marker, and color settings;
- add supported text and simple annotation objects;
- save the resulting project through Origin itself when requested.

The module must import `originpro` lazily. No package import should occur at
PolyNexus startup or when the user uses only the native editor.

### ComLabTalkAdapter

This adapter is the compatibility path for installations where the high-level
Python integration is missing or cannot handle the request. It should use the
optional COM bridge to attach to or launch Origin, import the already-written
CSV data snapshots, and execute a bounded, generated LabTalk command sequence.

LabTalk generation must be limited to PolyNexus-owned commands and validated
values. User-controlled labels, file names, and text must be escaped or passed
through safe Origin properties rather than concatenated into executable
commands.

COM calls must not block the Qt event loop. The GUI should invoke the service
through its existing worker/background-operation boundary and surface progress
and failure through the normal status channel.

### PackageExporter

This adapter is always available and does not require Origin. It should create
a self-contained bundle containing, as applicable:

```text
Origin_Export/
|- data/                  # CSV files with stable column headers
|- figure_document.json   # normalized PolyNexus figure definition
|- metadata.json          # source, units, warnings, and export context
|- preview.svg
|- preview.pdf
|- preview.png
`- import.ogs              # optional generated LabTalk import script
```

The bundle is the correct result when Origin is absent, unsupported, or
unavailable. When a direct adapter fails before committing any Origin-side
changes, the service may offer this bundle as a recovery action. It must be
clear to the user that the bundle is not an `.opju` project until opened and
saved by Origin.

## Dispatch and fallback

The service receives adapters through dependency injection. The default factory
orders them by priority, while tests can provide a custom list:

```text
for adapter in adapters sorted by descending priority:
    if not adapter.can_handle(request):
        continue
    result = adapter.export(request)
    if result.status == SUCCESS:
        return result
    if result.status == UNAVAILABLE:
        continue
    return result
```

The package exporter is registered last and normally claims every request whose
mode permits a package. A direct adapter must return `UNAVAILABLE` for a
capability mismatch before creating external state. It must return `FAILED` or
`PARTIAL` for an actual runtime error after beginning work. This prevents the
service from masking a partially created Origin project with a misleading
success from a later adapter.

The UI should expose the selected adapter and any downgrade in the result:

- `Exported to Origin using Python integration`;
- `Exported to Origin using COM compatibility mode`;
- `Origin unavailable; created an Origin-compatible package`.

## Data and visual mapping

The canonical PolyNexus figure document remains authoritative. Mapping is
explicit and loss-aware:

| PolyNexus data | Origin target |
|---|---|
| Data source | Worksheet or worksheet page |
| Numeric columns | Origin worksheet columns |
| Column name/unit | Long name, comments, or unit metadata |
| Plot series | Origin plot object |
| X/Y axis definitions | Layer axis properties |
| Title and legend | Graph text/legend objects |
| Line/marker/color style | Plot style properties |
| Simple text/line/arrow annotation | Origin annotation object when supported |
| Unsupported object or transform | Warning plus visual-fidelity asset |

Two user-visible modes are required:

1. `editable_origin`: prioritize native Origin objects and report any omitted
   or approximated features.
2. `visual_fidelity`: export the existing SVG/PDF/PNG render and optionally
   include the data package; this preserves appearance even when editability is
   impossible.

The adapter must never silently claim that a visual asset is an editable Origin
graph. Warnings are persisted in `metadata.json` and returned in
`ExportResult`.

## Error handling

- No Origin installation: skip direct adapters and use `PackageExporter`.
- Missing optional Python/COM dependency: report unavailable, not a startup
  error.
- Unsupported version or license: skip the adapter with a clear reason.
- Origin busy or connection timeout: return a recoverable failure only if no
  external project state was changed; otherwise return `PARTIAL`.
- Data mapping failure: keep the source bundle and return a warning/error that
  identifies the affected figure or data source.
- Save failure: do not report success or clear any native PolyNexus dirty state.
- User cancellation: return a cancelled/recoverable result and preserve files
  already committed to the approved output directory.

All direct-adapter errors should be normalized before reaching the GUI. Raw
COM exceptions and Python import traces belong in the application log, while
the user-facing message states the next action.

## Testing

### Contract tests

- A fake adapter satisfies `OriginAdapter` without inheritance.
- The service selects the highest-priority capable adapter.
- `UNAVAILABLE` continues the chain.
- `FAILED` and `PARTIAL` stop the chain and remain visible.
- The package exporter is always available as the final fallback.
- The service never imports optional Origin modules during construction.

### Package exporter tests

- Bundle contains the expected data, metadata, and render assets.
- Paths remain inside the requested output root.
- Unsupported features become explicit warnings.
- Repeated export uses staging/atomic commit rules and does not corrupt an
  existing bundle.

### Windows integration tests

These tests are optional and skipped when Origin is not installed:

- capability detection across a supported newer installation and an older COM
  installation;
- workbook/data transfer;
- plot and basic style creation;
- project save through Origin;
- timeout, cancellation, and license/busy error handling.

The CI baseline must not require Origin or Windows-specific optional packages.

## Rollout

1. Add the contracts, Protocol, registry injection, and package exporter with
   tests. Keep the feature available through an explicit export action.
2. Add capability probing and the COM/LabTalk adapter behind the same service.
3. Add the high-level Python adapter and make it the highest-priority direct
   adapter when its capability probe succeeds.
4. Add the GUI button and capability-aware status text. Preserve native
   PolyNexus export behavior when the button is unavailable.
5. Run manual acceptance checks on one newer and one older Origin installation,
   plus the no-Origin fallback path.

## Acceptance criteria

- PolyNexus starts and its native editor/export paths work when Origin is not
  installed.
- The GUI never contains version-specific `if/elif` dispatch logic.
- Every adapter conforms to the same Protocol and returns `ExportResult`.
- Newer high-level Origin integration is preferred when available.
- Older COM/LabTalk-compatible Origin installations can receive supported data
  and editable basic plots.
- No-Origin users can create a complete Origin-compatible bundle.
- Direct export failures and downgrade decisions are visible and actionable.
- Unsupported visual features are reported instead of silently discarded.
- The implementation has contract tests that run without Origin installed.
