# Current Release Evidence Reconciliation Design

## Goal

Keep one current release classification that distinguishes automated coverage
from scientific and human approval after the formal full/boundary verifier
finishes.

## Evidence flow

The new acceptance record cites the formal task for the complete current-head
wrapper result, the SAXS bridge task for its focused and SAXS-matrix results,
and the existing full-goal audit for module-by-module scientific boundaries.
The record supersedes stale current-status wording about the old timeout but
does not rewrite the historical task evidence.

## Classification contract

- Automated full-repository tests and boundary scans establish engineering
  evidence only.
- IR mapping remains `review_required` and diagnostic-only without
  sample-matched native coordinate, ROI, flattening, and calibration evidence.
- NMR solid-C remains assignment-limited without approved assignment truth and
  a calibrated ppm axis; Xc promotion remains prohibited.
- Joint conflicts remain diagnostic-only until a reviewer confirms scientific
  interpretation; operational severity cannot assign technique priority.
- Restarted-GUI visual acceptance and owner scientific/release authorization
  remain independent release gates.

## Non-goals

No source, test, threshold, provider, Figure, Manifest, Workbench, Gallery,
Editor, Export, AI, or storage behavior changes are part of this record.
