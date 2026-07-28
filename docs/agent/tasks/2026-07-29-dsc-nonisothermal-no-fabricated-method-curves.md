---
task_id: 2026-07-29-dsc-nonisothermal-no-fabricated-method-curves
kind: scientific-publication
status: completed
---

# DSC non-isothermal method curves must use authoritative points

## Goal

Prevent the DSC non-isothermal publication provider from fabricating a method
curve when completed kinetics metadata has no authoritative x/y coordinates.

## Non-goals

- Do not change DSC kinetics, fit thresholds, rates, or the
  `NonIsothermalResult` schema.
- Do not infer x/y coordinates from rates, a scalar parameter, or another
  method.
- Do not change conversion-series publication roles or shared rendering,
  Manifest, Gallery, Editor, export, or history contracts.

## Affected boundaries

- `polynexus/core/dsc_engine/figure_nonisothermal.py`: provider-only gate and
  diagnostic metadata.
- `tests/test_dsc_publication_nonisothermal_provider.py` and
  `tests/eval/test_dsc_publication_real_data.py`: explicit-point and
  no-point regressions.
- This task card, its design/plan, and durable agent memory.

## Acceptance criteria

- [x] A qualified method with rates and parameters but no finite aligned x/y
  points produces no plot objects and is diagnostic-only.
- [x] The diagnostic recipe records `missing_method_plot_data`, the reported
  method parameters, fit quality, and zero plot points.
- [x] A qualified method with explicit finite x/y points remains Main with its
  existing plot objects and role ordering.
- [x] Existing conversion Main, SI, and diagnostics behavior is unchanged.
- [x] Focused RED/GREEN, DSC provider/lifecycle/eval tests, task verifier, and
  diff checks pass; one explicit allowlist checkpoint is created.

## Implementation plan

1. Add a RED regression for a qualified rates-only method and update the ready
   fixture to carry explicit authoritative x/y points.
2. Make `_method_gate()` reject missing method points with the existing
   evidence-gated diagnostic path and remove the constant-y fallback from
   `_method_definition()`.
3. Preserve method parameters and point count in recipe metadata, then verify
   the focused DSC/provider/eval matrix and structured repository gates.

## Verification

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-07-29-dsc-nonisothermal-no-fabricated-method-curves.md
python -m pytest tests/test_dsc_publication_nonisothermal_provider.py -q
python -m pytest tests/test_dsc_publication_cutover.py tests/test_dsc_lifecycle_closure.py tests/eval/test_dsc_publication_real_data.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-29-dsc-nonisothermal-no-fabricated-method-curves.md --changed --types
git diff --check
```

## Verification evidence

- RED: `1 failed`; rates-only qualified Kissinger was incorrectly promoted to
  Main and carried a constant fabricated curve.
- GREEN: selected regression plus explicit-point Main path `2 passed`.
- DSC provider/lifecycle/eval matrix: `13 passed in 20.02s`.
- Complete DSC test matrix plus real publication evaluation: `70 passed in
  29.89s`.
- Task card validation, Ruff, compile, and `git diff --check` passed.
- Structured verifier exited `0`: quality `283 passed`, preprocessing `106
  passed`, Ruff, compile, type baseline, memory/task, and whitespace checks
  passed.

## Checkpoint

The allowlisted checkpoint is created after the structured verifier passes;
no analysis algorithm, shared GUI, or unrelated memory/scratch file is part of
this task.

## Changed-file allowlist

- `polynexus/core/dsc_engine/figure_nonisothermal.py`
- `tests/test_dsc_publication_nonisothermal_provider.py`
- `tests/eval/test_dsc_publication_real_data.py`
- `docs/agent/tasks/2026-07-29-dsc-nonisothermal-no-fabricated-method-curves.md`
- `docs/superpowers/specs/2026-07-29-dsc-nonisothermal-no-fabricated-method-curves-design.md`
- `docs/superpowers/plans/2026-07-29-dsc-nonisothermal-no-fabricated-method-curves.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`

## Known limitations

This closes a provider-level provenance defect. It does not establish that
the underlying DSC method data are scientifically valid, nor does it close
the restarted-GUI, real-instrument, or human DSC publication review gates.
