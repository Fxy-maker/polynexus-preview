---
task_id: 2026-07-31-full-goal-release-evidence-audit
kind: release-readiness
status: completed
date: 2026-07-31
title: Audit full-goal evidence and remaining release gates
---

# Full-goal release evidence audit

## Goal

Give the overall PolyNexus goal one current, evidence-linked classification
across SAXS, DSC, WAXS, IR, NMR, Joint, and the shared Results Workbench.

## Non-goals

- Do not change analysis algorithms, thresholds, quality levels, physical gates,
  rescue/AI policy, Figure roles, Manifest roles, or export semantics.
- Do not invent IR vendor coordinates, ROI bounds, detector calibration, NMR
  assignments, ppm calibration, or Joint conflict precedence.
- Do not delete or move test data, real datasets, source files, or runtime
  directories.
- Do not treat automated route coverage as scientific approval or final release
  authorization.

## Affected boundaries

- Evidence and release classification only.
- Shared Results/Gallery/History/Editor/Export acceptance records.
- Scientific review boundaries for IR mapping, NMR solid-C, and Joint.
- Parallel SAXS post-Workbench work is read-only context for this audit and is
  excluded from the changed-file allowlist.

## Implementation plan

1. Inventory the existing module and shared Workbench evidence from the
   referenced task and acceptance records, including the final SAXS parallel
   record once it is complete.
2. Classify each item as automated, structural-only, visual-review,
   scientific-review, or release-approval evidence without changing its
   publication consequence.
3. Record the remaining IR, NMR solid-C, Joint, restarted-GUI, and final-owner
   gates in the acceptance note.
4. Run the boundary audit, task-scoped verifier, and diff check, then create
   one explicit allowlist checkpoint for this audit's three documents.

## Acceptance criteria

- [x] Each technique and the shared Workbench has a named evidence class and
      source record.
- [x] Automated, structural, visual, scientific, and release-approval gates
      are not conflated.
- [x] Open IR, NMR, Joint, GUI, and final authorization conditions have an
      explicit safe publication consequence.
- [x] SAXS evidence is recorded only from the parallel task's final task card
      and acceptance record, with no duplicated or overwritten memory edits.
- [x] Boundary audit, task-scoped verifier, and diff check have exact outcomes.
- [x] One allowlist checkpoint contains only this audit's three documentation
      files.

## Current evidence classification

The detailed acceptance note is the authoritative record for this audit. The
classification is intentionally conservative:

| Area | Current evidence | Classification | Safe disposition |
|---|---|---|---|
| SAXS | Shared thread reports PAD8 2D acceptance and Static/Temperature/Strain real lifecycle shards; its task-scoped verifier and checkpoint must be read from the final parallel record | automated/conditional | preserve existing source-specific gates; no release claim until the parallel record is final |
| DSC | Existing lifecycle, evidence, Figure/Manifest, Workbench, Gallery/Editor/Export, AI-off and fallback tests | automated plus structural | still needs restarted-GUI visual review and scientific owner approval |
| WAXS | Existing static/temperature/strain/2D lifecycle and publication/evidence routes | automated plus structural | raw detector/geometry and scientific review remain separate gates |
| IR standard/temperature | Existing input, evidence, figure, route, fallback, and review contracts | automated plus structural | scientific interpretation and final release remain conditional |
| IR mapping | Official Thermo Scientific OMNIC Picta profile is documented: X is area-map column/Stage-X, Y is row/Stage-Y, both in `um`, stage-home origin `(0, 0)`, ROI follows the vendor step grid; no native sample map/coordinate export is present | structural-only/vendor profile | sample-specific mapping remains `review_required` and diagnostic-only |
| NMR liquid H/C | Existing lifecycle and provenance routes | automated plus structural | scientific assignment/release remains conditional where source truth is absent |
| NMR solid H/C | Existing labels and axis provenance are surfaced; no approved assignment truth set or calibrated ppm axis is available | structural-only/assignment-limited | preserve raw peaks and provenance; prohibit Xc promotion |
| Joint | Source/run transport, report, figures, and weighted conflict evidence exist | automated plus structural | unresolved scientific conflicts remain diagnostic-only; no automatic technique priority |
| Shared Workbench | Native route captures cover Results/Gallery/History/Editor/Export and fallback paths; screenshots are supplementary | structural/visual-review | restarted-GUI normal-size review and owner acceptance remain open |
| Final release | Release packet records a conditional decision and named decision fields | release-approval | project remains conditional until scientific, visual, and owner gates close |

## Open gates that cannot be closed by this audit

1. A source-matched IR mapping payload or coordinate export is needed to
   confirm sample-specific dimension order, origin, ROI bounds, flattening
   order, and calibration.
2. NMR solid-C needs an approved assignment truth set and calibrated ppm axis
   before any Xc promotion decision.
3. Joint needs a reviewer-confirmed scientific interpretation for unresolved
   conflicts; operational severity does not assign scientific precedence.
4. A restarted, normal-size GUI walkthrough must cover all required routes and
   record visual defects or acceptance.
5. The project owner must issue final scientific and release authorization after
   the above evidence is available.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-31-full-goal-release-evidence-audit.md`
- `docs/superpowers/plans/2026-07-31-full-goal-release-evidence-audit.md`
- `docs/acceptance/2026-07-31-full-goal-release-evidence-audit.md`

## Pre-existing changes left untouched

The shared checkout contains parallel SAXS edits, memory-file edits, pytest
temporary directories, external basetemps, and other historical work. None is
part of this task's allowlist.

## Verification evidence

- The parallel SAXS task is now `completed` and records PAD8
  `4 passed in 18.60s`, real Static/Temperature/Strain lifecycle
  `3 passed, 12 deselected in 90.79s`, task verifier exit `0`, and storage
  dry-run with `88` artifacts and `0` removed.
- `python scripts/boundary_audit.py --root D:\PolyNexus --json` exited `0`.
- `python scripts/verify.py --task
  docs/agent/tasks/2026-07-31-full-goal-release-evidence-audit.md --changed
  --types` exited `0`; quality gate `297 passed`, preprocessing gate `106
  passed`, task/memory, Ruff, compile, type baseline, and whitespace checks
  passed.
- `git diff --check` exited `0`.
- The first verifier attempt hit a pre-existing `tests/_tmp_phase3`
  `__pycache__` permission error; the immediate rerun produced the complete
  passing result above. It is not counted as a product test failure.

## Checkpoint

This documentation-only audit is ready for an explicit three-file allowlist
checkpoint. It does not close the scientific, restarted-GUI, or final owner
authorization gates listed above.

## Verification

```powershell
python scripts/boundary_audit.py --root D:\PolyNexus --json
python scripts/verify.py --task docs/agent/tasks/2026-07-31-full-goal-release-evidence-audit.md --changed --types
git diff --check
```

The boundary audit passed with exit code `0`. The first task verifier run
correctly rejected this card because the required `Implementation plan` and
`Verification` sections were absent; those sections are now present and the
task verifier is rerun before checkpoint creation.
