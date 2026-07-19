---
kind: state
status: active
date: 2026-07-19
title: Current PolyNexus repository state
---

## Mainline snapshot

- The dedicated local `main` worktree is at merge commit `583709ad`, which
  includes the Origin editor menu, run-root source-path fixes, visible native
  Origin activation, object-document routing, native plot rescaling,
  one-Graph multi-series export, source axis-scale forwarding, user-registry
  capability probing, and the GUI startup boundary restoration. It is ahead of
  `origin/main` locally; it has not been pushed.
- The active development worktree is `D:\PolyNexus` on
  `codex/origin-editor-usable-controls`, at the same merged commit. Its
  pre-existing untracked `.superpowers/` and Origin Lite design drafts are left
  untouched.

## Important boundaries

- The normal figure gallery is manifest-only. Legacy recursive discovery stays
  behind the explicit recovery path; see decision `0003`.
- Generated figure documents store data-source paths relative to the active run
  when `path_kind` is `run_relative`.
- Gallery entries carry `run_root` into ChartEditor. Origin export carries that
  context as `ExportRequest.source_root`, and all Origin adapters use the shared
  `polynexus/origin/path_resolution.py` resolver before falling back to the
  figure directory and process working directory.
- When native Origin automation is available, the ChartEditor action now uses
  the `originpro` adapter to show/activate Origin and leave the created graph
  visible; see decision `0011`.
- Origin capability probing checks `ORIGIN_EXE` in the current process first and
  then reads the Windows user environment registry, so a `setx ORIGIN_EXE ...`
  configuration is recognized without restarting the GUI process.
- Origin export is optional and Windows-only. Adapter order is high-level
  `originpro`, COM/LabTalk, then an Origin-compatible package fallback. The GUI
  must remain usable without Origin installed.
- Native OriginPro export now maps each plot's `data_ref` to its own worksheet,
  applies document colors/names/line widths, and forwards first-panel axis
  labels in addition to axis scales. Mathtext labels are converted to readable
  Unicode at the native boundary, and all plots still reuse one Graph.

## Verification evidence

- Origin capability, adapter, contract, package, and ChartEditor Origin tests:
  44 passed.
- GUI-startup regression checks: 3 passed.
- ChartEditor regression suite: 238 passed.
- Native Origin source/style fidelity suite: 16 passed.
- Native Origin label-display follow-up: 18 passed in the combined focused
  Origin suite.
- Automatic-commit regression tests: 2 passed.
- Ruff checks and `compileall` passed for the changed Origin/editor modules.
- The repository contract documents `python scripts/verify.py --changed
  --types`, but `D:\PolyNexus\scripts\verify.py` is absent as of this
  snapshot, so that command cannot currently run.

## Known limitations and next actions

- A live smoke export using the configured `Origin64.exe` returned
  `success/originpro` for the user's SAXS waterfall document. In-process
  inspection found one Graph, five plots, five document colors, five 0.8-point
  lines, five source worksheets, named Y columns, a `log10` Y axis, and clean
  Unicode axis labels. The temporary `.opju` remains locked until Origin
  closes; this is expected application ownership.
- The local mainline merge is complete at `583709ad`; an explicit push decision
  remains pending.
- Reconcile the older active-work entries in `active-work.md` against the
  current branch/PR state before using them as authoritative.
