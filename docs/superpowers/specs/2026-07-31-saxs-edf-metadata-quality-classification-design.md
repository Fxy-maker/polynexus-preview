# SAXS EDF Metadata and Pixel-Quality Classification Design

**Date:** 2026-07-31
**Status:** Approved for implementation
**Related task:** `docs/agent/tasks/2026-07-31-saxs-edf-metadata-quality-classification.md`

## Goal

Make the existing SAXS EDF path distinguish metadata presence, detector-data
encoding, and scientific calibration validity without introducing a new
DetectorMetadata DTO or changing publication gates.

## Scope

The existing `detector_quality_report` will be extended with a normalized,
JSON-safe metadata inventory. The reader will preserve the known EDF fields
needed to explain this detector and its processed image representation:
detector identity, geometry, exposure, threshold/cutoff fields, dummy/mask
fields, flat-field status, and background-correction information.

The pixel report will retain the existing conservative `nonpositive_pixels`
signal and additionally classify exact background-floor values and configured
dummy-sentinel values. It will not silently promote the data to a usable
quality level.

The saturation path will distinguish an explicit positive saturation value from
the real-file `Saturation=0` status-like field. `ThresholdSetting` will remain
metadata only. `CountCutoff` will be recorded as an instrument cutoff but will
not be used as a saturation threshold unless the header explicitly identifies
it as such; this avoids guessing detector semantics.

Geometry and mask calibration validity remain `not_assessed`. A new metadata
presence/source inventory will make clear that the fields were read from the
EDF header even when independent calibration evidence is absent.

## Boundaries

- The actual SAXS path is `polynexus/core/saxs_engine/io.py` and
  `polynexus/core/saxs_engine/preprocess.py`.
- Existing `DetectorQualityReport` and series transport contracts remain the
  public boundary; no new DTO is introduced.
- Sector-map reports remain separate from raw-detector reports.
- No generated outputs, real datasets, GUI behavior, publication eligibility,
  or scientific gate thresholds are changed.

## Acceptance criteria

- The four EDF frames under `Desktop/edf/610` expose the same detector identity
  and complete header-backed geometry inventory.
- `DetectorModel`, serial number, cutoff/threshold, flat-field, dummy, and
  background fields are available in the raw-detector report.
- The exact `-BackgroundCorrectionConstant` population is separately counted
  as a background-floor classification while the conservative raw
  nonpositive count remains visible.
- Configured dummy-sentinel pixels are separately counted and remain part of
  the existing mask report.
- `Saturation=0` does not become a false positive saturation threshold;
  explicit positive saturation values still work in existing tests.
- Geometry and mask validity remain `not_assessed`, while metadata presence is
  reported as complete/header-backed.
- Single-frame and four-frame SAXS regressions pass, and existing SAXS quality
  and transport tests remain green.

## Error handling

Malformed or absent optional header fields become `None` or an explicit
`unknown` source in the JSON-safe report. They do not abort EDF image loading.
The report remains conservative when detector-field semantics cannot be
confirmed.
