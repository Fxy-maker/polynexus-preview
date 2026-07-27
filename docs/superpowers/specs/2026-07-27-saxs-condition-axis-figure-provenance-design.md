# SAXS Condition-Axis Figure Provenance Design

Date: 2026-07-27
Status: approved working design

## Goal

Keep the existing `MetricEvidenceSummary.condition_axis` intact across the
read-only SAXS Figure/Manifest evidence binding boundary.

## Design

Add `condition_axis` to the existing `_COMMON_EVIDENCE_FIELDS` projection list
in `figure_evidence.py`. This is an allowlist extension, not a generic mapping
copy: all existing strict JSON conversion, enum/level validation, detached
mapping creation, and non-finite-to-`null` handling remain in force.

The change applies equally to frame-level and series-level metric evidence.
Temperature source-index and Guinier sequence evidence remain separate fields;
strain orientation evidence remains separate from 1D metric evidence.

## Data flow

```text
MetricEvidenceSummary.condition_axis
  -> _project_metric_collection()
  -> frame_records / series_record
  -> FigureDefinition recipe evidence
  -> Manifest figure.pnfig.json
```

No consumer reconstructs an axis or changes its status. A missing or malformed
mapping remains omitted as before, and existing attachment failure fallback is
unchanged.

## Verification boundary

Tests cover defective frame/series axes, strict JSON, detached nested values,
temperature source-index retention, strain orientation separation, and
FigurePipeline serialization. The full SAXS matrix and task verifier remain
required; this does not constitute real-data scientific acceptance.
