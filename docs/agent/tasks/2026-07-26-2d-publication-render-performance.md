# 2D publication render performance

## Goal

Make complete real WAXS strain directories reach the shared publication
boundary within a bounded time by limiting only the editable image-grid
snapshot size.

## Non-goals

- No change to raw detector arrays or scientific WAXS analysis.
- No change to figure-role eligibility, thresholds, or IR vendor semantics.
- No deletion or modification of repository fixtures or scratch outputs.

## Affected boundaries

- `polynexus.core.waxs_engine.figure_strain._image_grid_source`.
- Existing FigureDefinition `image_grid` data-source, renderer, editor, and
  export contracts.
- Focused WAXS publication/document/renderer regressions and the complete real
  WAXS strain walkthrough.

## Implementation plan

1. Add failing provider regressions for bounded WAXS image-grid snapshots,
   duplicate IR temperature-2D frame figures, and bounded IR correlation
   snapshots.
2. Implement vectorized WAXS snapshot sampling without mutating raw detector
   arrays; implement IR publication-only duplicate suppression and correlation
   downsampling while retaining full analysis matrices.
3. Run focused provider/lifecycle matrices, then run the complete real WAXS
   strain and IR temperature-2D shared-lifecycle walkthrough.
4. Run the structured verifier, update durable acceptance/memory evidence, and
   checkpoint only the explicit changed-file allowlist.

## Acceptance criteria

- [x] Raw `scan.image` arrays remain unchanged and are still used by analysis.
- [x] Each publication image-grid frame contains no more than 256×256 samples.
- [x] Existing image-grid columns, frame tiling, editor materialization, and
  manifest publication contracts remain valid.
- [x] Complete real WAXS strain and IR temperature-2D publications return
  without the prior timeout and complete the shared lifecycle walkthrough.
- [x] Structured verifier passes and the checkpoint contains only the explicit
  allowlist.

## Verification

```powershell
python -m pytest --basetemp=C:\Temp\PolyNexus_waxs_2d_perf tests/test_waxs_publication_strain_provider.py tests/test_waxs_figure_document.py tests/test_figure_image_grid.py tests/test_v2_adapter_image_grid.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-26-2d-publication-render-performance.md --changed --types
```

## Changed-file allowlist

- `polynexus/core/waxs_engine/figure_strain.py`
- `polynexus/core/ir_engine/figure_provider.py`
- `tests/test_waxs_publication_strain_provider.py`
- `tests/test_ir_complete_figure_provider.py`
- `tests/test_real_published_run_walkthrough.py`
- this task card
- the linked implementation plan
- acceptance/memory files only when fresh real-run evidence changes status
