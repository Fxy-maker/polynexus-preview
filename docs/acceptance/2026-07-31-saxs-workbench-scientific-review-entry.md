# SAXS Workbench Scientific Review Entry Acceptance

Task: `docs/agent/tasks/2026-07-31-saxs-workbench-scientific-review-entry.md`

## Scope

The Results Workbench now lets a reviewer explicitly choose the existing SAXS
scientific-review scope, in ordered form: `saxs.1d`, then `saxs.2d`. The
choice only selects an existing review contract. It does not infer detector or
algorithm meaning, and saving continues through the existing validated dialog,
run-scoped SampleDB update, and source-linked promotion snapshot.

## Acceptance evidence

- TDD RED: importing the planned `review_scope_options_for_context` helper
  failed before its implementation existed.
- Focused GREEN on 2026-07-31:
  `python -m pytest -q tests/test_scientific_review.py
  tests/test_scientific_review_workbench.py -o addopts=` → `49 passed`.
- Fresh SAXS matrix:
  `653 passed, 6 warnings in 505.81s`, exit code `0`.
- Structured verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-workbench-scientific-review-entry.md --changed --types`
  → exit `0`; quality `297 passed`, preprocessing `106 passed`, plus
  task/memory, Ruff, compile, type baseline, and whitespace checks.
- `git diff --check` → exit `0`.
- Storage `report --json` and `clean --older-than-hours 24 --json` both
  returned exit `0` in dry-run mode. The latter reported `88` artifacts,
  `24,069,661,628` bytes total, `45` emergency-eligible artifacts,
  `22,700,847,442` eligible bytes, and `removed_count=0`. No storage
  `--apply` was run.

## Boundaries preserved

- SAXS 1D/2D is chosen by the reviewer; no mode, detector, geometry, mask,
  beam-center, orientation, or algorithm state is used to guess a scope.
- IR, NMR, and Joint retain their existing single-scope mappings; unknown
  techniques remain fail-closed.
- Missing run, cancelled chooser, rejected dialog, and invalid records do not
  persist a review.
- This does not modify SAXS calculation, quality level, physical gates,
  rescue, AI state, Figure, Manifest, Export, or publication role. In
  particular, an `accepted` review record remains evidence, not automatic
  scientific-release authorization.

## Pre-existing changes left outside this task

`docs/agent/memory/current-state.md`, `docs/agent/memory/active-work.md`,
`pytest.ini`, all scratch/test-storage directories, and unrelated parallel
GUI/NMR changes are excluded from this task's allowlist checkpoint.
