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
| Restart source | `scripts/launch_gui.py --diagnose` | root/package/commit aligned at `41588a0` |

The static payload retained data-quality, Guinier, and metric evidence. The
temperature payload retained sequence Guinier evidence. The strain payload
retained only the evidence available for that run. The temperature run's
existing validation error was preserved and did not become a publication
promotion.

## Open human gates

- Restart the desktop GUI from `D:\PolyNexus` and visually inspect the SAXS
  Workbench, figure gallery, selected figure, and export entry point.
- Review real temperature and strain plots for physically credible trends,
  quality downgrades, and publication roles.
- Keep AI rescue in shadow/confirm-only mode until calibration and scientific
  review authorize a future tiered-auto policy.
