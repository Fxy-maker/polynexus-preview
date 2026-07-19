---
kind: decision
status: active
date: 2026-07-18
title: Origin export opens a visible native graph when automation is available
---

## Decision

The ChartEditor `Export to Origin` action is a one-click send action. It uses
the native `originpro` adapter when the installed OriginPro executable and
Python bridge are available. The adapter makes Origin visible, activates the
created graph window, imports the prepared figure sources, and saves the
native project. The ChartEditor does not ask for an output directory before
starting this workflow; native projects use the figure's containing directory
as the default output root.

The portable `Origin_Export` package remains the explicit fallback when native
automation is unavailable. It is reported as a compatibility package, not as a
live Origin graph.

ChartEditor requests `editable_origin` for any persisted object document, even
when the runtime generated-document flag is not set after a reload. Static
image documents continue to use the visual-fidelity path.

The native facade rescales each Origin graph layer after adding a plot. Origin
starts new graph layers with a default `0..1` Y range, which hides valid SAXS
intensity data unless the layer is rescaled.

One export creates one Origin Graph and reuses its first layer for all mapped
plot series. This preserves multi-series figures as one native Origin graph
instead of opening one graph window per curve.

The first object-document panel's X/Y axis scales are forwarded to the Origin
layer; the document's `log` scale maps to Origin's `log10` scale before the
final rescale.

## Rationale

The user-facing intent is to see the current figure inside Origin, not merely
receive CSV/JSON files in Explorer. Application startup and window activation
belong to the Origin adapter boundary so GUI code does not depend on Origin
APIs.

## Evidence and limitation

- Native activation and no-directory-dialog regressions pass.
- Origin capability probing reads the configured executable from the current
  process environment first, then falls back to the Windows user environment
  registry key. This matters because `setx` updates future processes while an
  already-running GUI keeps its original `os.environ`.
- With the user's installed `D:\Program Files\OriginLab\Origin2026\Origin64.exe`,
  the live probe returns installed/native-capable in the existing GUI process.
- A live smoke export using the configured `Origin64.exe` returned
  `success/originpro`, created `codex_origin_smoke.opju`, and left an `Origin64`
  window visible with that project title. The temporary project remains locked
  until Origin closes; this is expected Windows application ownership.

## Revisit condition

Revisit if OriginPro's installed API requires a different foreground-window
activation mechanism or if users need a separate explicit “open blank Origin”
action.
