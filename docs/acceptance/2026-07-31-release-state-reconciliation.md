---
kind: acceptance
status: recorded
date: 2026-07-31
title: Current release-state evidence reconciliation
task: docs/agent/tasks/2026-07-31-release-state-reconciliation.md
---

# Acceptance record

## Current disposition

The software is **conditionally ready for further scientific review**, not
finally approved for publication. Automated transport and structural coverage
are broad; the remaining scientific and owner gates are intentionally visible.

## Evidence classification

| Area | Latest evidence | Class | Safe consequence |
| --- | --- | --- | --- |
| DSC/WAXS/IR/NMR non-SAXS lifecycle | `12 passed, 3 deselected, 11 warnings in 291.31s`, exit `0` | automated lifecycle | transport through Manifest/Gallery/Editor/Export/History is verified; scientific approval remains separate |
| Joint real data | `1 passed in 15.55s`, exit `0` | automated provenance | source/run transport is verified; unresolved conflicts stay diagnostic-only |
| IR mapping | native route shows `Review required`, `review_missing`; no native map/coordinate payload | structural/visual + scientific gate | diagnostic-only until source-matched dimension, origin, ROI, flattening, and calibration evidence is reviewed |
| NMR solid-C | native route shows `Review required`, `review_missing`; current axis is default-range and uncalibrated | structural/visual + scientific gate | assignment-limited; Xc cannot be promoted without assignment truth and calibrated ppm |
| Joint | native route shows `2 errors, 2 warnings`, `blocked`, `allowed=false`, `conflict_error` | structural/visual + scientific gate | no automatic DSC/SAXS/WAXS priority; unresolved conflict is diagnostic-only |
| Shared Workbench | Results/Gallery/History/Editor/Export and fallback routes have automated/native evidence | structural/visual | restarted normal-size all-mode walkthrough and owner acceptance remain open |
| SAXS existing-review sync | focused `69 passed`; quality `297`, preprocessing `106`; full SAXS matrix tool timeout `124` with no summary | automated focused + incomplete full matrix | evidence transport is checkpointed; timeout is not a full-matrix pass and scientific release remains open |
| Final release | existing decision packet says `conditional` | release approval | final owner authorization remains open |

## Remaining gates

1. IR needs a source-matched vendor-native mapping or coordinate export that
   confirms dimension order, physical origin, ROI bounds, flattening order, and
   calibration for the actual sample.
2. NMR solid-C needs a reviewer-approved assignment truth set and a confirmed
   calibrated ppm axis; ambiguous peaks remain unassigned and Xc remains gated.
3. Joint needs reviewer-confirmed scientific interpretation of the conflicting
   contributing results; operational severity does not invent scientific
   precedence.
4. A restarted, normal-size GUI walkthrough must cover the required routes and
   record owner acceptance or defects.
5. Final scientific and publication authorization must be issued by the
   project owner after the preceding gates close.

## Verification record

The following checks are required for this documentation task:

```powershell
python scripts/boundary_audit.py --root D:\PolyNexus --json
python scripts/verify.py --task docs/agent/tasks/2026-07-31-release-state-reconciliation.md --changed --types
git diff --check
```

Only complete summaries and exit codes are recorded as passes. Storage report
and clean are not part of this task and no `--apply` is authorized here.

Observed outcomes:

- `python scripts/boundary_audit.py --root D:\PolyNexus --json` exited `0`.
- `python scripts/verify.py --task docs/agent/tasks/2026-07-31-release-state-reconciliation.md --changed --types` exited `0`; quality `297 passed`, preprocessing `106 passed`, task/memory, Ruff, compile, type baseline, and whitespace checks passed.
- `git diff --check` exited `0`.

## Workspace boundary

Only the four documentation files named in the task card may enter this
checkpoint. Parallel SAXS changes, memory edits, and test/storage artifacts
remain untouched.
