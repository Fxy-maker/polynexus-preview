---
kind: acceptance
status: in_progress
date: 2026-07-31
title: Joint real-data current-HEAD recheck
task: docs/agent/tasks/2026-07-31-joint-real-data-current-head-recheck.md
---

# Acceptance record

## Scope

The existing Joint real-data test runs real DSC, SAXS, and WAXS source engines,
persists their outputs through SampleDB, builds a Joint report, and publishes
the Figure Manifest/Gallery context.

## Evidence rule

Only a complete pytest summary and exit code `0` count as a pass. A fixture skip
or missing summary remains incomplete evidence.

## Scientific boundary

This contract proves data transport and provenance. It does not assign
scientific conflict precedence, resolve disagreement between techniques, or
authorize a Joint publication conclusion. Unresolved conflicts remain
diagnostic-only.

## Verification commands

```powershell
python -m pytest -p no:cacheprovider -q tests/test_joint_real_data_lifecycle.py -vv --basetemp=C:\PolyNexus-test-runs\joint-real-data-current-head-20260731
python scripts/verify.py --task docs/agent/tasks/2026-07-31-joint-real-data-current-head-recheck.md --changed --types
python scripts/boundary_audit.py --root D:\PolyNexus --json
git diff --check
```

Observed result: `1 passed in 15.55s`, exit code `0`. The automated contract
confirms source-run transport and run-linked publication context only; it does
not close Joint scientific conflict review or final release authorization.
