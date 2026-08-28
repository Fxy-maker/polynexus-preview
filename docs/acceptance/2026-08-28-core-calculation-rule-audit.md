# Core calculation rule-tier audit — 2026-08-28

## Scope and invariant

This is a read-only audit of the shared path from canonical conversion through
Core/provider, `ComputeRun`, and writing-metric projection. No algorithm,
threshold, input template, source artifact, or evidence eligibility changes in
this record.

A recommendation is valid only when it names both the producing condition and
the observed public `ComputeRun` or writing-metric result.

## Shared route

```text
canonical converter -> technique provider/Core -> ComputeRun
                    -> result metrics/warnings -> writing metrics/evidence
                    -> CLI, Agent/Codex, and GUI consumers
```

## Ledger

| Technique | Rule / owner | Trigger | Current computation outcome | Current evidence outcome | Observed tier | Recommended tier | Evidence | Follow-up |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DSC | `dsc_kinetics.relative_crystallinity_isothermal` | Too few valid points, no positive exotherm, zero event width, or zero exotherm area | The affected event cannot define a valid conversion curve; unrelated events/runs remain executable | No metric is emitted for the affected quantity | `structural_block` (scoped to that metric/event) | Retain | `dsc_engine/dsc_kinetics.py`; `test_dsc_kinetics.py` | Keep the block local; do not reject other segments in the same file |
| DSC | `dsc_kinetics.avrami_fit` | Too few fit points or poor fit quality (`R² < 0.95`) | Avrami parameters may still be returned when a fit exists | Writing projection keeps values but marks them `diagnostic_only` with `low_avrami_r_squared` | `calculation_warning` + `evidence_restriction` | Retain | `project_workflow/writing_metrics.py`; DSC kinetics tests | Preserve numeric result and warning; no automatic Results promotion |
| DSC | Adaptive event baseline | Endpoint baseline unavailable/unclosed, or endpoint-vs-tail sensitivity | Tail-constant fallback or endpoint-linear selection still produces a deterministic event result | Sensitivity/boundary flags are retained as quality metadata and restrict writing eligibility | `calculation_warning` | Retain | `docs/acceptance/2026-08-28-dsc-adaptive-baseline.md` | Already implemented; no further gate relaxation in this audit |
| DSC | Multi-rate regression | Fewer than two valid rates, no common temperature window, or invalid regression | The requested multi-rate kinetic scalar is mathematically undefined; ordinary thermal/event values remain available | Only the regression quantity is absent/diagnostic | `structural_block` (scoped to regression) | Retain | `dsc_engine/dsc_kinetics.py`; focused DSC matrix | Keep curve-level outputs independent of regression failure |
| FTIR | Canonical 1-D mapping | Ambiguous axis/intensity columns, invalid mapping proposal, or no numeric pairs | Canonical template cannot unambiguously represent x/y data | `needs_input` before provider execution; no fabricated spectrum | `structural_block` | Retain | `canonical_experiments/one_dimensional.py`; `test_ftir_no_auto_material_identification.py` | AI may propose a source-bound mapping, but must not guess silently |
| FTIR | Material identity / peak assignment | Material hint absent or literature-backed assignment unavailable | Generic spectrum, peak positions, widths, and counts remain calculable | Material-specific assignments and uncalibrated Xc are diagnostic/review-only | `evidence_restriction` | Retain | `project_workflow/writing_metrics.py`; FTIR acceptance note | Do not block generic processing; require review for phase/material claims |
| FTIR | Uncalibrated crystallinity index | No validated absolute calibration | An index value can be calculated and retained | Emitted as `diagnostic_only` with `absolute_crystallinity_not_supported` | `evidence_restriction` | Retain | `writing_metrics._ir` | Keep index visible in evidence package, never label it absolute Xc |
| SAXS | 1-D profile sanitization/shape | Missing, non-numeric, length-mismatched, or empty q/I arrays | No valid profile exists for the affected analysis | Unusable/diagnostic result; no finite metric is claimed | `structural_block` (affected profile/metric) | Retain | `saxs_engine/core.py`; `test_saxs_1d_method_evidence.py` | Keep source diagnostics and preserve any independent legacy outputs |
| SAXS | q-unit, beam-stop, detector geometry, or calibration uncertainty | q unit unresolved, low-q truncation, detector-quality issue, or calibration context incomplete | Numerical fits may still be computed on the surviving profile | Method evidence stays `Diagnostic`/non-applicable; finite values remain traceable | `calculation_warning` or `evidence_restriction` | Retain | `saxs_engine/core.py`; SAXS quality-contract tests | These are not blanket calculation blocks; expose warnings and per-metric status |
| SAXS | Porod/Kratky/invariant/lamellar applicability | Applicability unknown, slope/plateau unstable, invalid invariant, or insufficient lamellar support | Legacy method outputs are preserved where finite; evidence builder marks unsupported methods diagnostic | `metric_evidence.applicable != true` maps to `diagnostic_only` | `evidence_restriction` (when finite) | Retain | `test_saxs_1d_method_evidence.py`; `writing_metrics._saxs` | Keep values for exploration; do not promote without method support |
| SAXS | Orientation tracking | Missing/unstable axis or insufficient sector support | Orientation quantity for that frame/track is unavailable; other SAXS metrics continue | Orientation evidence is `blocked`/`unavailable` and remains diagnostic | `structural_block` (orientation only) | Retain | `saxs_engine/saxs_strain.py`; orientation contract tests | Scope the block to orientation, not the whole run |
| WAXS | Reader/array validity | Unsupported/unreadable source, invalid 2θ/intensity shape, or no usable scan | No physically meaningful pattern can be analyzed | Run is failed/unusable; no finite WAXS claim | `structural_block` | Retain | `waxs_engine/core.py`; WAXS publication tests | Preserve source error and avoid fallback values |
| WAXS | Peak/physical-support requirements | Weak/insufficient peaks, unresolved phase support, or amorphous partition not defensible | Peak-derived values may still be finite | `Xc_pct` and Scherrer size remain `diagnostic_only`; W-H reliability is diagnostic when support is low | `evidence_restriction` | Retain | `project_workflow/writing_metrics.py`; `test_waxs_publication_cutover.py` | Do not discard finite diagnostics; require support before Results use |
| NMR | Canonical table conversion | Unsupported/unreadable source or ambiguous/no numeric x/y mapping | Spectrum cannot be formed from the source | `needs_input`/blocked before provider execution | `structural_block` | Retain | `canonical_experiments/one_dimensional.py`; `test_nmr_shared_entry.py` | Keep vendor/FID envelopes replayable without inventing data |
| NMR | Generic spectrum and peak metrics | Material name absent, or polymer library assignment unavailable | ppm-axis spectrum, peak count/area/FWHM/SNR and generic regions remain calculable | Generic assignments are retained without polymer identity; no fabricated material labels | `evidence_restriction` | Retain | `test_nmr_shared_entry.py`; `test_nmr_engine.py` | This is the desired flexible default |
| NMR | Solid 13C crystallinity | Crystalline/amorphous phase pair unsupported or assignment confidence below gate | Xc is NaN or may be numerically present but phase interpretation is limited | `Xc_assignment_status=assignment_limited`; not a Results claim | `evidence_restriction` (or scoped structural absence when no areas) | Retain | `nmr_engine/core.py`; NMR engine tests | Keep the phase-support reason and allow human/AI context correction |

## Cross-entry visibility finding

The inspected shared route retains converter outcomes, provider parameters,
quality flags, metric evidence, and writing eligibility in `ComputeRun` and
`EvidencePackageView`. Focused GUI/ComputeRun tests did not show a consumer that
silently upgrades diagnostic values or drops the public warning/status fields.
Therefore no cross-entry reclassification is justified by this audit. Any
future UI simplification should consume these projections rather than creating
a second gate or private metric representation.

## Prioritized recommendations

### Candidate: none confirmed in this read-only audit

- Current behavior: All inspected hard exits correspond either to an undefined
  mathematical quantity or to an invalid/ambiguous canonical input; finite
  values already survive as warnings or diagnostic evidence where appropriate.
- Why a finite result can or cannot exist: Empty/ambiguous arrays and missing
  required coordinates cannot define the requested quantity. Weak fit,
  calibration, applicability, and phase-support limits do not necessarily
  prevent a numerical value and are already represented separately.
- Proposed tier: retain the current scoped tiers; no automatic downgrade.
- Evidence boundary after any future change: diagnostic values remain
  `diagnostic_only` until method support and human review are present.
- Required future regression: preserve the focused matrices listed below and add
  a regression for every approved scientific rule change before implementation.

## Verification evidence

- `python -m pytest -p no:cacheprovider -q tests/test_dsc_kinetics.py tests/test_dsc_canonical_isothermal_conversion.py tests/test_ftir_no_auto_material_identification.py tests/test_project_writing_metrics.py` → **42 passed, 2 warnings** (existing polynomial-fit warnings).
- `python -m pytest -p no:cacheprovider -q tests/test_saxs_1d_method_evidence.py tests/test_saxs_mode_evidence_contract.py tests/test_waxs_publication_cutover.py tests/test_project_writing_metrics.py` → **21 passed**.
- `python -m pytest -p no:cacheprovider -q tests/test_nmr_shared_entry.py tests/test_compute_service.py tests/test_evidence_package_view.py --maxfail=1` → **57 passed, 3 skipped**.
- `git diff --check` and the structured task verifier are required before the documentation checkpoint; no production source or raw dataset was changed by this audit.

## Known limitations and follow-up

- This document does not change thresholds, templates, algorithms, or evidence
  promotion policy. A concrete scientific decision to relax a rule must become
  a separate task card with test-first implementation and human review.
- The full repository historical failure set remains a separate release-boundary
  issue; it is not evidence that these calculation tiers are scientifically
  wrong.
- NMR’s full real-instrument fixture subset was not rerun in this audit because
  it depends on external fixtures; shared-entry and public-contract coverage is
  recorded above.
