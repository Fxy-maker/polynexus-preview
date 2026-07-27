# SAXS empty-profile fail-closed design

## Context

The deterministic 1D sanitizer correctly returns an empty analysis profile for
empty or wholly invalid q/I input. `analyze_single()` still sends that empty
profile into the numerical pipeline; `lorentz_fit_long_period()` indexes
`q[-1]` and raises `IndexError`. An unanalysable frame should remain visible as
an existing `Unusable` quality result rather than aborting its caller.

## Design

At the analysis boundary, after sanitization and before smoothing or any
numerical method, detect `sanitized.q.size == 0`. Build the same existing
quality report contract from the original inputs and sanitizer actions, build
the existing empty `GuinierEvidence` contract, and return a structurally safe
`SAXSResult` containing read-only empty q/I/I_smooth arrays,
`LongPeriodResult()` and `StructureParams()` defaults, and an empty method
evidence mapping. This preserves the result shape needed by static,
temperature, and strain callers while keeping all numeric outputs unavailable.

The branch does not add a threshold or a new scientific decision: the existing
quality contract already classifies zero usable points as `Unusable`, and the
existing Guinier builder already produces the corresponding fail-closed reason
codes. Non-empty profiles continue through the unchanged numerical path.

## Non-goals

- No interpolation, padding, neighbor copy, frame fabrication, or rescue.
- No changes to any numerical method, threshold, physical gate, quality level,
  publication role, AI behavior, or consumer schema.
- No alteration of short-but-nonempty profile behavior.

## Acceptance criteria

- Empty q/I input returns a structured result instead of `IndexError`.
- The report is `Unusable`, records existing insufficient-point reasons, and
  keeps source/action provenance.
- Guinier evidence is strict-JSON-safe and `Unusable`.
- Static/temperature/strain callers can retain the returned frame as an
  unavailable result without inventing values.
- Focused RED/GREEN, exact SAXS matrix, structured verifier, diff check, and an
  explicit allowlist checkpoint are recorded.

## Verification evidence (2026-07-28)

- RED reproduced the existing `IndexError` at `lorentz_fit_long_period()` for
  empty q/I input; focused GREEN passed `17` tests.
- The exact `test_saxs_*.py` matrix passed `413` tests with `6` existing
  warnings. The structured task verifier passed with quality `283` and
  preprocessing `106`, including Ruff, compile, type baseline, memory/task,
  and whitespace checks; `git diff --check` passed.
- Full/boundary repository verification remains outside this scoped task.

## Affected boundaries

- `polynexus/core/saxs_engine/core.py`
- focused SAXS empty-profile regression test
- task/spec/plan and durable agent memory
