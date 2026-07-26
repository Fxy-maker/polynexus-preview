# Real published-run audit — 2026-07-26

This note records real-fixture execution evidence separately from the
synthetic lifecycle matrices. A generated Manifest is evidence of the shared
publication boundary; it is not a scientific sign-off.

## Runs completed

| Mode | Real input | Result | Evidence |
|---|---|---|---|
| DSC standard | repository PA6 standard DSC text | pipeline completed; Manifest published; two validation warnings | `C:\Temp\PolyNexus_release_walkthrough_20260726\dsc_standard_real` |
| WAXS static | repository PA6 `.raw` | pipeline completed; Manifest published; validation passed | `C:\Temp\PolyNexus_release_walkthrough_20260726\waxs_static_real` |
| WAXS temperature | repository PA6 EDF directory | pipeline completed; Manifest published; validation passed | `C:\Temp\PolyNexus_release_walkthrough_20260726\waxs_temperature_real` |
| IR standard | repository PA6 `YL.SPA` | pipeline completed; Manifest published; validation passed | `C:\Temp\PolyNexus_release_walkthrough_20260726\ir_standard_real` |
| SAXS temperature | repository PA6 EDF directory | eight Manifest entries are `ready`; scientific validation is false because Q* is contaminated and lamellar evidence is diagnostic-only | `C:\Temp\PolyNexus_release_walkthrough_20260726\saxs_temperature_real_after_colorbar_fix` |
| NMR liquid/solid H/C | repository NMR fixtures | covered by the real-data lifecycle matrix | `tests/test_nmr_lifecycle_closure.py` |

## Runs not accepted as pass

- WAXS strain real 2D directory exceeded the 244-second diagnostic timeout.
- IR temperature-2D real directory exceeded the 244-second diagnostic
  timeout.
- SAXS temperature is intentionally not a normal-science pass: the engine
  retains the run and figures while reporting `ERROR:qstar_contaminated` and
  diagnostic-only lamellar rows.

## Figure-audit correction

The real SAXS temperature run exposed a shared audit defect: colorbar axes were
treated as data axes. `polynexus.plotting.figure_audit` now skips only axes with
Matplotlib's `_colorbar` marker. The focused regression plus SAXS temperature
provider/panel/evidence matrix passed with 20 tests.

## Remaining release gates

- For every mode, complete active Gallery selection, Editor revision, export
  bundle inspection, and History restore against an accepted real run.
- Complete restarted canonical GUI visual walkthrough and Main/SI/diagnostic
  publication-role review.
- Obtain IR mapping/ROI vendor semantics and assignment-limited NMR/Joint
  scientific sign-off.
- Decide how real fixtures with diagnostic-only or validation-error results are
  to be released; no result is promoted to Main by this note.
