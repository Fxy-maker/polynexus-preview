# SAXS AI Rescue Evidence Visibility Design

## Goal

Expose the already-produced SAXS AI rescue plan, decision, replay audit, and
confirmed-rerun audit through the public engine-parameter payload and the
Results Workbench as detached, read-only evidence.

## Scope

This slice joins two existing boundaries:

1. `SAXSEngine.get_parameters()` copies the four existing audit fields from the
   engine/result state into the public parameters payload for static,
   temperature, strain, and aligned-batch results.
2. `saxs_results_table_service` emits a compact review summary from those
   public mappings. The summary is advisory and says whether a candidate,
   confirmation request, replay, or confirmed-rerun audit is present; it does
   not apply candidates or infer scientific validity.

The existing Export `quality_evidence.json` path remains authoritative for the
full audit. Parameters and Workbench receive detached copies/formatting only.

## Non-goals

- No model call, candidate generation, deterministic rerun, or transaction.
- No interpolation, missing-frame fabrication, or automatic rescue.
- No new physical indicator, quality threshold, or publication-role decision.
- No change to History persistence or Export schema beyond their existing
  consumption of the public/engine state.
- `apply_allowed` is displayed as a decision field only; it is never rendered
  as accepted, applied, or physically valid.

## Data contract

When an existing value is present, the public payload may contain the same
mapping/list under these keys:

- `saxs_ai_rescue_plan`
- `saxs_ai_rescue_decision`
- `saxs_ai_rescue_replay`
- `saxs_confirmed_rerun_audit`

Values are deep-copied. Missing values stay absent. Empty replay/audit values
are not converted into a positive rescue claim. Workbench formatting accepts
only mappings and list items with the expected scalar identifiers and ignores
malformed entries.

## Workbench behavior

The review text reports candidate count/identifiers, decision name, replay
status, and confirmed-rerun phase/gate statuses when available. It includes a
next action to review existing SAXS physical and quality gates and to perform
deterministic validation before any action. It never says that a candidate was
accepted, applied, or physically valid merely because `apply_allowed` is true
or a plan exists.

## Verification boundary

Tests cover detached transport for temperature and static/series states,
consumer formatting, malformed/empty fail-closed behavior, and preservation of
the source mappings. Existing Export tests continue to verify the complete
audit path separately.
