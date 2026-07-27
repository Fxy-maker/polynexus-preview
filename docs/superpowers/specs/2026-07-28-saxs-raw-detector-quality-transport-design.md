# SAXS Raw Detector Quality Transport Design

**Date:** 2026-07-28
**Status:** Approved for implementation in the current SAXS quality goal
**Related task:** `docs/agent/tasks/2026-07-28-saxs-raw-detector-quality-transport.md`

## Goal

Carry trustworthy raw-detector quality evidence from an EDF image load through
SAXS preprocessing and the existing static, temperature-series, and
strain-series result contracts. The evidence must remain distinguishable from
the existing sector-map report and must not make a publication or rescue claim.

## Scope

The preprocessing boundary will build the existing `DetectorQualityReport` for
the raw image. Its inputs are deliberately narrow:

- the detector image itself;
- the mask already produced by `_build_mask()`;
- an explicitly named saturation value from the EDF header, when present;
- a beam center only when both center coordinates are explicitly present in
  the header.

The report is stored in the preprocessing payload. `SAXSEngine` retains one
report slot per loaded frame, including `None` for 1D or failed/missing input,
and supplies the aligned reports to the existing result-series APIs. Static
analysis receives the corresponding frame report through a
`raw_detector_quality_report` field. Temperature and strain series attach raw
reports by source index and reuse their existing conservative series
aggregation. The existing `detector_quality_report` field remains the
sector-map report for strain/orientation routes, so the two evidence sources
cannot overwrite each other.

## Scientific and safety boundaries

- `source_kind="raw_detector"` is used only for a raw image report;
  sector-integrated maps remain `source_kind="sector_map"`.
- Saturation is counted only from an explicit finite header value. The maximum
  pixel value is never used as a detector limit.
- No mask is inferred from image statistics. The only automatic mask input is
  the pre-existing `_build_mask()` result.
- A config-default beam center is not reported as header beam-center evidence.
  Missing or incomplete header coordinates remain missing in the report.
- No new physical threshold, quality gate, Figure role, AI action, frame
  interpolation, frame copying, or automatic rescue is introduced.
- A raw detector report can improve provenance and diagnostics, but it does not
  automatically raise any existing `DataQualityReport` or publication level.
  Geometry and mask scientific validity remain a human acceptance boundary.

## Data flow

```text
EDF image + header
  -> preprocess_pipeline(detector_header=header)
       -> existing _build_mask(image, cfg)
       -> explicit header saturation/beam-center extraction
       -> DetectorQualityReport(source_kind=raw_detector)
  -> SAXSEngine per-frame aligned report list
  -> static result or TemperaturePointResult / StrainPointResult
  -> existing series detector-quality summary
  -> existing parameters/figure/export consumers (raw field preserved)
```

The new optional argument preserves all callers that preprocess an in-memory
image without a header. Such callers still get a conservative raw-detector
inventory with unknown saturation and missing header beam-center evidence.

## Error handling

Invalid or absent header fields become the existing reason codes from
`build_detector_quality_report` (`detector_saturation_unknown`,
`beam_center_missing`, or the existing invalid-field codes). Header parsing
errors do not abort image preprocessing. A non-image input has no raw report;
its aligned slot is `None`, preserving missing-frame semantics.

## Verification

TDD must first demonstrate that a header-backed preprocessing payload currently
lacks the raw detector report, then pass after the minimum transport change.
Focused tests cover explicit saturation, existing dummy mask, missing center,
unknown saturation, strict JSON, and source-kind separation. The SAXS matrix and
structured task verifier are required. A replay of
`D:\PolyNexus\测试数据\saxs\PAD8原位拉伸` must show five aligned raw reports with
the explicit header provenance while preserving conservative levels and the
existing sector-map evidence. No generated replay output is committed.
