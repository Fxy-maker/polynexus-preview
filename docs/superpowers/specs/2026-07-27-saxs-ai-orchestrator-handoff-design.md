# SAXS AI orchestrator handoff design

## Problem

The SAXS AI rescue bridge already validates protected features and wraps the
shared decision outcome, but the general preprocessing orchestrator does not
invoke that SAXS-specific boundary. A valid-looking generic intent can
therefore enter the shared adapter without the stronger SAXS protection
contract, and the bridge fields are not automatically available to the engine
export audit.

## Design

At the start of `_run_preprocess_intent`, SAXS uses a public validator from
`saxs_ai_rescue.py`; all other techniques retain the existing generic parser.
The orchestrator still generates and executes candidates through the existing
adapter and transaction code. Once candidates have been generated, the
orchestrator constructs the existing `SAXSAIRescuePlan` around those exact
candidates rather than generating a second set.

After the shared evidence is scored, SAXS wraps the same
`DecisionOutcome` inputs with `assess_saxs_ai_candidate`. The wrapped JSON is
used for the report decision and is also stored as a separate
`saxs_ai_rescue_decision` audit field. The plan and decision are attached to
the source engine as plain dictionaries, which lets the existing export
bundle include them without coupling export to orchestration internals.

## Safety

The bridge remains candidate-only. Shadow keeps the original. Confirm-only
only requests confirmation. Tiered-auto remains controlled by the existing
calibration and hard guards. No code path applies a SAXS candidate merely
because a plan or decision field exists.

Invalid SAXS intents fail closed through the existing `_invalid_report` path;
no trial engine is created and no audit field claims a valid rescue plan.
