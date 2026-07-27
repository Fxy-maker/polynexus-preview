# Task: SAXS deterministic 1D profile sanitization

**Status:** complete; explicit local allowlist checkpoint created

## Goal

Make the existing SAXS 1D analysis entrypoint robust to recoverable q/I defects
without changing scientific thresholds, inventing observations, or hiding the
raw input. The analysis methods must receive a deterministic finite, positive
profile, while the quality report records exactly what was removed or reordered.

## Finding

`analyze_single()` currently sends the caller-owned q/I arrays directly to
smoothing and the 1D methods, then builds `DataQualityReport` afterward. The
report identifies non-finite, non-positive, non-monotonic, and duplicate points,
but its `actions` field does not describe a canonical analysis profile. This
means some recoverable dirty inputs are only diagnosed after methods have
already seen them.

## Design decision

- Convert q and I to detached one-dimensional float arrays.
- Pair only the existing aligned prefix when lengths differ; never pad either
  axis.
- Drop pairs with non-finite or non-positive q/I before analysis.
- Stable-sort the surviving pairs by q.
- Preserve exact duplicate q observations in stable order; do not average,
  interpolate, or otherwise synthesize intensity values because no measurement
  error model is available in this task.
- Keep caller-owned arrays unchanged and expose the original/analysis counts
  and action codes through `DataQualityReport`.
- If fewer than the existing minimum usable points remain, keep the existing
  `Unusable` level and fail closed through the existing method evidence gates.

## Non-goals

- No new point-count, q-range, qRg, R², physical, or publication threshold.
- No duplicate-q aggregation, interpolation, extrapolation, neighbor copying,
  frame fabrication, or missing-frame repair.
- No changes to temperature sequence semantics, AI rescue acceptance, Figure
  roles, or detector geometry interpretation.
- No mutation of raw input arrays or generated regression datasets.

## Acceptance criteria

- [x] A pure sanitizer returns detached aligned q/I arrays and deterministic
      action codes for malformed input.
- [x] Non-finite and non-positive pairs are excluded from the analysis copy,
      while duplicate q points remain in stable order.
- [x] `analyze_single()` uses the sanitized copy for all existing methods and
      retains the legacy result shape for clean inputs.
- [x] `DataQualityReport.actions` records only actions actually taken, and the
      original/usable counts remain consistent with the raw input.
- [x] Caller-owned arrays remain unchanged, strict JSON remains valid, and
      missing/insufficient data stays fail-closed.
- [x] Focused RED/GREEN tests, the exact SAXS matrix, task verifier, and diff
      check are recorded.
- [x] Explicit allowlist checkpoint is created after the final boundary rerun.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/core.py`
- `tests/test_saxs_dirty_profile_sanitization.py`
- this task card, its design/spec/plan, and durable SAXS memory

## Implementation plan

1. Add RED tests for detached sanitization, invalid-pair removal, stable q
   ordering, duplicate retention, action ordering, and analysis-boundary use.
2. Implement the pure `Sanitized1DProfile` helper and pass its action codes to
   the existing `DataQualityReport` without changing level rules.
3. Wire `analyze_single()` to use the sanitized analysis copy while retaining
   caller-owned input arrays and legacy clean-input behavior.
4. Run the focused tests, exact SAXS matrix, task verifier, and diff check.
5. Record actual evidence and create one explicit allowlist checkpoint; leave
   parallel GUI/editor/release files untouched.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_dirty_profile_focus'
python -m pytest -q tests/test_saxs_dirty_profile_sanitization.py tests/test_saxs_quality_contracts.py tests/test_saxs_guinier_evidence.py
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=C:\Temp\PolyNexus_saxs_dirty_profile_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-deterministic-1d-profile-sanitization.md --changed --types
git diff --check
```

## Verification record

- TDD RED: `4 failed, 11 passed`; failures were the missing sanitizer,
  missing action de-duplication, and the dirty-input Lorentz NaN failure.
- TDD GREEN: focused sanitizer/quality/Guinier suite `20 passed`.
- Exact SAXS matrix: `406 passed, 6 warnings` in `26.83s` using the external
  basetemp above.
- Task-scoped verifier: exit `0`; task card and memory checks, Ruff, compile,
  type baseline, quality gate `283 passed`, preprocessing gate `106 passed`,
  and whitespace checks all passed.
- Fresh full/boundary with `PYTEST_ADDOPTS` basetemp on D: exited `0`:
  `2838 passed, 16 skipped, 12 warnings` in `1579.21s`; boundary audit passed.
  Quality gate was `283 passed`, preprocessing gate `106 passed`, and Ruff,
  compile, type baseline, and whitespace checks passed.
- An earlier C:-based full attempt is classified separately as an environment
  failure (`No space left on device`) and is not used as evidence for this
  task; the D:-isolated run is authoritative.
- Explicit allowlist checkpoint created locally; no push.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/core.py`
- `tests/test_saxs_quality_contracts.py`
- `tests/test_saxs_dirty_profile_sanitization.py`
- `docs/agent/tasks/2026-07-28-saxs-deterministic-1d-profile-sanitization.md`
- `docs/superpowers/specs/2026-07-28-saxs-deterministic-1d-profile-sanitization-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-deterministic-1d-profile-sanitization.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`

Parallel GUI/editor drafts, release documents, scratch directories, and
pre-existing untracked files are outside this allowlist.
