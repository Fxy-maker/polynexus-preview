# Task: SAXS structure-parameter fail-closed guard

**Status:** complete; explicit local allowlist checkpoint created

## Goal

Make SAXS structure-parameter analysis degrade through its existing result and
quality contracts when a limited-q profile has no usable tangent branch,
instead of raising because an artifact flag was not initialized.

## Root-cause evidence

`compute_structure_params()` assigns `idf_is_artifact = False` only inside
`if np.isfinite(tangent_thickness) and tangent_thickness > 0.3`. The same local
is read later while building confidence, including when tangent, IDF, and
gamma-minimum estimates are unavailable. A reproducible 24-point profile over
`q=0.02..0.6` reaches that path and raises `UnboundLocalError` at the
post-estimate artifact penalty.

## Design decision

Initialize the existing local artifact flag before the tangent decision and
leave its current detection block and downstream calculations unchanged. The
default means “no artifact detected by the existing heuristic”; it is not a
new scientific conclusion or acceptance gate.

## Non-goals

- No numerical method, threshold, quality level, physical gate, rescue, AI, or
  publication-role change.
- No new artifact heuristic or data repair.
- No unrelated cleanup of the SAXS core or parallel GUI/editor/release files.

## Acceptance criteria

- [x] The minimal short-q public regression fails with the observed
  `UnboundLocalError` before the fix.
- [x] The same regression returns a structured result and quality/evidence
  payload after the fix.
- [x] Exact SAXS matrix and task-scoped verifier pass.
- [x] One explicit allowlist checkpoint is created after fresh verification.

## Affected boundaries

- `polynexus/core/saxs_engine/core.py`
- `tests/test_saxs_structure_params_fail_closed.py`

## Implementation plan

1. Add the minimal public short-q regression and verify the expected
   `UnboundLocalError` before changing production code.
2. Initialize the existing `idf_is_artifact` local before the tangent branch,
   preserving the current peak-spacing heuristic and confidence calculations.
3. Run the focused regression/adjacent quality tests and the complete SAXS
   matrix.
4. Run the structured verifier and diff check, update durable evidence, and
   create one explicit allowlist checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_structure_fail_closed_focus'
python -m pytest -q tests/test_saxs_structure_params_fail_closed.py
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_structure_fail_closed_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-structure-params-fail-closed.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/core.py`
- `tests/test_saxs_structure_params_fail_closed.py`
- `docs/agent/tasks/2026-07-28-saxs-structure-params-fail-closed.md`
- `docs/superpowers/specs/2026-07-28-saxs-structure-params-fail-closed-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-structure-params-fail-closed.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`

## Verification record

- TDD RED: `1 failed`; traceback confirmed the uninitialized
  `idf_is_artifact` read in `compute_structure_params()`.
- Focused GREEN: `21 passed`.
- Exact SAXS matrix: `412 passed, 6 warnings`.
- External-D task verifier exited `0`: task/memory checks, Ruff, compile, type
  baseline, quality gate `283 passed`, preprocessing gate `106 passed`, and
  whitespace/diff checks all passed. The six existing warnings are the known
  Arial glyph and EDF geometry fallback warnings; no new warning category was
  introduced. Explicit allowlist checkpoint created locally; no push, merge,
  release, or scientific publication approval is implied.
