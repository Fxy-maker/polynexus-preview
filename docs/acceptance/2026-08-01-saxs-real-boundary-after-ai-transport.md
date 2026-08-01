---
kind: acceptance
status: recorded
date: 2026-08-01
title: Current-head real SAXS boundary after AI context transport
task: docs/agent/tasks/2026-08-01-saxs-real-boundary-after-ai-transport.md
---

# Acceptance Record

## Automated Evidence

- Real method evidence:
  `python -m pytest -q tests/test_saxs_real_method_evidence_surfaces.py -vv
  -o addopts= --basetemp=D:\PolyNexus-test-runs\saxs-real-boundary-methods-20260801`
  returned `3 passed in 75.34s`, exit code `0`. The three cases were Static,
  Temperature, and Strain, and each checked Parameter, Figure/Manifest, and
  Export method evidence.
- PAD8 boundary:
  `python -m pytest -q tests/test_saxs_real_2d_scientific_acceptance.py -vv
  -o addopts= --basetemp=D:\PolyNexus-test-runs\saxs-real-boundary-pad8-20260801`
  returned `4 passed in 20.61s`, exit code `0`.
- Real lifecycle:
  `python -m pytest -q tests/test_real_published_run_walkthrough.py -k saxs
  -vv -o addopts= --basetemp=D:\PolyNexus-test-runs\saxs-real-boundary-lifecycle-20260801`
  collected 15 items, selected 3, and returned `3 passed, 12 deselected in
  93.23s`, exit code `0`.

## Boundary Meaning

These runs confirm current-head software transport and conservative existing
gate behavior. PAD8 remains `diagnostic_only`; automated validation does not
promote geometry, mask, beam-center, orientation, temperature/strain meaning,
or publication roles.

No interpolation, frame fabrication, rescue execution, or scientific decision
was introduced by this verification slice. The source fixtures were read-only;
each pytest command used a separate external D: basetemp.

## Verification Closure

- Task-scoped verifier exited `0`: quality `297 passed`, preprocessing `106
  passed`, task/memory, Ruff, compile, type baseline, and whitespace checks
  passed.
- Storage report and dry-run clean exited `0` in non-destructive mode: `145`
  artifacts, `34,459,621,656` total bytes, `eligible_bytes=0`, `failures=[]`,
  and `removed=0`. No `test_storage.py --apply` ran.
- `git diff --check` exited `0`.

The explicit four-file documentation checkpoint is the final task step.

## Human Gates

Instrument-aware geometry/calibration review, mask validity, beam-center meaning,
orientation interpretation, temperature/strain scientific review, restarted
GUI inspection, and final publication/release approval remain open.
