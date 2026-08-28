# Six-sample v011 result-completeness acceptance

Date: 2026-08-29

## Scope

The six real samples (PA6, PA6-50, PA11, PA11-50, PA12, PA12-50) were replayed
through the shared project workflow using copied raw inputs. The source tree
and the earlier v007 replay were not modified.

## Evidence

- Replay root: `D:\PolyNexus-six-sample-replay-20260829-v011`
- Package: `D:\PolyNexus-six-sample-replay-20260829-v011\.polynexus\evidence\pa6-six-sample-v011-v001`
- Audit: `D:\PolyNexus-six-sample-replay-20260829-v011\replay-audit-v011-final.json`
- 42/42 runs are `review_required`; no run-level `failed`, `blocked`, or
  unexplained reason code remains.
- 270 copied raw files have SHA-256 equality with the v007 raw tree.
- Package contains 270 evidence items, 558 indexed figures, 3,640 assets,
  `result-tables.json`, and `review-decision.json`.

## Result-completeness decisions

- Null metric aliases are `needs_input`, never falsely `completed`.
- Existing finite SAXS Porod/Kratky/Guinier and WAXS peak/decomposition,
  Williamson–Hall fields are exposed through the shared provider projection.
- No numerical algorithm, quality threshold, material inference, or scientific
  publication decision was changed.

## Verification

```powershell
pytest -q tests/test_capability_execution.py tests/test_saxs_batch_parameters.py tests/test_waxs_temperature.py
python scripts/verify.py --task docs/agent/tasks/2026-08-29-six-sample-result-completeness.md --changed --types
```
