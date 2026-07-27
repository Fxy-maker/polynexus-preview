# SAXS temperature Guinier metric evidence

## Goal

Expose existing temperature frame-level Guinier evidence through the common
series metric contract, completing the first vertical quality route without
changing physical analysis semantics.

## Non-goals

- No new Guinier fitting or threshold changes.
- No frame repair, interpolation, or sorting.
- No strain Rg sequence, AI execution, or publication changes.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`: derive the common
  per-frame Guinier metric mapping and series summary.
- `tests/test_saxs_temperature_guinier_evidence.py` and focused transport,
  Workbench, and Export tests: regression coverage.
- Existing `saxs.py`, Workbench, History, and Export contracts are expected to
  consume the added common summary without new presentation logic.
- This task card, its design/spec, implementation plan, and SAXS memory.

## Acceptance criteria

- [x] Temperature `metric_evidence` includes a `guinier` summary with the
  existing coverage/level/count/reason contract.
- [x] Missing or failed temperature frames remain missing at their original
  positions; no neighboring evidence is copied.
- [x] Existing sequence evidence, frame fields, DataFrame values, and strain
  behavior remain unchanged.
- [x] Parameter transport, Workbench review, History persistence, and Export
  quality provenance retain both common Guinier and detailed sequence evidence.
- [x] Focused tests observe RED before implementation and GREEN afterward.
- [x] `python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-temperature-guinier-metric-evidence.md --changed --types`
  and `git diff --check` pass.
- [x] `scripts/auto_commit.py` creates one atomic checkpoint using the explicit
  changed-file allowlist.

## Verification commands

```powershell
python -m pytest tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_mode_evidence_propagation.py tests/test_saxs_workbench_series_evidence.py tests/test_saxs_export_bundle.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-temperature-guinier-metric-evidence.md --changed --types
git diff --check
```

## Known limitations

Real-data scientific sign-off, expert calibration, candidate reruns, AI model
calls, and publication authorization remain outside this atomic task.

## Implementation plan

1. Add failing temperature and mode-propagation assertions for complete and
   failed-frame Guinier metric summaries.
2. Derive a read-only `guinier` frame mapping from existing nested evidence and
   aggregate it with the existing series metric builder.
3. Verify parameter, Workbench, History, Export, and figure-role propagation.
4. Run the task verifier and SAXS regression matrix, then record exact results
   and create one checkpoint with the explicit allowlist.

## Verification

```powershell
python -m pytest tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_mode_evidence_propagation.py tests/test_saxs_workbench_series_evidence.py tests/test_saxs_export_bundle.py tests/test_saxs_workbench_figure_contracts.py tests/test_results_workbench_profiles.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-temperature-guinier-metric-evidence.md --changed --types
git diff --check
```

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_temperature_guinier_evidence.py`
- `tests/test_saxs_mode_evidence_propagation.py`
- `tests/test_saxs_workbench_series_evidence.py`
- `tests/test_saxs_export_bundle.py`
- `docs/agent/tasks/2026-07-27-saxs-temperature-guinier-metric-evidence.md`
- `docs/superpowers/specs/2026-07-27-saxs-temperature-guinier-metric-evidence-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-temperature-guinier-metric-evidence.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`

## Verification result

- TDD RED was observed: the new summary assertions initially failed with a
  missing `metric_evidence["guinier"]` entry.
- Temperature/mode evidence matrix: `6 passed`.
- Workbench/Export/Figure consumer matrix: `22 passed` using an isolated
  basetemp because the repository's pre-existing `.pytest_tmp` is locked.
- Full SAXS matrix: `283 passed, 4 existing font glyph warnings` using an
  isolated basetemp.
- Task verifier: passed with task validation, memory validation, changed-file
  Ruff, compile, type baseline, quality gate `282`, preprocessing gate `106`,
  whitespace, and selected-check status. The configured default `.pytest_tmp`
  remains locked by pre-existing workspace state, so the verifier was run with
  an explicit isolated basetemp; no existing temp data was deleted.
- `git diff --check`: passed.
- Atomic checkpoint: `3324b2e`, created with `scripts/auto_commit.py`; no push,
  merge, deployment, or unrelated workspace cleanup was performed.
