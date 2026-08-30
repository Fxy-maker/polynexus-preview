# Real elastomer IR/NMR article evidence

## Goal

Use the real dataset at `C:\Users\Fan Xuyi\Desktop\文件夹\弹性体\弹性体中文` to
produce a replayable evidence package containing the six IR temperature
sequences and the available liquid/solid NMR spectra for article drafting.

## Non-goals

- Do not modify raw files or infer scientific conclusions, peak assignments, or
  crystallinity claims.
- Do not add a cross-technique image model or change provider algorithms.
- Do not publish or merge external artifacts.

## Shared objects and entry points

- Objects: `CanonicalExperiment`, `AnalysisRun`, `ProjectWorkflowRun`, and
  immutable evidence package.
- AI/Codex/CLI: use the same adapter, canonical converter, replay, and package
  contracts; no private persistence path is introduced.
- GUI: unchanged; it reads the resulting evidence package through the existing
  evidence view.
- Cross-entry rule: canonical templates and mapping proposals are source-hash
  bound and validated identically for adapter and replay consumers.

## Context and output budget

- Read first: repository contract, canonical conversion modules, project
  workflow adapters/service, NMR/IR tests, and project memory.
- Search scope: canonical models/registry, agent replay, project adapters and
  service, focused tests, and the user data directory.
- Report: package path/counts, exact verification, limitations, and untouched
  pre-existing workspace changes.

## Affected boundaries

- Canonical table mapping and replay.
- Single-input project recipe propagation.
- Real-data project evidence materialization.

## Acceptance criteria

- [x] Canonical one-dimensional conversion records an explicit user-confirmed
  mapping for headerless NMR tables: first column chemical shift, second column
  intensity.
- [x] Canonical replay reuses that mapping and remains source-hash bound.
- [x] `nmr/` files route to liquid H/C by filename; `solid-NMR/C` and `solid-NMR/H`
  route to solid C/H by directory and filename.
- [x] Six `insu-FTIR/<sample>` directories route to
  `ir.temperature_series.v1` without changing raw data.
- [x] Generated evidence remains `review_required` where existing provider or
  scientific gates require review.

## Implementation plan

1. Add validated mapping-proposal deserialization and optional converter/replay
   propagation.
2. Carry confirmed mappings through the single-input adapter and project run
   request parameters.
3. Test the public replay path and materialize the real IR/NMR evidence package.

## Verification

- Focused canonical/project workflow tests.
- `python scripts/verify.py --task docs/agent/tasks/2026-08-30-real-elastomer-ir-nmr-evidence.md --changed --types`.
- Read-only source hash and package-view validation after materialization.

## Completion evidence

- Corrected `PA6-H.csv` and eleven remaining solid-NMR files replayed; all 12
  new runs entered the mutable working set as `review_required`.
- Frozen package:
  `C:\Users\Fan Xuyi\Desktop\文件夹\弹性体\弹性体中文\.polynexus\evidence\elastomer-ir-nmr-article-v002`
  with 32 runs, 32 evidence items, and 151 indexed figures. v001 remains
  immutable.
- Package view reload succeeded with 151 figures and IR/NMR techniques.
- Headerless exports with trailing empty columns are accepted only when the
  explicit source-bound mapping is valid; raw files remain untouched.
