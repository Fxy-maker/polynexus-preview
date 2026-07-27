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

- [ ] Temperature `metric_evidence` includes a `guinier` summary with the
  existing coverage/level/count/reason contract.
- [ ] Missing or failed temperature frames remain missing at their original
  positions; no neighboring evidence is copied.
- [ ] Existing sequence evidence, frame fields, DataFrame values, and strain
  behavior remain unchanged.
- [ ] Parameter transport, Workbench review, History persistence, and Export
  quality provenance retain both common Guinier and detailed sequence evidence.
- [ ] Focused tests observe RED before implementation and GREEN afterward.
- [ ] `python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-temperature-guinier-metric-evidence.md --changed --types`
  and `git diff --check` pass.
- [ ] `scripts/auto_commit.py` creates one atomic checkpoint using the explicit
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
