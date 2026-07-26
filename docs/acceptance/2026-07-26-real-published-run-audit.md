# Real published-run audit — 2026-07-26

This note records real-fixture execution evidence separately from the
synthetic lifecycle matrices. A generated Manifest is evidence of the shared
publication boundary; it is not a scientific sign-off.

## Runs completed

| Mode | Real input | Result | Evidence |
|---|---|---|---|
| DSC standard | repository PA6 standard DSC text | pipeline completed; Manifest published; two validation warnings | `C:\Temp\PolyNexus_release_walkthrough_20260726\dsc_standard_real` |
| DSC isothermal | repository PA6 isothermal DSC text | pipeline completed; Avrami/series Manifest published; validation warnings retained; shared walkthrough passed | `C:\Temp\PolyNexus_release_walkthrough_20260726\dsc_isothermal_real` |
| DSC non-isothermal | repository non-isothermal DSC XLS | pipeline completed; conversion is SI and kinetics are diagnostic because only one valid conversion curve was available; shared walkthrough passed using the SI entry | `C:\Temp\PolyNexus_release_walkthrough_20260726\dsc_nonisothermal_real` |
| SAXS static | one repository PAD8 EDF frame used as a real static input | pipeline completed; validation passed; shared Gallery/Editor/export/History walkthrough passed | `C:\Temp\PolyNexus_release_walkthrough_20260726\saxs_static_real` |
| WAXS static | repository PA6 `.raw` | pipeline completed; Manifest published; validation passed | `C:\Temp\PolyNexus_release_walkthrough_20260726\waxs_static_real` |
| WAXS temperature | repository PA6 EDF directory | pipeline completed; Manifest published; validation passed | `C:\Temp\PolyNexus_release_walkthrough_20260726\waxs_temperature_real` |
| IR standard | repository PA6 `YL.SPA` | pipeline completed; Manifest published; validation passed | `C:\Temp\PolyNexus_release_walkthrough_20260726\ir_standard_real` |
| SAXS temperature | repository PA6 EDF directory | eight Manifest entries are `ready`; scientific validation is false because Q* is contaminated and lamellar evidence is diagnostic-only; shared Gallery/Editor/export/History walkthrough passed | `C:\Temp\PolyNexus_release_walkthrough_20260726\saxs_temperature_real_after_colorbar_fix` |
| SAXS strain | repository five-frame PAD8 EDF directory | analysis and Manifest completed; available figures are diagnostic-only and retain that role; shared Gallery/Editor/export/History walkthrough passed | `C:\Temp\PolyNexus_saxs_real_final_check\test_real_published_run_preser1\output` |
| NMR liquid/solid H/C | repository NMR fixtures | covered by the real-data lifecycle matrix | `tests/test_nmr_lifecycle_closure.py` |
| WAXS strain/2D bounded subset | two repository EDF frames (0% and 400%) copied to external temp | pipeline completed; validation passed; shared Gallery/Editor/export/History walkthrough passed | `C:\Temp\PolyNexus_release_walkthrough_20260726\waxs_strain_subset_real` |
| IR temperature-2D bounded subset | two repository temperature CSV frames copied to external temp | pipeline completed; two expected temperature/2D-COS warnings retained; shared Gallery/Editor/export/History walkthrough passed | `C:\Temp\PolyNexus_release_walkthrough_20260726\ir_temperature_2d_subset_real` |
| WAXS strain complete 2D | repository five-frame EDF directory | 3 ready Manifest figures; complete Gallery/Editor/export/History walkthrough passed after bounded image-grid snapshot; validation passed | `C:\Temp\PolyNexus_full_2d_walkthrough\test_full_2d_real_published_ru0\output` |
| IR temperature-2D complete directory | repository 48-frame temperature CSV directory | 6 ready Manifest figures; complete Gallery/Editor/export/History walkthrough passed after bounded correlation snapshots and duplicate-frame suppression; expected 2D warnings retained | `C:\Temp\PolyNexus_full_2d_walkthrough\test_full_2d_real_published_ru1\output` |

## Performance correction

- WAXS strain publication image-grid snapshots now use vectorized sampling
  capped at 256×256 pixels per frame. Raw detector arrays remain unchanged
  for analysis. The complete real run measured about 13.5 seconds for
  analysis and 57.2 seconds for publication in the external performance
  probe.
- IR temperature-2D publication no longer emits duplicate generic per-frame
  spectrum/peak-fit figures when the temperature-series figures are present.
  Correlation figure snapshots use the existing 420×420 legacy-render limit;
  full analysis matrices remain on the result object. The complete real run
  measured about 3.7 seconds for analysis and 40.3 seconds for publication.
- The full 2D shared-lifecycle test passed `2` cases in `101.39s`:
  `python -m pytest --basetemp=C:\Temp\PolyNexus_full_2d_walkthrough tests/test_real_published_run_walkthrough.py -k full_2d -q`.
- A historical complete real published-run matrix passed `15` cases in
  `276.15s` with `python -m pytest tests/test_real_published_run_walkthrough.py
  -q`; its external pytest basetemp is no longer retained for independent
  replay. The expanded matrix added SAXS temperature/strain; the
  non-isothermal run selected its SI conversion figure and the SAXS strain run
  selected a diagnostic figure, preserving both publication roles. The
  currently retained SAXS strain output is listed in the table above.

## Runs not accepted as scientific sign-off

- The WAXS strain and IR temperature-2D runs now complete the shared software
  lifecycle, but this is not a human scientific publication sign-off.
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
