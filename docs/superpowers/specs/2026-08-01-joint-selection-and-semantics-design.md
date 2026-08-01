# Joint Selection and Result Semantics

Date: 2026-08-01
Status: approved for implementation planning
Scope: Joint workspace selection, source visibility, validation status, and
cross-technique conclusion boundaries.

## Problem

The Joint workspace currently makes two implicit choices:

1. It loads all samples and batches when opened and automatically checks every
   row containing at least two techniques.
2. For each selected batch it takes the newest run for each technique without
   exposing the source identity as a preflight decision.

The batch boundary is useful for provenance, but it is not proof that files are
scientifically comparable. A wrongly imported source can therefore appear as a
cross-technique conflict. Missing inputs are also represented as warning-like
validation rows, which makes absent evidence look like disagreement.

## Goals

- Make the user selection, rather than an implicit recommendation, the gate for
  Joint comparison and publication.
- Keep one Joint row equal to one explicitly selected batch.
- Make the exact source run and source file visible before report generation.
- Separate measured disagreement, unavailable checks, and non-comparable data.
- Keep source-specific values and evidence; do not synthesize an automatic
  cross-technique Xc.
- Keep NMR solid-C assignment-limited results out of Joint Xc comparison.
- Correct the real PA6 Joint fixture so it uses a PA6 SAXS source rather than
  the unrelated `8-000-s...edf` source.

## Non-goals

- No automatic sample identity inference from filenames.
- No technique-priority rule for DSC, WAXS, SAXS, or NMR.
- No change to technique-specific Xc formulas in this task.
- No scientific assignment of solid-C peaks or ppm calibration.
- No publication approval from a Joint report.

## Selection Contract

`collect_joint_dataset()` continues to support explicit `sample_ids` and
`batch_ids`. The standalone Joint widget may load candidate rows for browsing,
but it must not check rows during refresh. The user must explicitly check rows
or arrive from Sample Browser with selected batch IDs.

The comparison unit is a single `batch_id`. Rows from different batches are
never merged automatically, even when their sample names match. Within one
selected batch, the current newest-run-per-technique behavior is retained for
this slice, but each selected run is surfaced in the source preflight and
provenance. A later run-selection feature can replace this policy without
changing the batch contract.

The recommended-selection action remains available as an explicit user action.
It may suggest rows with at least two techniques, but it must never run during
refresh or silently affect a report.

## Source Preflight

Before generating a Joint overview, the UI and report context expose one source
entry per selected technique:

- sample ID and displayed sample name;
- batch ID, label, and condition values;
- technique and submodule;
- analysis run ID and created time;
- original input/source file when available;
- analysis evidence status and evidence reasons;
- whether the source contributes to the requested comparison.

The system does not infer that two files are the same specimen from filenames.
If the user selected a batch whose sources have inconsistent or incomplete
conditions, the report keeps the values but marks the relevant comparison
`not_comparable` or `review_required` rather than treating the result as a
normal conflict.

## Result Semantics

Joint validations use three distinct statuses:

- `DIFF`: both required values exist and fail the comparison rule;
- `SKIP`: a required value or method output is unavailable, so no comparison
  was performed;
- `NOT_COMPARABLE`: source identity, condition compatibility, or evidence
  policy prevents a scientific comparison.

`SKIP` is not a warning or error and does not increment conflict counts. A
`DIFF` retains both source values, units, tolerance, evidence status, and run
provenance. A diagnostic-only or assignment-limited source may remain visible
for context but cannot make a publication-ready Joint conclusion.

Joint continues to report source-specific values such as DSC enthalpy Xc,
WAXS peak-area Xc, and SAXS structural metrics. It does not calculate or label
an automatic consensus Xc. The Joint conclusion is limited to coverage,
agreement, differences, and review targets; reviewer acceptance remains a
separate gate.

NMR solid-C results with `Xc_assignment_status=assignment_limited` are excluded
from Joint Xc comparisons while their spectrum/assignment limitation remains
visible in source evidence.

## Real-Data Fixture Boundary

The real Joint lifecycle fixture must select the PA6 SAXS input under
`测试数据/saxs/普通小角` and must not use the unrelated `8-000-s...edf` input
from the PAD8 tensile data. The test still proves transport and provenance; it
does not claim that the three technique outputs are scientific ground truth.

## GUI and Export Behavior

- Refresh shows all candidate rows unchecked.
- Explicit checkboxes and Sample Browser batch selection control the report
  scope.
- The generated report and exported source table include the preflight fields.
- A report with no selected rows cannot run.
- The existing figure lifecycle remains available, but figure/report status
  remains diagnostic or review-required when sources are not comparable or
  publication authorization is absent.

## Verification

Focused tests will cover:

- no implicit selection after refresh;
- explicit batch selection only;
- recommended selection only after an explicit button action;
- newest source run and source provenance within a selected batch;
- `SKIP` not counted as a conflict;
- non-comparable conditions retained without automatic precedence;
- assignment-limited solid-C excluded from Joint Xc comparison;
- PA6 real fixture source resolution;
- existing Joint report, GUI, figure manifest, and export contracts.

Required repository checks after implementation:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-01-joint-selection-and-semantics.md --changed --types
python scripts/boundary_audit.py --root D:\PolyNexus --json
git diff --check
```

## Approval Boundary

This design does not choose a scientific winner among DSC, WAXS, SAXS, or NMR.
It only prevents the software from choosing comparison sources or inventing a
consensus. Scientific interpretation remains a reviewer decision after the
source preflight is accepted.
