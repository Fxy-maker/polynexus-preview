# ARS-Selected Group Figure Candidates Acceptance

Date: 2026-08-14

The AI-native project workflow now accepts an explicit ARS figure-selection
request. ARS selects returned candidate group IDs before analysis; PolyNexus
runs only those sources and returns a bounded set of manuscript figure
candidates. The first implemented route is same-technique FTIR group plotting.

## Request and Selection

`FigureSelectionRequest` accepts a manuscript question, one or two inventory
candidate group IDs, a figure intent, and a main-candidate limit of one or two.
It blocks duplicate/unknown IDs, invalid intents or limits, intent/count
mismatches, mixed techniques, and incompatible condition kinds before provider
execution. The two-group `compare_groups` contract is currently fail-closed
before provider execution with `group_comparison_not_implemented`; no false
comparison figure is emitted in this FTIR-only vertical slice.

`project-workflow analyze-project` accepts the JSON request through
`--figure-selection <path>`. The JSON result reports `selected_groups` and
`figure_candidates` while preserving the existing candidate-group result fields
for callers that do not submit a selection.

## FTIR Candidate Output

- The renderer uses only selected artifact paths and writes beneath
  `.polynexus/figures/<selection-id>/`.
- A group with at least two usable spectra yields a normalized, linear-baseline
  FTIR overlay as PNG and SVG. It uses the existing IR reader/preprocessing
  pipeline and preserves the conventional descending wavenumber axis.
- The optional trend is restricted to one finite provider-reported `Xc_pct`
  with the same explicit method for every selected condition. Missing,
  non-finite, or mixed-method metrics, duplicate conditions, or an exhausted
  figure limit suppress the trend and record an omission reason.
- Provider single-file figures are not promoted into the main candidate list.
- All generated candidates are `review_required`; no scientific conclusion or
  sample/batch identity is inferred from the filename-derived group.

## Evidence Package

The immutable evidence package now carries `figure-candidates.json`, copies
only main/supporting candidate assets, records candidate metadata in the
package manifest, and adds a manuscript-candidate section to `writing-input.md`.
Internal-only evidence stays in project-local provenance rather than becoming a
default manuscript asset.

## Read-Only PA6 Smoke

External source files remained behind the existing read-only junction:

`D:\PolyNexus-pa6-v4-ai-entry-20260812\raw`

The renderer read exactly:

- `PA6-JW-100.csv`
- `PA6-JW-110.csv`
- `PA6-JW-120.csv`

It created an overlay PNG/SVG and manifest beneath:

`D:\PolyNexus-pa6-v4-ai-entry-20260812\.polynexus\figures\real-pa6-jw-overlay-smoke`

Visual inspection confirmed a nonblank three-curve overlay, descending
wavenumber axis, and 100/110/120 C legend. No provider metric was supplied to
this read-only rendering smoke, so the trend was correctly omitted as
`metric_trend_metric_unavailable`. No external raw data was modified.

## Verification

- Focused ARS group candidate tests: `11 passed`.
- Project workflow regression matrix: `57 passed`.
- Ruff and `git diff --check`: passed before structured verification.
- Structured verifier: required before checkpoint.
