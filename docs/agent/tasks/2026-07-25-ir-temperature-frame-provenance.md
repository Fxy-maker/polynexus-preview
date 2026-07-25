# IR temperature-2D frame provenance

## Goal

Keep each IR temperature-2D figure traceable to the frame temperature, stage,
time, label, and ordering source without changing the plotted sequence-frame
axis or scientific interpretation.

## Non-goals

- Do not infer temperatures, stages, or band meaning when the input is missing.
- Do not change IR mapping reader semantics or publication roles.

## Affected boundaries

- `polynexus/core/ir_engine/figure_provider.py`
- `tests/test_ir_complete_figure_provider.py`
- IR temperature-2D manifest data-source and recipe payloads.

## Acceptance criteria

- [x] Heatmap and band-series sources carry temperature/time columns when
  available, with numeric NaN for missing values rather than fabricated values.
- [x] Recipe payloads preserve label, stage, estimated-time, and order-source
  metadata as JSON-safe values.
- [x] Existing one-frame, manifest publication, and role regressions pass.
- [x] Structured verifier and atomic checkpoint pass.

## Implementation plan

1. Add a failing provider regression for condition metadata.
2. Add run-safe numeric source columns and JSON-safe frame metadata.
3. Verify the existing FigurePipeline renderer still accepts missing numeric
   values and the IR temperature matrix remains green.
4. Run task verifier and checkpoint with an explicit allowlist. (15 focused IR
   tests; verifier quality gate 282 and preprocessing gate 103 passed.)

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_ir_temperature_frame_verify'
python -m pytest tests/test_ir_complete_figure_provider.py tests/test_ir_temperature.py tests/test_ir_figure_provider.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-25-ir-temperature-frame-provenance.md --changed --types
```
