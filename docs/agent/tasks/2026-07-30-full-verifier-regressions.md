---
task_id: 2026-07-30-full-verifier-regressions
kind: regression-repair
status: completed
---

# Current full-verifier regression repair

## Goal

Repair the current-HEAD full-suite regressions exposed after the scientific
review visibility/provenance and SAXS figure-lifecycle checkpoints, without
changing scientific policy or removing diagnostic failure entries.

## Root causes

- IR figure recipes now preserve an empty `policy_version` in every review
  snapshot; one older test expected the pre-provenance shape.
- Results Workbench intentionally displays `Scientific review: Not applicable`
  for non-gated SAXS runs; two older MainWindow assertions omitted that suffix.
- Real SAXS strain publication keeps an error-status diagnostic figure visible;
  the lifecycle test selected it for editor persistence even though only ready
  figures can be edited.
- `tests/_tmp_phase3/test_visual_audit_capture.py` is a pre-existing untracked
  scratch test with an obsolete output-root assumption and is outside this
  repair allowlist.

## Non-goals

- Do not change scientific formulas, thresholds, reviewer values, or
  publication roles.
- Do not hide or delete error-status diagnostic Manifest entries.
- Do not modify `current-state.md`, real datasets, test-storage directories,
  or the pre-existing visual scratch test.

## Affected boundaries

- Scientific review snapshot serialization test contract.
- Results Workbench scientific-review presentation assertions.
- Shared Figure Manifest ready/error lifecycle selection in the real-run
  regression.
- Task verifier, quality/preprocessing gates, and the full pytest collection.

## Implementation plan

1. Reproduce each current-HEAD failure independently and classify its root
   cause as scratch/environment, stale expectation, or product lifecycle bug.
2. Apply the smallest test or lifecycle-selection correction for each
   confirmed root cause without changing scientific behavior.
3. Run focused regressions, the task verifier, and a full suite that excludes
   only the pre-existing untracked scratch test.
4. Record exact summaries, limitations, and the explicit allowlist before
   checkpointing.

## Acceptance criteria

- [x] The IR provenance assertion includes the current JSON-safe policy field.
- [x] Both SAXS Results Workbench assertions match the current visible review
  suffix while retaining their existing risk-summary checks.
- [x] The real lifecycle selects only a ready figure for Editor persistence and
  still leaves error entries visible in the manifest/gallery evidence.
- [x] Focused regressions pass; the task verifier passes, and the full-suite
  pytest summary is recorded with its wrapper-exit-code limitation.

## Verification

```powershell
python -m pytest -q tests/test_ir_mapping.py tests/test_main_window_persistence.py
python -m pytest -q tests/test_real_published_run_walkthrough.py -k saxs.strain
python scripts/verify.py --task docs/agent/tasks/2026-07-30-full-verifier-regressions.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `tests/test_ir_mapping.py`
- `tests/test_main_window_persistence.py`
- `tests/test_real_published_run_walkthrough.py`
- `docs/agent/tasks/2026-07-30-full-verifier-regressions.md`
- `docs/acceptance/2026-07-30-full-verifier-regressions.md`
- `docs/agent/memory/active-work.md`

## Pre-existing workspace changes

Keep `docs/agent/memory/current-state.md`, all untracked test/storage/scratch
directories, and unrelated GUI or parallel-agent changes outside this task.
