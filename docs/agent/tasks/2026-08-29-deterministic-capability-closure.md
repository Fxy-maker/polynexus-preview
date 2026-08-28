---
task_id: 2026-08-29-deterministic-capability-closure
kind: architecture
status: active
date: 2026-08-29
title: Close deterministic result contracts without sample replay
---

# Deterministic capability and result-contract closure

## Goal

Expose deterministic outputs uniformly and preserve method sensitivity and
condition-scoped group statistics without rerunning the six-sample dataset.

## Non-goals

- No six-sample replay or raw-data changes.
- No automatic grouping, literature interpretation, RAG, material database, or
  manuscript promotion.

## Acceptance criteria

- [x] Every `ComputeResult` leaf has a JSON-safe metric manifest with value/type,
  optional unit/method/parameters/source, warnings, and status; JSON and flat
  CSV projections are available.
- [x] Group statistics include count, mean, std, CV, minimum, maximum, trend,
  repeatability, and source row IDs without mixing condition values; GUI detail
  rows expose the extrema.
- [x] A shared method-sensitivity DTO preserves primary and candidate results
  with an explicit difference range and unavailable status.
- [x] A technique-neutral capability catalog lists the requested deterministic
  outputs and their shared `result.metric_manifest` projection; catalog entries
  do not claim execution or publication eligibility.
- [ ] All provider-specific deterministic capabilities are registered and
  consumed through the shared capability executor.
- [x] GUI, CLI, and evidence package expose the complete metric-manifest
  projection for persisted ComputeRun results; provider-specific capability
  registration remains open.
- [ ] Task verification and focused regression coverage pass.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-29-deterministic-capability-closure.md --changed --types
git diff --check
```
