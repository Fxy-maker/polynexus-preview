# SAXS AI Replay Application Binding Design

## Goal

Keep the SAXS AI replay audit synchronized with the actual candidate
application outcome produced by the shared preprocessing transaction.

## Scope

The orchestrator already validates a SAXS intent, runs bounded candidates, and
evaluates their evidence through the existing quality and physical hard gates.
This change only fixes the final audit projection: replay rows are built after
the commit attempt, use the final decision payload, and mark application as
performed only after a successful commit.

## Non-goals

- No new SAXS metric, threshold, quality level, or physical gate.
- No model-provider call or automatic intent generation.
- No raw q/I, detector pixels, source paths, or candidate data in replay rows.
- No change to shadow, confirmation, or calibrated-auto policy semantics.

## Design

`build_preprocess_replay_audit()` accepts an optional `apply_performed` flag,
defaulting to `False` for backward compatibility. The SAXS orchestrator keeps
candidate trials and their evidence unchanged, performs the existing commit
transaction, then constructs replay rows from the final report decision. Only
the selected candidate receives `apply_performed=True`, and only when the
existing commit helper returns success. A failed commit updates the final
SAXS decision to `keep_original`; the replay row is then generated from that
decision and retains `apply_performed=False`.

## Acceptance criteria

1. A calibrated, hard-gated auto-accepted SAXS candidate has a replay row with
   `decision=auto_accept`, `apply_allowed=true`, and `apply_performed=true`.
2. A commit failure has a replay row with the final `keep_original` decision,
   `apply_allowed=false`, and `apply_performed=false`.
3. Shadow, confirmation, failed-trial, JSON-safety, and existing physical
   gate behavior remain unchanged.

## Verification

- Focused RED/GREEN tests in `tests/test_saxs_ai_orchestrator_handoff.py`.
- Replay contract tests in `tests/test_preprocess_replay_contract.py`.
- SAXS matrix, structured task verifier, diff check, and storage report/clean
  dry-run.
