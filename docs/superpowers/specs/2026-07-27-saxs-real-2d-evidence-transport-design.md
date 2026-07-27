# SAXS Real 2D Evidence Transport Design

**Date:** 2026-07-27
**Status:** Approved for the next atomic implementation slice
**Related route:** `docs/superpowers/specs/2026-07-26-saxs-quality-analysis-program-design.md`

## Goal

Preserve the detector-quality evidence already produced for a sector-integrated
2D map when the real SAXS strain pipeline converts that map into
`StrainPointResult` and `StrainSeriesResult`. The existing evidence must reach
the series summary and the existing result/parameter transport without changing
any SAXS calculation or publication role.

## Evidence of the current gap

The repository's real PAD8 strain directory was replayed into an external
output root. The EDF probe was `(1028, 512)` `float64`; its header contained
sample-detector distance and beam-center fields, and all five loaded frames
reported `geometry_source=header` with confidence `0.95`. The run completed
with `validation_passed=True` and produced five sector maps.

The sector-map orientation evidence already contained a JSON-safe detector
report with `source_kind=sector_map`, approximately `0.787--0.789` coverage,
`nonpositive_pixels`, unknown saturation, and missing beam-center evidence.
However, the same run produced `None` for both the frame-level
`StrainPointResult.detector_quality_report` and the series-level
`StrainSeriesResult.detector_quality_report`. This loses a provenance field at
the exact real-data boundary even though orientation evidence still embeds it.

## Scope and non-goals

### In scope

- Return the existing detector report from `herman_from_sector_data` alongside
  the existing Herman and orientation fields.
- Copy that report into each `StrainPointResult` before the existing series
  aggregation helper runs.
- Preserve existing missing/failed behavior: absent sector data or a failed
  orientation analysis yields no fabricated detector report.
- Add focused regressions for the sector-map helper and strain series summary.

### Non-goals

- Do not reinterpret a sector map as a raw detector image.
- Do not infer a mask, saturation limit, beam center, detector geometry, or new
  physical threshold.
- Do not change pyFAI, EDF parsing, azimuthal integration, Herman calculation,
  orientation-axis calculation, quality-level rules, Figure roles, Workbench
  risk text, AI behavior, or publication eligibility.
- Do not claim real-data scientific sign-off from this transport fix.

## Design

`analyze_anisotropy` remains the single producer of the sector-map detector
report. `herman_from_sector_data` returns that already JSON-safe dictionary in
its result mapping. `analyze_strain_series` assigns it to the corresponding
point, then calls the existing `build_series_detector_quality_report` exactly
as before. If no point has a report, the existing `None` result is preserved.

```text
sector map
  -> analyze_anisotropy
       -> detector_quality_report (source_kind=sector_map)
       -> orientation_evidence
  -> herman_from_sector_data result
  -> StrainPointResult
  -> StrainSeriesResult detector summary
  -> existing parameters/Figure/Export consumers
```

The transport is intentionally one-way and lossless for the existing public
dictionary. The series summary remains conservative: partial coverage and
diagnostic detector levels are retained, and no orientation metric is folded
into generic 1D evidence.

## Verification contract

TDD must show a focused RED caused by the missing transport, then GREEN after
the minimal change. The focused test must assert `source_kind=sector_map`,
strict JSON safety, and non-null frame/series reports for supplied sector maps;
it must also retain the existing no-2D absence behavior. The task-scoped
verifier and exact SAXS matrix are required before an explicit allowlist
checkpoint.
