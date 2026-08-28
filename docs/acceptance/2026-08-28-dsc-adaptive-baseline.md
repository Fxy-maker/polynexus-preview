# Adaptive isothermal DSC baseline acceptance — 2026-08-28

Isothermal DSC now computes two explicit baseline variants for each event:
`endpoint_linear` and `tail_constant`. The endpoint-linear variant is selected
when both event-edge windows are usable; otherwise the result falls back to the
tail-constant variant and records `endpoint_baseline_unavailable`. Variant
results are retained for sensitivity review but are never averaged.

The selected method, edge values, slope, window indices, selection reason,
sensitivity flag, and variant scalars are exposed through `AvramiResult`, DSC
parameter rows, and the existing ComputeRun JSON projection.

The tail-constant variant preserves the established recorded-segment-tail
definition. Its provenance now records that actual tail window and its zero
slope (rather than borrowing the endpoint-linear window). A sensitivity result
also becomes the `baseline_sensitive` quality flag, so its writing metrics stay
`diagnostic_only` while its numerical result remains available for review. The
legacy `isothermal_kinetics` summary now reuses the same complete projection as
the shared segment rows.

When a candidate reaches the record boundary before it has a post-event window,
`endpoint_linear` is explicitly unavailable and the existing tail-constant
fallback is selected. This retains the calculation while preventing an
unclosed endpoint from being presented as a settled linear baseline.

PA6-DWJJ read-only replay with the shared `ComputeRunService` produced the
following endpoint-linear primary values:

| T (°C) | t₁/₂ (min) | n | R² |
|---:|---:|---:|---:|
| 180.1 | 1.835 | 2.827 | 0.9997 |
| 181.1 | 1.940–1.958 | 1.486–1.489 | 0.994–0.995 |
| 182.1 | 2.355 | 1.882 | 0.9987 |
| 183.1 | 2.858 | 2.183 | 0.9999 |
| 184.1 | 3.422 | 2.171 | 0.9994 |

These values agree with the historical endpoint-linear AI calculation within
the expected rounding and event-window differences. The 183 and 184 °C rows
are marked `baseline_sensitive`, so their tail-constant alternatives remain
visible for review. The 185 °C segment falls back to `tail_constant` because
no independent pre-event baseline window is available; it remains computable
and explicitly flagged.

Verification:

- DSC/canonical/ComputeRun/CLI/Batch/Agent/evidence/writing matrix: `120 passed, 3 skipped`.
- `python scripts/verify.py --task docs/agent/tasks/2026-08-28-adaptive-isothermal-baseline.md --changed --types` → passed.
- `git diff --check` → passed.
- Read-only six-sample `ComputeRun` smoke: all six `*-DWJJ.txt` files completed;
  every emitted segment row has the complete baseline projection.

Scientific promotion and paper-use decisions remain human/ARS review
boundaries.
