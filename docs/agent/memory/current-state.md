---
kind: state
status: active
date: 2026-07-18
title: Current PolyNexus repository state
---

## Mainline snapshot

- The dedicated local `main` worktree is at merge commit `16c268b3`, which
  includes the Origin editor menu, run-root source-path fixes, visible native
  Origin activation, object-document routing, native plot rescaling,
  one-Graph multi-series export, user-registry capability probing, and the GUI
  startup boundary restoration. It is ahead of `origin/main` locally; it has
  not been pushed.
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

## Verification evidence

- Origin capability, adapter, contract, package, and ChartEditor Origin tests:
  42 passed.
- GUI-startup regression checks: 3 passed.
- ChartEditor regression suite: 238 passed.
- Automatic-commit regression tests: 2 passed.
- Ruff checks and `compileall` passed for the changed Origin/editor modules.
- The repository contract documents `python scripts/verify.py --changed
  --types`, but `D:\PolyNexus\scripts\verify.py` is absent as of this
  snapshot, so that command cannot currently run.

## Known limitations and next actions

- A live smoke export using the configured `Origin64.exe` returned
- `success/originpro` for the user's SAXS waterfall document and generated a
  native `.opju` with the rescaled graph layer. The temporary `.opju` remains
  locked until Origin closes; this is expected application ownership. Broader
  user-figure manual testing remains pending.
- The local mainline merge is complete at `16c268b3`; an explicit push decision
  remains pending.
- Reconcile the older active-work entries in `active-work.md` against the
  current branch/PR state before using them as authoritative.
