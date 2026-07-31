---
task_id: 2026-07-31-saxs-ai-summary-context
status: accepted-automated
date: 2026-07-31
---

# SAXS AI summary-only context acceptance

## Delivered boundary

The SAXS rescue bridge now exposes a deterministic `saxs-ai-summary-v1`
context envelope. It reuses existing quality/physical evidence projection and
status assessment, and explicitly marks `candidate_only=True`,
`physical_validation_required=True`, `raw_profile_included=False`, and
`raw_detector_data_included=False`. The prompt consumes this envelope only
when a caller supplies it; it does not change the no-context prompt.

No model invocation, candidate execution, configuration mutation, new
threshold, q/I repair, detector processing, quality-level change, physical-gate
change, rescue authorization, publication role, Figure, Manifest, or Export
behavior was added.

## Verification evidence

- RED collection: missing context helper, as expected.
- A second RED proved that prompt rendering needed to filter untrusted raw
  fields; the sanitizer regression and focused suite passed after the fix.
- Focused AI/prompt regression: `38 passed`, exit `0`.
- Exact SAXS matrix after the sanitizer: `678 passed, 6 warnings`, exit `0`.
- Structured task verifier: exit `0`; quality `297 passed`, preprocessing `106
  passed`, plus Ruff/compile/type/memory/task/whitespace checks.
- Storage report and clean were non-destructive dry-runs: `57` artifacts,
  `1,368,589,871` bytes total, `7,873` eligible bytes, `0` removed.
- `git diff --check`: exit `0`.

## Remaining gates

This task defines the model-input boundary but does not connect a model
provider. Future intent generation must still pass the existing SAXS intent
validator, bounded candidate generation, physical/quality decision gates, and
confirmation policy. Human scientific review and release authorization remain
open.

## Checkpoint

The explicit allowlist checkpoint is created locally with
`scripts/auto_commit.py`; no push or merge is performed.
