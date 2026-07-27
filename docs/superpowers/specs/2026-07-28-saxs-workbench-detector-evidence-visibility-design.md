# SAXS Workbench Detector Evidence Visibility Design

**Date:** 2026-07-28
**Status:** Approved for implementation in the current SAXS quality goal
**Related task:** `docs/agent/tasks/2026-07-28-saxs-workbench-detector-evidence-visibility.md`

## Goal

Make the existing raw-detector and sector-map quality evidence visible in the
SAXS Results Workbench without re-running detector analysis or changing any
scientific decision.

## Current gap

The raw detector report is already transported through static, temperature,
strain, parameter, History, Figure, and Export boundaries. The Workbench
currently summarizes 1D metric evidence and condition-axis defects, but does
not summarize the detector evidence source, level, frame coverage, or its
existing reason codes. Users therefore need to open Diagnostics or an export
bundle to discover that a report is sector-map evidence, raw-detector evidence,
partial, or unusable.

## Design

Add one presentation-only formatter beside the existing Workbench review
formatters. It consumes only the already persisted `detector_quality_report`
and `raw_detector_quality_report` mappings. For each non-empty report it emits
the existing level, source kind(s), evidence/total frame counts, coverage, and
up to three existing reason codes. A raw-detector report is labeled separately
from a sector-map report; the two fields are never merged.

The formatter returns an advisory risk/next-step pair only when the report is
Diagnostic or Unusable, incomplete, or contains reason codes. It does not
interpret a reason code as a new physical failure, infer geometry or mask
validity, sort frames, change a level, or authorize rescue/publication. The
full nested report remains in the existing diagnostics and persistence paths.

```text
parameters / restored History
  -> build_saxs_results_presentation()
       -> existing metric/axis/Guinier review formatters
       -> detector evidence formatter (read-only projection)
       -> ResultsTablePresentation.risk_text / next_text
```

## Testing and verification

Focused tests cover raw-only, sector-only, both-source, complete, partial, and
missing reports in English and Chinese. They assert that the input mappings are
not mutated and that no detector review text appears when the report is absent.
Existing SAXS consumer/export tests remain in the matrix. The task-scoped
verifier and `git diff --check` are required before the explicit allowlist
checkpoint.

## Non-goals

- No detector re-analysis, geometry calibration, mask inference, or new threshold.
- No changes to quality levels, physical gates, Figure roles, AI behavior,
  rescue behavior, publication eligibility, or persistence schema.
- No GUI algorithm branching on SAXS internals; the GUI consumes persisted DTO
  mappings only.
