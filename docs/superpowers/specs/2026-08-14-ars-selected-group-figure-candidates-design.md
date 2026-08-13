# ARS-Selected Group Figure Candidates Design

## Purpose

ARS decides which candidate experiment groups answer the manuscript question
before PolyNexus computes or publishes figures. PolyNexus then creates a small
set of manuscript figure candidates for only those groups, while preserving
all source-level outputs as internal evidence.

The first vertical slice targets same-technique FTIR temperature/time groups.
It establishes reusable contracts without changing scientific analysis or
claiming that filename-derived groups establish sample identity.

## Request Contract

The project workflow accepts an explicit figure-selection request containing:

```json
{
  "question": "Compare PA6 JW and SW temperature evolution",
  "selected_groups": [
    "ir:pa6-jw:temperature_C",
    "ir:pa6-sw:temperature_C"
  ],
  "figure_intent": "compare_groups",
  "main_figure_limit": 2
}
```

- `selected_groups` must be non-empty, unique candidate group IDs returned by
  the same project inventory.
- `figure_intent` is one of `describe_group`, `compare_groups`, or
  `show_trend`.
- `main_figure_limit` defaults to `2` and may only be `1` or `2` in V1.
- The request is invalid if a group is absent, if selected groups use different
  techniques or incompatible condition kinds, or if the selected count does
  not match the requested intent.
- Explicit `--paths` remains the lower-level escape hatch. It does not create
  a manuscript figure selection by itself.

## Figure Candidate Contract

Every candidate figure records a stable ID, group IDs, technique, role,
condition axis, source runs, source artifacts, output paths, status, and
limitations. Its role is one of:

- `main_candidate`: eligible for ARS to consider in a manuscript figure set;
- `supporting_candidate`: eligible for supplementary material or review;
- `internal_evidence`: single-file, diagnostic, or quality output retained for
  traceability but not offered as a main-figure candidate.

For a selected FTIR group, V1 attempts these candidates in priority order:

1. `group_overlay`: one aligned spectral overlay, with group condition values
   shown in the legend;
2. `metric_trend`: one trend figure only when a common finite quantitative
   metric exists for every selected condition and the condition axis is valid;
3. `single_file`: existing per-file provider figures, marked
   `internal_evidence`.

For `compare_groups`, the first candidate is a shared overlay or comparison
figure only when both groups have comparable condition axes and compatible
spectral representation. Otherwise each selected group may receive one
group-overlay candidate, subject to the total limit. Trend candidates are
suppressed rather than fabricated when a common metric is unavailable or
review-bound conditions make comparison unsafe.

## Output and Evidence

PolyNexus writes only beneath `.polynexus`:

```text
.polynexus/
  figures/<selection-id>/
    main/
    supporting/
    internal/
    manifest.json
  evidence/<package-version>/
    figure-candidates.json
```

`manifest.json` is the source of truth for the generated files. The evidence
package copies only eligible output assets and records `figure-candidates.json`
alongside existing evidence, limitations, and writing input. ARS receives:

- at most two `main_candidate` figures;
- the condition axis and group membership behind each figure;
- source provenance and limitations;
- explicit omission reasons for unavailable overlays/trends.

ARS selects the final manuscript figures and writes the figure narrative.
PolyNexus does not decide publication inclusion and does not add scientific
interpretation beyond provider evidence.

## Failure Boundaries

- Unknown, stale, or mixed-technique group IDs block the request before any
  provider run.
- Unreliable filename-derived grouping remains labelled
  `inferred_from_filename`.
- Fewer than two usable files suppresses a group overlay.
- No common finite metric, duplicate or missing condition values, or a
  technique-specific validation limit suppresses a trend figure with a reason
  code; the underlying single-file evidence remains available.
- Generated candidate figures retain `review_required` whenever their source
  run or provider evidence is review-bound.
- No raw data, project notes, or manuscript files are modified.

## Acceptance Criteria

- ARS can submit one or two returned group IDs and a figure intent.
- Only selected group artifacts are analyzed.
- The result exposes no more than two main-figure candidates.
- A selected FTIR series produces a group overlay when at least two usable
  spectra are available.
- A trend appears only with a common finite metric and valid condition axis.
- Existing single-file outputs remain traceable but are absent from the default
  main-candidate list.
- Candidate metadata reaches the evidence package without changing raw inputs.
