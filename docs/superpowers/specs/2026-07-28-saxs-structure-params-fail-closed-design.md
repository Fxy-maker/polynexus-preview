# SAXS structure-parameter fail-closed guard design

## Context

`compute_structure_params()` detects regular IDF peak spacing as an artifact
only inside the tangent-success branch. A later confidence calculation reads
`idf_is_artifact` for every branch. On short or limited-q profiles where the
tangent branch is not entered, the local is undefined and the whole
`analyze_single()` call raises `UnboundLocalError` instead of returning the
existing low-confidence/diagnostic result.

## Design

Initialize the existing artifact flag to `False` before the branch that may
populate it. Keep the current artifact detection scope and all existing
confidence calculations unchanged. This makes the no-artifact default explicit
and allows the existing downstream confidence logic to complete for profiles
without a usable tangent estimate.

The regression uses the smallest reproducible short-q profile through the
public `analyze_single()` entrypoint. It asserts that the frame returns a
structured result and quality/evidence payload rather than raising. No new
quality threshold or scientific interpretation is introduced.

## Non-goals

- No changes to q/I sanitization, smoothing, IDF, tangent, Bragg, Lorentz,
  Guinier, Porod, or invariant calculations.
- No new artifact heuristic, threshold, confidence value, rescue action, AI
  call, interpolation, or frame repair.
- No changes to publication roles, Workbench presentation, or export schema.

## Acceptance criteria

- A short/limited-q profile that previously raised from an uninitialized local
  returns through `analyze_single()`.
- Existing confidence and artifact behavior remain unchanged when the tangent
  branch is entered.
- The regression is RED before the one-line initialization and GREEN after it.
- Focused test, exact SAXS matrix, structured verifier, diff check, and an
  explicit allowlist checkpoint are recorded.

## Affected boundaries

- `polynexus/core/saxs_engine/core.py`
- focused SAXS regression test
- task/spec/plan and durable agent memory
