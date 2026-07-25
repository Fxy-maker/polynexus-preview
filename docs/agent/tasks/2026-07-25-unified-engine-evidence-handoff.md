---
task_id: 2026-07-25-unified-engine-evidence-handoff
kind: cross-module
status: completed
---

# Unified engine evidence handoff

## Goal

Ensure ordinary DSC, WAXS, and IR engine analysis paths attach the shared
`AnalysisEvidence` payload to `AnalysisResult`, so Workbench, History, export,
and preprocessing consumers receive the same evidence boundary as SAXS/NMR.

## Non-goals

- Do not change scientific calculations, thresholds, or publication roles.
- Do not overwrite richer technique-specific evidence already attached by
  SAXS, NMR, or an explicit IR mapping handoff.
- Do not infer IR mapping vendor semantics or add new GUI branches.

## Affected boundaries

- `polynexus/core/analysis_evidence_handoff.py`: shared evidence assembly.
- `polynexus/core/dsc.py`, `polynexus/core/waxs.py`, `polynexus/core/ir.py`:
  direct analysis handoff points.
- `tests/test_engine_evidence_lifecycle.py`: focused engine regressions.
- `docs/agent/memory/` and `docs/acceptance/`: durable evidence and state.

## Acceptance criteria

- [x] DSC direct analysis attaches evidence with `technique == "DSC"`.
- [x] WAXS direct analysis attaches evidence with `technique == "WAXS"`.
- [x] IR static and temperature paths use the shared evidence builder.
- [x] The shared helper fills evidence only when a richer payload is not
  already present.
- [x] Focused engine/evidence regression and existing five-technique matrices
  pass.

## Implementation

- Added a shared core helper that combines the representative typed result with
  scalar engine-level parameters and validation context.
- Wired DSC, WAXS, and IR direct analysis paths to the helper.
- Added `tests/test_engine_evidence_lifecycle.py` with one regression per
  affected engine.

## Implementation plan

1. Add direct-analysis regressions for DSC, WAXS, and IR and verify they fail
   while `AnalysisResult.analysis_evidence` is empty.
2. Add a shared core evidence helper that uses typed result parameters and
   validation context without changing scientific calculations.
3. Wire the helper into the affected direct analysis paths, then rerun the
   focused matrix.
4. Run the structured verifier, inspect the cumulative diff, and create one
   allowlisted checkpoint commit.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_engine_evidence_focus'
python -m pytest tests/test_engine_evidence_lifecycle.py tests/test_dsc_engine.py tests/test_waxs_temperature.py tests/test_ir_engine.py tests/test_nmr_engine.py tests/test_saxs_result_contract.py -q
```

Result: `44 passed in 86.49s`.

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-25-unified-engine-evidence-handoff.md --changed --types
```

Result: selected checks passed; quality gate `282 passed`, preprocessing gate
`103 passed`, changed-file Ruff and compile checks passed.

Real-data, restarted-GUI, AI-off/failure/fallback, and scientific release
review remain part of the full-software goal.
