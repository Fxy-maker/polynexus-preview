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
