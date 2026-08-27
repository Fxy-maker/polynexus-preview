# Full-suite release boundary — 2026-08-28

## Fresh verification

The full boundary command completed with:

- **4197 passed**
- **39 failed**
- **25 skipped**

Core quality gates passed independently: **311 focused tests** and **157
preprocess tests**. The current task-focused matrices also passed:

- evidence gallery filters: **25 passed**
- package/evidence/AI handoff: **50 passed**
- GUI batch ComputeRun persistence: **20 passed**

## Failure classification

The 39 failures are not evidence that the new shared-template route failed.
They are concentrated in pre-existing surfaces:

- ChartGallery reflow and legacy figure output profiles;
- the historical IR orchestrator no-op path with ambiguous canonical mapping;
- GUI history/log wording and persistence fixtures;
- legacy manifest editor, Sample Browser, and result-table expectations;
- SAXS 2-D detector/strain/temperature dirty-data and advisory paths.

These remain a release-readiness backlog. No quality rule or scientific gate
was relaxed to reduce the count.

## Current boundary

The goal is implementation-complete for the shared project/ComputeRun/template
architecture and six-sample replay, but remains `review_required` for:

- human scientific approval of DSC/FTIR/SAXS/WAXS evidence;
- full legacy GUI/SAXS failure closure;
- final ARS manuscript use decisions.
