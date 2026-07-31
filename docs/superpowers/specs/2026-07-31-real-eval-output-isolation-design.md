# Real Evaluation Output Isolation Design

## Goal

Allow a real evaluation case to direct engine artifacts to a caller-owned
external output directory instead of relying on an empty engine default.

## Scope

- read optional `eval_output_dir` from a case's config overrides;
- pass it only as the existing `run_pipeline(..., output_dir=...)` argument;
- preserve all analysis, scoring, provenance, and config semantics;
- exercise the forwarding contract with an engine double.

## Non-goals

- no changes to NMR algorithms or real input files;
- no output cleanup, deletion, or storage apply;
- no scientific truth, assignment, calibration, or publication changes.

## Safety boundary

The field is an evaluation harness control, not a scientific configuration
parameter. If absent, the existing empty-string behavior remains compatible;
registered vendor cases and callers can opt into an external output root.
