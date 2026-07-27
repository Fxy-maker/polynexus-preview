# Task: SAXS Workbench review evidence readability

**Status:** checkpointed locally in `6fe3128`

## Goal

Make the existing SAXS Workbench risk and next-step evidence auditable at a
glance by separating each independent review source into an ordered line,
without changing any evidence, algorithm, gate, or persistence contract.

## Evidence and root cause

The real native SAXS Results capture shows multiple independent `Risk note` and
`Next step` messages rendered as one long paragraph. The source is
`build_saxs_results_presentation()` in
`polynexus/gui/saxs_results_table_service.py`, where already-formatted sections
are joined with a space. The evidence content itself is correct; only the
presentation separator is inadequate for review.

## Design decision

Keep `ResultsTablePresentation.risk_text` and `.next_text` as strings for
compatibility with existing Workbench, History, and GUI consumers. Join the
non-empty sections with `\n` in their existing deterministic order. Preserve
every section's text and reason code; do not truncate, deduplicate, reorder, or
invent labels. Existing QLabel word wrapping will render one review source per
line.

## Non-goals

- No SAXS core, quality level, physical indicator, threshold, rescue, AI, or
  publication-role changes.
- No new DTO, persistence schema, Figure/Manifest/Export contract, or GUI
  algorithm branch.
- No changes to Chinese/English wording beyond the line separator.
- No modifications to the parallel native GUI harness or release documents.

## Acceptance criteria

- [x] Risk sections remain in current source order and are separated by a
  newline.
- [x] Next-step sections remain in current source order and are separated by a
  newline.
- [x] Empty sections are omitted without leading/trailing blank lines.
- [x] Existing evidence text and reason codes remain byte-for-byte unchanged
  within each section; input payloads are not mutated.
- [x] Focused RED/GREEN, Workbench consumer matrix, SAXS matrix, task verifier,
  and diff check are recorded; the explicit allowlist checkpoint is the final
  handoff action.

## Affected boundaries

- `polynexus/gui/saxs_engine` presentation consumer:
  `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_workbench_review_readability.py`
- This task's spec/plan and durable memory.

## Implementation plan

1. Add a failing presentation regression that asserts ordered newline-separated
   risk and next-step sections plus payload immutability.
2. Replace only the two final space joins with newline joins over the existing
   section tuples.
3. Run focused Workbench consumers, the complete SAXS matrix, task verifier,
   and diff checks; record exact results and create one explicit checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_workbench_review_red'
python -m pytest -q tests/test_saxs_workbench_review_readability.py

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_workbench_review_focus'
python -m pytest -q tests/test_saxs_workbench_review_readability.py tests/test_saxs_workbench_series_evidence.py tests/test_saxs_results_table_service.py tests/test_saxs_workbench_figure_contracts.py tests/test_results_workbench_profiles.py

$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_workbench_review_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-workbench-review-readability.md --changed --types
git diff --check
```

## Evidence before checkpoint

- RED: `1 failed`; the expected failure showed two risk sources joined into one
  line by the old space separator.
- Focused Workbench consumer matrix: `104 passed`.
- Exact SAXS matrix: `419 passed, 6 warnings` in 37.27s. Warnings are the
  existing Arial glyph and missing-geometry warnings.
- Post-change full/boundary verification passed: `2851 passed, 17 skipped,
  12 warnings` in 1567.25s. Quality `283`, preprocessing `106`, compile,
  whitespace, and boundary audit all passed.
- Structured verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-workbench-review-readability.md --changed --types`
  passed with quality gate `283`, preprocessing gate `106`, Ruff, compile,
  memory/task checks, and whitespace checks. The changed-file Ruff/compile
  list also contained the pre-existing native GUI harness modification; it was
  not included in this task's checkpoint.

## Explicit changed-file allowlist

- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_workbench_review_readability.py`
- `docs/agent/tasks/2026-07-28-saxs-workbench-review-readability.md`
- `docs/superpowers/specs/2026-07-28-saxs-workbench-review-readability-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-workbench-review-readability.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`
