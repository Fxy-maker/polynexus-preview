---
title: Current-head full and boundary recheck after test-storage rule update
date: 2026-07-30
status: approved
---

# Current-head Full/Boundary Recheck

## Decision

Run the repository's authoritative full verifier against the current checkout
after the test-storage rule update and the fresh SAXS matrix. Accept the
automated result only when the verifier returns exit code `0`, pytest prints a
complete summary, and the boundary audit completes successfully.

## Scope

This is a verification-only task. It records current-checkout evidence and
does not change production behavior, scientific thresholds, quality levels,
rescue policy, AI behavior, publication roles, or test-storage contents.

## Safety boundaries

- Existing parallel NMR, Joint, GUI, scratch, and untracked test-output files
  remain outside the task allowlist.
- `scripts/test_storage.py report --json` and `clean --older-than-hours 24
  --json` are read-only inventory/planning commands; no `--apply` is run.
- A timeout, crash, setup error, disk error, or process exit without a pytest
  summary is incomplete evidence, never a pass.
- Automated verification does not grant restarted-GUI, detector-geometry,
  instrument-calibration, scientific-meaning, or release approval.

## Acceptance

- The current checkout is inspected after all prior pytest processes exit.
- Full verification records complete pytest, quality, preprocessing, boundary,
  and wrapper exit results when available.
- The storage report and dry-run are recorded without deletion.
- Task verification and diff hygiene pass for the documentation allowlist.
- A documentation-only checkpoint contains only this task's files and durable
  audit records.
