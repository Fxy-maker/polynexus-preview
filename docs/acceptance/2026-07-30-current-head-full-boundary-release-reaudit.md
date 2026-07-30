---
kind: acceptance
status: recorded
date: 2026-07-30
title: Current-head full and boundary release re-audit
task: docs/agent/tasks/2026-07-30-current-head-full-boundary-release-reaudit.md
---

# Acceptance Record

## Result

The current-head full/boundary release gate remains open. The authoritative
command was executed and its incomplete outcome was classified from actual
output; no pass is claimed.

## Evidence

- `python scripts/verify.py --changed --types --full --boundary` completed the
  memory, Ruff, compile, type baseline, quality (`290 passed`), and
  preprocessing (`106 passed`) phases.
- The all-tests phase reached progress output but did not produce a final
  pytest summary. It ended while pytest wrote its cache with
  `OSError: [Errno 28] No space left on device`; the wrapper exit code was
  `1`. Because the quality gate stopped before returning success,
  `boundary_audit` did not execute.
- C:-isolated task verification avoided the disk-space failure for its first
  phases, but quality collection stopped with
  `ImportError: cannot import name 'SampleDB'` from the current parallel
  `polynexus/data/sample_db.py`; that quality gate returned `2`. No file in
  that parallel change was modified by this task.
- D: space audit reported `Free=0`; read-only storage report reported `81`
  artifacts, `17270956962` total bytes, `eligible_bytes=0`, and `removed=0`.
  No apply or deletion was performed.

## Remaining Gates

The next release attempt requires external state changes: recoverable D: test
storage management or another approved volume, plus reconciliation of the
parallel `SampleDB` import failure. After that, rerun the full command and
require a complete pytest summary, successful quality/preprocessing phases,
and a completed boundary audit. Restarted-GUI visual review, real-detector
calibration/mask meaning, reviewer-owned scientific interpretation, and final
publication approval remain separate human gates.
