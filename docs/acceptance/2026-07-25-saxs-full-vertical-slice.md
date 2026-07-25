# SAXS full vertical slice checkpoint

## Delivered

The existing SAXS static, temperature, and strain providers are now reachable
from the customized Results Workbench through real manifest figure IDs. Each
mode exposes a main entry plus support/selected evidence, while the gallery
router resolves the first available fallback candidate for incomplete runs.
The route remains manifest-backed, so preview, editable document, publication
role, export assets, and provenance continue to come from the same run record.

SAXS profile entries:

- Static: `saxs.static.comparison` with
  `saxs.static.correlation.support`, falling back to
  `saxs.series.static.waterfall` when needed.
- Temperature: `saxs.temperature.evolution` with
  `saxs.temperature.waterfall`, falling back to
  `saxs.series.temperature.parameters` when the evolution gate is incomplete.
- Strain: `saxs.strain.evolution.1d` with
  `saxs.strain.phase-evidence`, falling back to
  `saxs.series.strain.waterfall` for the main route.

## Verification evidence

- SAXS evidence/provider/panel/profile matrix: 40 passed.
- SAXS export, publication cutover, FigureDocument, FigurePipeline,
  production, gallery, and main-window figure matrix: 48 passed, with four
  pre-existing Matplotlib font warnings.
- Results Workbench and main-window matrix: 94 passed.
- Real/Synthetic SAXS evaluation runner: 6 passed.
- Ruff, compileall, and `git diff --check`: passed.

## Remaining acceptance boundary

- Human restarted-GUI visual and scientific review is still required before a
  release-ready claim.
- The profile registry's non-SAXS figure IDs remain generic until their own
  vertical slices validate the mode-specific Manifest IDs.
- AI-off/failure/fallback behavior is covered by existing SAXS/preprocess
  contracts, but still needs to be included in the final cross-module release
  matrix.
