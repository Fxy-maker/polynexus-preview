# SAXS AI Confirmed-Rerun Safety Design

## Goal

Close the safety gap between a user confirming a SAXS preprocessing candidate
and the post-confirmation analysis result. A confirmed rerun must be a single,
auditable transaction whose result is accepted only when the existing SAXS
physical indicators and quality gates remain valid. Failure must restore the
original configuration and result without storing a positive experience.

## Scope

This slice covers the existing candidate-confirmation path for SAXS static,
temperature, and strain modes:

- a mode-aware transaction boundary around the existing GUI confirmation
  service;
- before/after configuration hashes, candidate identity, and application
  status in a JSON-safe audit record;
- post-rerun evidence capture through existing SAXS quality/physical evidence
  contracts;
- fail-closed rollback when the rerun fails, evidence is unavailable, the
  candidate/config identity changes, or an existing gate rejects the result;
- read-only propagation of the audit record into the existing preprocessing
  and SAXS export provenance paths.

The existing `run_preprocess_intent` candidate trial remains the source of the
candidate and its pre-confirmation evidence. The confirmed rerun reuses the
same candidate identity and does not silently generate a new candidate.

## Non-goals

- No new SAXS numerical algorithm, q-window, physical threshold, or quality
  threshold.
- No interpolation, frame fabrication, missing-frame repair, or automatic
  rescue.
- No external model call, automatic acceptance, tiered-auto promotion, or
  calibration shortcut.
- No change to publication roles, Figure selection, Manifest/Gallery policy,
  or editor behavior.
- No replacement of the authoritative `quality_evidence.json` contract.
- No technique-specific branching in GUI event handlers; GUI remains a thin
  adapter over services and result DTOs.

## Current gap

`PreprocessTransactionService` already snapshots selected configuration and
the previous result, applies a confirmed configuration, invokes one rerun, and
restores state when the callback raises. It does not yet record the SAXS mode,
candidate identity, before/after hashes, post-rerun physical/quality evidence,
or the reason for a gate-based rollback. The current GUI callback also treats
any successful `_run_analysis` completion as sufficient to finalize the
transaction. That is weaker than the SAXS contract because a successful
engine run can still produce diagnostic or unusable evidence.

## Design

### 1. Shared transaction with a SAXS evidence adapter

Keep transaction mechanics in
`polynexus/gui/preprocess_transaction_service.py` and keep scientific
acceptance in a core/service boundary. The transaction receives a structured
rerun result from the existing analysis lifecycle rather than inspecting
SAXS engine internals in a widget callback.

The transaction audit is a detached, strict-JSON record with these semantic
fields:

- `technique`: `SAXS`;
- `mode`: exactly `static`, `temperature`, or `strain`;
- `candidate_id` and the candidate's original/base configuration hash;
- `before_config_hash` and `after_config_hash` for the transaction's captured
  configuration scope;
- `phase`: `apply_pending`, `applied`, `rolled_back`, `failed`, or `undone`;
- `apply_performed`: true only after the confirmed rerun passes all gates;
- `physical_gate_status` and `quality_gate_status`, copied from existing
  evidence decisions rather than recomputed with new thresholds;
- detached before/after quality-evidence references or compact projections;
- `rollback_reason`, when the transaction is not accepted;
- `accepted_by` and an audit timestamp.

Non-finite values become JSON `null`. Raw curves, detector arrays, and full
result objects are never stored in this audit record.

The service must reject a confirmation before applying anything when the
report is malformed, the decision is not `request_confirmation`, the selected
candidate ID is absent/mismatched, the candidate base hash does not match the
current captured configuration, the mode is unsupported, or another
transaction is pending. A confirmation transaction invokes the rerun callback
at most once.

### 2. Existing SAXS evidence remains the acceptance authority

The core/service adapter consumes the result DTO/evidence produced by the
normal SAXS lifecycle after the rerun. It does not invent a second quality
system. Acceptance requires all of the following existing signals to be
available and passing:

1. the rerun completed successfully and returned a result;
2. existing candidate hard guards are all true;
3. the mode-specific SAXS quality evidence is not missing or `Unusable`;
4. existing physical validation/quality status is not a failure.

For static mode, the projection retains frame-level and existing 1D metric
evidence. For temperature mode, it retains frame evidence plus the existing
series trend/diagnostic evidence and original `source_index` mapping; trend
evidence never upgrades a frame. For strain mode, generic 1D metric evidence
and detector/orientation evidence remain separate. Missing frames stay
missing.

The transaction does not require a new numeric cutoff. If a required existing
evidence section cannot be obtained, the status is `unavailable` and the
transaction rolls back rather than guessing.

### 3. Apply, post-gate, and rollback sequence

The state machine is:

```text
idle
  -> apply_pending (capture before state and validate identity)
  -> rerun once
  -> post_gate
      -> applied (persist experience, apply_performed=true)
      -> rolled_back (restore config/result, apply_performed=false)
  -> undo_pending -> undone / applied
```

The original config and result are retained until post-gate acceptance. A
failed engine callback, missing evidence, changed hash, failed physical gate,
failed quality gate, or exception while restoring state produces an explicit
rollback reason. Positive experience persistence happens only after `applied`;
its failure is recorded without claiming that experience was stored. Existing
undo behavior remains reversible and receives the same audit treatment.

### 4. Provenance propagation

The audit is added as read-only provenance to the existing preprocessing/SAXS
report and export evidence. `quality_evidence.json` remains authoritative;
Figure/Manifest records may reference the audit but do not duplicate raw
quality data or change publication roles. Shadow, keep-original, and rejected
candidate paths continue to show `apply_performed=false` and never enter the
confirmed transaction state.

## Error handling and downgrade policy

- Invalid or incomplete confirmation: no mutation, `apply_performed=false`.
- Config identity mismatch: no rerun, preserve the current original state.
- Rerun exception or unsuccessful result: restore the original state.
- Missing/diagnostic-only/unusable post-rerun evidence: restore the original
  state; do not promote trend evidence or infer a frame.
- Existing physical/quality gate failure: restore the original state and retain
  both the failed candidate evidence and the original evidence for review.
- Restore failure: retain an explicit `restore_failed` audit reason and surface
  the failure through the existing error diagnostics; never claim acceptance.

## Verification and acceptance criteria

- [ ] A pure audit/validation contract serializes strictly and maps non-finite
  values to `null`.
- [ ] A confirmed static transaction applies exactly once and is accepted only
  after existing quality and physical gates pass.
- [ ] Temperature and strain transactions preserve their existing mode-specific
  evidence boundaries, including source indices and independent orientation
  evidence.
- [ ] Hash mismatch, candidate mismatch, missing evidence, gate failure, and
  rerun exception all restore the original config/result and leave
  `apply_performed=false`.
- [ ] Experience persistence occurs only after post-gate success; undo revokes
  it only after a successful undo rerun.
- [ ] Shadow, keep-original, and rejected paths remain non-applying.
- [ ] Workbench/quality export provenance preserves the audit without changing
  figure roles or authoritative evidence ownership.
- [ ] Focused transaction/SAXS mode matrix, task-scoped verifier, strict JSON,
  compile, whitespace, and `git diff --check` pass.

## Affected boundaries

- `polynexus/gui/preprocess_transaction_service.py`
- `polynexus/gui/main_window_ai_tuning_mixin.py`
- `polynexus/gui/main_window_run_mixin.py` only for typed rerun-result handoff
- `polynexus/core/saxs_engine/saxs_ai_rescue.py` or a focused adjacent core
  service for SAXS audit validation
- existing replay/export provenance boundary only where a read-only field is
  required
- focused transaction, SAXS AI, mode, and export tests
- task card, implementation plan, and durable memory

## Review boundary

This is a scientific-semantics and cross-layer change. Human review is still
required before merge for the definition of “existing physical/quality gate”
and for restarted-GUI confirmation behavior. Automated tests cannot replace
that review.
