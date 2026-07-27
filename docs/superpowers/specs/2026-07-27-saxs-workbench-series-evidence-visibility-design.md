# SAXS Workbench Series Evidence Visibility Design

Date: 2026-07-27
Status: approved working design

## Goal

Make the existing temperature and strain series-level `metric_evidence`
visible in the Results Workbench review path. A user must be able to tell
which metrics are fully covered, which are only trend-level, and which are
downgraded because frames are missing, diagnostic, or unusable.

## Scope

The change has two parts:

1. The SAXS engine's temperature/strain parameter payloads will carry the
   already-computed series `metric_evidence` summaries. The payload is only a
   persistence/view transport; it does not recalculate evidence.
2. The SAXS results presentation will derive a compact, localized review
   summary from those summaries. The summary is placed in the existing
   `risk_text`/`next_text` presentation channels, while the existing
   Diagnostics table continues to expose the complete nested evidence JSON.

History restore will work through the existing persisted `parameters` payload.
Figure routing and publication roles remain unchanged; figure links continue
to select manifest-backed figures and Export remains the authoritative full
provenance path.

## Evidence display contract

For each metric summary, display only existing contract fields:

- metric name;
- series level (`Quantitative`, `Trend`, `Diagnostic`, or `Unusable`);
- evidence coverage (`evidence_frame_count/frame_count` and percentage when
  available);
- counts for diagnostic and unusable frames when non-zero;
- missing-frame count when non-zero;
- the first few deterministic reason codes when a downgrade exists.

No method-specific physical cutoff, new threshold, imputation, interpolation,
or publication decision is introduced. A complete multi-frame summary remains
Trend-capped. A summary with missing, diagnostic, unusable, or invalid-level
frames is presented as downgraded evidence, not as a failed analysis.

The review summary is advisory display text only. It cannot authorize AI
candidate execution, publication, or tiered-auto behavior.

## Data flow

```text
TempSeriesResult.metric_evidence / StrainSeriesResult.metric_evidence
        -> SAXS.get_parameters() transport payload
        -> persisted run parameters / History restore
        -> build_saxs_results_presentation()
        -> existing ResultsTableModel risk/next channels
        -> Results Workbench review summary
        -> Diagnostics table keeps full nested evidence
```

The existing `saxs_export_bundle._quality_evidence_payload()` remains
unchanged and continues to read the series object directly. Figure definitions
remain unchanged because they do not interpret quality levels.

## Failure and downgrade behavior

- No `metric_evidence` key: preserve current presentation with no new text.
- Malformed/non-mapping summary: ignore it for display and keep the nested
  payload visible in Diagnostics through the existing serializer.
- Missing or invalid level: display the contract's existing level value and
  reason codes; do not repair it in the GUI.
- Mixed frame quality: show the series level and counts, never a binary
  "good/bad" promotion.

## Testing and acceptance

- Engine payload tests prove temperature and strain parameters include the
  exact existing series summaries without changing frame rows or numeric
  values.
- Presentation tests prove complete Trend summaries and downgraded mixed
  summaries produce deterministic English and Chinese review text.
- Results-table model tests prove the text reaches the existing Workbench
  model and nested evidence remains in Diagnostics.
- History persistence/restore tests prove the summary survives through the
  existing parameters payload.
- Focused SAXS/Workbench tests, `git diff --check`, and the repository's
  changed-file verifier are run. The known pre-existing GUI Ruff blocker is
  reported separately and remains out of scope.

## Non-goals

- no changes to Guinier/Porod/Kratky/invariant/lamellar algorithms;
- no new quality thresholds or scientific semantics;
- no changes to figure publication roles, manifest IDs, or export schema;
- no GUI cleanup unrelated to the evidence visibility path;
- no AI model call, candidate rerun, or automatic rescue authorization.
