# SAXS real data and Workbench acceptance — 2026-07-27

## Result

The automated real-data acceptance slice is green for SAXS static,
temperature, and strain lifecycle replay. Export provenance is present in all
three external diagnostic bundles. This note does not grant scientific sign-off.

## Evidence

| Boundary | Evidence | Result |
|---|---|---|
| Real lifecycle | `test_real_published_run_walkthrough.py -k saxs` | 3 passed |
| Workbench | SAXS figure contracts + Results Workbench profiles | 9 passed |
| Export | `C:\Temp\PolyNexus_saxs_stage9_real_bundle` | 3 bundles `ok`; 3 manifests register `quality_evidence.json` |
| Restart source | `scripts/launch_gui.py --diagnose` | root/package/branch/current commit aligned at `9fa7b82` |
| Full boundary verification | `python scripts/verify.py --changed --types --full --boundary` | 2662 passed, 10 warnings; boundary audit passed |

The static payload retained data-quality, Guinier, and metric evidence. The
temperature payload retained sequence Guinier evidence. The strain payload
retained only the evidence available for that run. The temperature run's
existing validation error was preserved and did not become a publication
promotion.

The rendered static main figure, temperature waterfall, and strain evolution
figure were inspected from the external bundle root. They render successfully;
the strain heatmap is close to saturation and the temperature bundle retains
its validation error, so neither observation is treated as scientific approval.

## Current-head refresh

- Fresh SAXS real walkthrough: `3 passed, 12 deselected in 53.40s`.
- Fresh Workbench/figure profile matrix: `29 passed in 0.29s`.
- Current launcher diagnosis: source root `D:\PolyNexus`, package under the
  same root, branch `codex/origin-editor-usable-controls`, commit `9fa7b82`.
- The bundle evidence remains conservative: static quality is `Trend` but all
  four 1D method evidence entries are `Diagnostic`; temperature has four
  `Quantitative` and one `Diagnostic` frame and `Unusable` sequence Guinier
  evidence; strain has five `Trend` frames. The strain heatmap near-saturation
  and temperature end-of-axis truncation remain review signals.

## Open human gates

- Restart the desktop GUI from `D:\PolyNexus` and visually inspect the SAXS
  Workbench, figure gallery, selected figure, and export entry point. The
  current-head launcher identity is now verified, but this user interaction
  review is still open.
- Review real temperature and strain plots for physically credible trends,
  quality downgrades, and publication roles.
- Keep AI rescue in shadow/confirm-only mode until calibration and scientific
  review authorize a future tiered-auto policy.
