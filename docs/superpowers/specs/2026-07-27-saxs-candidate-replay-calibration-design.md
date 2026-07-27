# SAXS candidate replay and calibration audit design

Date: 2026-07-27
Status: design checkpoint; implementation is not yet enabled

## Goal

Close the remaining SAXS AI rescue gap by making every bounded candidate
replay auditable across static, temperature, and strain modes, while keeping
the original result authoritative until the existing SAXS physical and quality
gates permit a separately authorized action.

## Non-goals

- Do not change Guinier, Porod, Kratky, invariant, lamellar, 2D, orientation,
  sequence, or publication thresholds.
- Do not let an LLM invent numeric preprocessing values or bypass the SAXS
  protected-feature validator.
- Do not enable tiered-auto, call an external provider during tests, or make a
  scientific publication claim.
- Do not modify raw data, real regression fixtures, generated repository
  outputs, or user-owned configuration.

## Current evidence and gap

`LLMClient` and `rag.Advisor` already provide a provider boundary. The SAXS
bridge validates the seven protected features and the shared orchestrator
already creates bounded trial engines. The missing evidence is a stable,
mode-aware record for each trial and a calibration case format that can prove
or block future automation. Existing `PreprocessEvidence`,
`SAXSAIRescueDecision`, `AnalysisEvidence`, and SAXS quality contracts remain
authoritative.

## Design

### 1. Candidate replay audit

For each generated SAXS candidate, the orchestrator will retain a JSON-safe
replay row with:

- `candidate_id`, `generation_reason`, `mode`, and source run/sequence context;
- original and effective configuration hashes;
- `run_status`, bounded timeout/error information, and whether a trial engine
  was created;
- the existing `PreprocessEvidence` and its hard-guard results;
- the existing SAXS physical/quality evidence references, including available
  frame or sequence coverage;
- `decision`, `simulated_decision`, `apply_allowed`, and explicit
  `original_preserved` / `apply_performed` flags.

The row records what happened; it does not create a second scoring system. A
missing frame, invalid condition, unavailable 2D metadata, or failed physical
metric remains missing/failed rather than being synthesized.

### 2. Mode boundary

The same replay contract is used by `saxs.static`, `saxs.temperature`, and
`saxs.strain`. Mode-specific evidence is read through the existing engine
result/evidence contracts. A temperature or strain candidate may be ranked
only when the relevant sequence/mode evidence is available; otherwise the
shared decision remains `keep_original` with an explicit reason code.

### 3. Decision and application rules

- `shadow` always preserves the original and reports `keep_original`, even if
  the simulated decision is `auto_accept`.
- `confirm_only` reports `request_confirmation`; a later user transaction must
  re-check the original configuration hash and rerun the selected candidate
  before applying it.
- `tiered_auto` remains rejected unless the existing calibration loader
  accepts a matching, hashed, promotion-allowed report and every hard guard
  passes. This design does not turn it on.
- `apply_performed` is false in replay audit rows. Any later application is a
  separate transaction audit and must never be inferred from candidate ranking.

### 4. Calibration cases

Calibration consumes a versioned manifest of case rows. Each row contains the
technique/mode, source identity, original/effective config hashes, evidence
coverage, metric drifts, hard-guard violations, candidate selection, and an
expert label with a reason. It must support synthetic cases and external real
case references without copying raw data into the repository.

The existing calibration report remains the only promotion artifact. Promotion
is blocked when there are no cases, insufficient evidence coverage, insufficient
expert agreement, hard-guard false accepts, or any version/hash mismatch.

## Data flow

```text
LLM response
  -> Advisor normalization
  -> SAXS protected-feature validator
  -> bounded candidates
  -> mode-aware trial engines
  -> existing SAXS/PreprocessEvidence
  -> shared hard guards and decision
  -> replay audit row (candidate-only)
  -> report/export provenance
```

## Testing strategy

1. Contract tests prove every replay row is JSON-safe, hash-consistent, and
   explicit about original preservation/application.
2. Fake-engine tests prove static, temperature, and strain trial success and
   failure paths do not mutate the control engine.
3. Protected-field and malformed-provider tests prove invalid SAXS intents fail
   before trial creation.
4. Calibration tests prove missing cases, low coverage, false accepts,
   disagreement, report hash mismatch, and version mismatch block promotion.
5. External real-data replay uses an external temporary output root and checks
   only audit/provenance; it cannot mark scientific trends as accepted.

## Acceptance boundary

This design is complete only when replay provenance and calibration blockers are
automated and verified. Human GUI review and expert scientific labels remain
required before any release or tiered-auto claim.
