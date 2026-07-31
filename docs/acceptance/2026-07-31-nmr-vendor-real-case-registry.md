---
kind: acceptance
status: recorded
date: 2026-07-31
title: NMR vendor real-case registry
task: docs/agent/tasks/2026-07-31-nmr-vendor-real-case-registry.md
---

# Acceptance record

## Scope

This task registers four existing NMR inputs as real-engine evaluation cases:
liquid H, liquid C, solid H, and solid C. The source files remain read-only.

## Scientific boundary

The cases use `source: vendor_unreviewed` and empty `ground_truth`. They prove
input resolution, real-engine dispatch, output provenance, and safe external
output placement only. They do not provide peak assignments, ppm calibration,
Xc truth, reviewer scores, or publication approval. Solid-C remains
assignment-limited and Xc remains gated.

## Verification record

To be filled only from complete command summaries and exit codes:

```powershell
python -m pytest -q tests/eval/test_nmr_vendor_real_case_registry.py tests/eval/test_runner_real_nmr.py -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-31-nmr-vendor-real-case-registry.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

No storage `--apply` is part of this task.

## Observed results

- RED before implementation: `6 failed` because the four registry descriptors
  did not exist.
- Registry real-engine test: `6 passed in 116.32s`, exit `0`.
- Registry plus existing bridge regression: `7 passed in 118.12s`, exit `0`.
- Each input ran through the actual NMR engine with output redirected to a
  pytest-owned external directory. The four descriptors load with
  `vendor_unreviewed`, empty ground truth, and valid normalized real-engine
  submodule IDs.
- Solid-C remains `assignment_limited`; no Xc or assignment truth was added.

## Structured verification

- Task verifier exited `0`; quality `297 passed`, preprocessing `106 passed`,
  task/memory, Ruff, compile, type baseline, and whitespace checks passed.
- Storage report and dry-run clean each exited `0`: `62` artifacts,
  `eligible_bytes=0`, `10` emergency candidates, `0` removable bytes, and
  `removed=0`. No `--apply` was run.
- `git diff --check` exited `0`.
- The checkpoint allowlist excludes all real NMR files, memory edits, parallel
  SAXS changes, and scratch directories.

## Workspace boundary

Only the explicit task allowlist may be checkpointed. Real NMR files,
pre-existing memory edits, parallel SAXS changes, and scratch directories stay
outside the checkpoint.
