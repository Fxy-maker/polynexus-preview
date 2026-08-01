# SAXS AI Existing Gate Enforcement Design

## Goal

Ensure every SAXS AI preprocessing candidate is rejected unless the existing
SAXS physical and quality assessment accepts the candidate trial result.

## Contract

`assess_saxs_confirmed_rerun()` remains the sole authority for the existing
SAXS physical and quality gates. The AI preprocessing path may rank candidates
with the shared generic evidence contract, but it cannot return `request_confirmation`
or `auto_accept` when the existing SAXS assessment is failed or unavailable.

The candidate trial must therefore satisfy both:

- the existing generic preprocessing hard guards; and
- `physical_gate_status == "passed"` and `quality_gate_status == "passed"`
  from the existing SAXS assessment for its actual static, temperature, or
  strain mode.

Missing frames, missing quality evidence, `Diagnostic`/`Unusable` evidence, or
an existing physical-gate failure remain `keep_original` outcomes. Their
existing reason codes are preserved and the decision exposes explicit
`saxs_existing_quality_gate` and `saxs_existing_physical_gate` hard-guard keys.

## Architecture

The guard is applied in `orchestrator_preprocess._execute_preprocess_candidate`
after the candidate engine has completed and the generic adapter has built its
evidence. A small SAXS-only adapter at this boundary calls the existing
assessment, copies a detached compact assessment into `PreprocessEvidence`'s
`technique_specific` payload, and replaces the decision with a low-confidence
`keep_original` result when either existing gate is not passed.

The confirmed transaction service remains unchanged. It already validates and
rechecks confirmed reruns through the same assessment. No new threshold,
physical calculation, model call, interpolation, frame repair, or publication
promotion is introduced.

## Failure Handling

- A trial exception or missing output continues to use the existing failed
  evidence path.
- A completed trial with missing/weak SAXS evidence is retained for audit but
  cannot be selected for application.
- The original engine/configuration remains untouched when the SAXS gate fails.
- Replay and decision payloads remain strict-JSON and retain the existing
  candidate-only/original-preserved semantics.

## Verification

The regression will cover static, temperature, and strain mode labels, a
generic-metric-positive but SAXS-quality-negative candidate, a passing
candidate, and strict-JSON audit output. The focused AI orchestration suite,
complete SAXS matrix, task-scoped structured verifier, storage dry-run, and
explicit allowlist checkpoint are required.

## Scope Boundary

This task does not decide whether a scientist should approve a real detector,
temperature, or strain interpretation. Those existing human review gates stay
open.
