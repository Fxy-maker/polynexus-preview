# SAXS strain dirty-frame post-processing

## Goal

Make recoverable dirty q/I observations usable by strain-series 1D
post-processing without changing physical algorithms or losing raw-frame
quality provenance.

## Non-goals

- No new physical or point-count thresholds.
- No interpolation, duplicate-q aggregation, frame copying, fabricated frames,
  AI calls, rescue decisions, or publication-role changes.
- No changes to 2D sector/Herman calculations, strain ordering, or source-index
  mapping.
- No change to `analyze_single()`'s public result contract.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_strain_dirty_frame_postprocessing.py`
- Durable task/spec/plan and SAXS agent memory.

## Acceptance criteria

- [x] Reference and per-frame strain invariants consume only the existing
      sanitized surviving q/I observations.
- [x] Strain phase and void post-processing receive the same sanitized profile.
- [x] Original q/I arrays still reach `analyze_single()` and retain the raw
      `DataQualityReport` actions/counts.
- [x] Empty sanitized frames remain unavailable/fail-closed with no fabricated
      Q* or void metric.
- [x] Clean profiles preserve existing strain/source alignment and outputs.
- [x] Focused RED/GREEN, exact SAXS, task-scoped verifier, and diff evidence are
      recorded, with a fresh full/boundary result reported accurately.
- [x] One explicit allowlist checkpoint is created without touching parallel
      GUI/Joint/editor/scratch files.

## Implementation plan

1. Write a RED regression with NaN, non-positive, and unsorted q/I that asserts
   all strain 1D post-processing doubles see finite positive sorted survivors,
   while a fake `analyze_single()` records the original arrays and quality
   actions.
2. Add one `sanitize_1d_profile()` auxiliary profile per frame after the
   existing length validation; route only the four named post-processors
   through it.
3. Add empty-profile and clean/source-alignment assertions without changing
   the 2D sector/Herman path.
4. Run focused, exact SAXS, task-scoped, and fresh full/boundary verification;
   update durable memory with actual results and checkpoint only the allowlist.

## Verification

```powershell
python -m pytest tests/test_saxs_strain_dirty_frame_postprocessing.py tests/test_saxs_strain_evidence_filtering.py tests/test_saxs_1d_method_evidence.py -q
$saxsTests = Get-ChildItem tests -File | Where-Object { $_.Name -like 'test_saxs*.py' } | ForEach-Object { $_.FullName }
python -m pytest $saxsTests -q
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-strain-dirty-frame-postprocessing.md --changed --types
git diff --check
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-strain-dirty-frame-postprocessing.md --changed --types --full --boundary
```

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_strain_dirty_frame_postprocessing.py`
- `docs/agent/tasks/2026-07-28-saxs-strain-dirty-frame-postprocessing.md`
- `docs/superpowers/specs/2026-07-28-saxs-strain-dirty-frame-postprocessing-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-strain-dirty-frame-postprocessing.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`

## Known limitations

This slice makes strain 1D post-processing consume the same deterministic
survivor profile as single-frame analysis. It does not establish raw detector
geometry quality, orientation uncertainty, or scientific publication
authorization; those remain separate gates.

## Verification result

- TDD RED: `1 failed, 2 warnings`; the failure showed raw NaN q reaching the
  reference invariant helper.
- TDD GREEN: `3 passed, 1 warning`; strain/method cross-matrix: `9 passed, 1
  warning`.
- Exact SAXS matrix: `428 passed, 8 warnings` in `29.83s`.
- Task-scoped verifier exited `0`: quality `283`, preprocessing `106`, Ruff,
  compile, type baseline, memory/task, and whitespace checks passed.
- Fresh full/boundary verification: `2869 passed, 17 skipped, 12 warnings` in
  `1686.81s`, exit code `0`; boundary audit passed. This run included the
  current strain production/test changes.
