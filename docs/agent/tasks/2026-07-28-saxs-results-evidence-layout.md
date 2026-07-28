# Task: SAXS Results evidence layout readability

**Status:** checkpointed locally after verification

## Goal

Keep long SAXS risk and next-step evidence inside the Results viewport so
reviewers can read the full diagnostic text without horizontal clipping.

## Non-goals

This is a GUI presentation fix only. The change may adjust Qt label sizing
policy for the existing Results evidence labels, but it must not change the
evidence strings, reason codes, quality levels, physical gates, rescue logic,
AI behavior, persistence, Figure/Manifest/Export contracts, or the native GUI
harness.

## Affected boundaries

- `polynexus/gui/main_window_results_mixin.py`: existing Results summary and
  review labels only.
- `tests/test_saxs_results_evidence_layout.py`: Qt geometry regression.

## Acceptance criteria

- [ ] Long risk and next-step text does not make the Results summary group's
  minimum size expand to the text's unbounded single-line width.
- [ ] Summary and review evidence labels use a horizontally shrinkable policy and
  retain word wrapping.
- [ ] The exact text supplied by `_set_results_summary()` remains available from
  the labels; no display-only text rewrite is introduced in this task.
- [ ] Existing MainWindow persistence, Results Workbench, and SAXS tests remain
  green.
- [ ] Verification uses the repository-managed external test storage and records
  the exact command outcomes before checkpointing.

## Implementation plan

1. Add a Qt regression that supplies long risk and next-step strings and
   observes the current unbounded `Preferred` label policy in RED.
2. Configure the existing Results summary and review labels with zero minimum
   width and `QSizePolicy.Ignored` horizontally while retaining word wrapping
   and exact text assignments.
3. Run the focused GUI slice, complete SAXS matrix, structured verifier, and
   diff check; update this card with exact evidence and create one explicit
   allowlist checkpoint.

## Verification plan

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_results_evidence_layout_red'
python -m pytest -q tests/test_saxs_results_evidence_layout.py

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_results_evidence_layout_focus'
python -m pytest -q tests/test_saxs_results_evidence_layout.py tests/test_main_window_results_mixin.py tests/test_saxs_workbench_review_readability.py tests/test_saxs_results_table_service.py

$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_results_evidence_layout_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-results-evidence-layout.md --changed --types
git diff --check
```

## Verification

The commands above include the task-scoped verifier invocation:
`python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-results-evidence-layout.md --changed --types`.

## Evidence before checkpoint

- RED: `1 failed` in `3.15s`; the expected assertion showed the existing
  `Preferred` horizontal policy on the risk label.
- Focused GUI/Workbench slice: `63 passed` in `4.14s`.
- Exact SAXS matrix: `456 passed, 6 warnings` in `268.18s`. Warnings are the
  existing Arial glyph and missing-geometry warnings.
- Structured verifier passed: task-check valid, Ruff and compile passed,
  quality gate `287 passed`, preprocessing gate `106 passed`, and whitespace
  passed.
- Fresh native Windows Qt SAXS route capture: `3 passed, 14 deselected` in
  `56.53s`, covering Static/Temperature/Strain Results, Gallery, History, and
  Editor routes. Captures are external under
  `D:\PolyNexus_native_saxs_results_evidence_layout_20260728` and are not
  checkpoint files. The Results surface shows ordered risk/next lines within
  the bounded layout; reason-code runs remain intentionally unrewritten.
- `git diff --check` passed with no output.
- Test-storage report remained dry-run only: `468` discovered artifacts and
  `83` eligible candidates were reported; no data was deleted or moved. The
  separate dry-run cleanup probe exceeded its 34-second tool limit while the
  workspace had concurrent Python activity, so no cleanup result is claimed.

## Durable-memory boundary

`docs/agent/memory/active-work.md` became concurrently modified by the Joint
workflow task during this task. It remains outside this disjoint checkpoint;
the pre-existing `docs/agent/memory/current-state.md` modification is also
untouched.

## Explicit changed-file allowlist

- `polynexus/gui/main_window_results_mixin.py`
- `tests/test_saxs_results_evidence_layout.py`
- `docs/agent/tasks/2026-07-28-saxs-results-evidence-layout.md`
- `docs/superpowers/specs/2026-07-28-saxs-results-evidence-layout-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-results-evidence-layout.md`

Do not include the pre-existing `docs/agent/memory/current-state.md` change,
the concurrently edited `docs/agent/memory/active-work.md`, native GUI
harness changes, generated captures, scratch directories, or `.superpowers/`.
