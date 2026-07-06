# PolyNexus deep physics model enhancement patch bundle

Generated on 2026-07-06 from isolated worktree:

`C:\Users\Fan Xuyi\.config\superpowers\worktrees\PolyNexus\integrate-phys-confidence`

Branch:

`physics-quality-models-v1`

Base commit:

`6e2adaf docs: add physical confidence integration patch bundle`

## Included commits

1. `f1db267 docs: plan deep physics model enhancements`
2. `474182d chore: add cjk font fallback for exports`
3. `c153006 feat: add dsc multibaseline crystallinity uncertainty`
4. `c5bb3d7 feat: propagate waxs size uncertainty`
5. `22e990b feat: score nmr assignments with polymer library`
6. `9ea60ee chore: make core physics warnings contextual`
7. `7450335 chore: normalize responsibility boundary copy`

## What changed

- Engineering quality:
  - Added CJK font fallback before figure export to avoid Arial missing-glyph warnings.
  - Added core guard tests for generic physics-engine warning logs.
  - Replaced generic DSC/WAXS/NMR warning messages with contextual fallback messages.
  - Normalized responsibility-boundary copy so Chinese UI/history still includes the stable `Boundary` marker.

- DSC:
  - Added multibaseline and boundary-shift reintegration around melting/cold crystallization events.
  - Exported `DHm_Jg_mean/std`, `DHcc_Jg_mean/std`, `Xc_pct_mean/std/ci95`, `baseline_variant_count`, and `integration_variant_count`.
  - Fed Xc uncertainty distribution into `analysis_evidence`; high `Xc_pct_ci95` downgrades crystallinity reliability.

- WAXS:
  - Added Caglioti/constant instrument-broadening helper.
  - Added per-peak Scherrer size records with propagated uncertainty.
  - Added weighted Williamson-Hall output with `D_WH_uncertainty_nm`, `epsilon_WH_uncertainty_pct`, `WH_fit_r_squared`, and `size_reliability_status`.
  - Surfaced these fields in WAXS `phase_evidence` and `structure_evidence`.

- NMR:
  - Normalized the built-in 13C polymer assignment database into scored records.
  - Added assignment-library scoring: `library_match_fraction`, `assignment_confidence`, `phase_pair_support`, `solvent_overlap_penalty`, `matched_library_count`, and `assignment_library_source`.
  - Added conservative Xc assignment gate: supported only when phase-pair support is present and solvent overlap penalty is low.
  - Surfaced assignment scoring in `analysis_evidence` for AI/context consumers.

## Verification

Fresh verification in this worktree:

```powershell
python -m compileall polynexus tests -q
# passed

pytest tests/test_core.py tests/test_dsc_engine.py tests/test_waxs_residual_analyzer.py tests/test_waxs_temperature.py tests/test_nmr_engine.py tests/test_analysis_evidence.py -q
# 83 passed

pytest tests/test_main_window_persistence.py -q
# 182 passed

pytest -q
# 608 passed
```

## Merge note

Do not blindly merge into `D:\PolyNexus` while that main worktree still has uncommitted chart post-processing changes. Recommended sequence:

1. Commit or stash the current `D:\PolyNexus` chart/UI work.
2. Merge or cherry-pick this branch.
3. Re-run `python -m compileall polynexus tests -q` and `pytest -q`.

Patch files in this directory can also be applied one by one with `git am` after the main worktree is clean.
