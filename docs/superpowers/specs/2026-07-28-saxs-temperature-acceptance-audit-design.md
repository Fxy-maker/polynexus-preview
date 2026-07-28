# SAXS Temperature Scientific Acceptance Audit Design

**Date:** 2026-07-28
**Status:** Approved working design for the current SAXS quality goal

## Problem

The SAXS temperature pipeline can retain useful diagnostic frame and sequence
evidence while its validation fails, but its parameter payload currently does
not expose the same read-only scientific acceptance boundary already available
for strain results. This makes downstream consumers inspect different contracts
for two series modes.

## Goal

Reuse `build_saxs_scientific_acceptance_audit()` at the temperature parameter
boundary. The audit is an existing-gates-only summary; it is not a scientific
approval or publication decision.

## Contract

After existing temperature parameters and aligned `_batch_data` are assembled,
`get_parameters()` adds `scientific_acceptance_audit`. The builder receives the
unchanged `result.validation_passed` value and the final detached payload. Its
existing status, evidence levels, provenance validity, reason codes, and
publication flags are preserved. The returned audit must contain
`publication_decision_changed=False` and remain strict JSON safe.

## Scientific boundary

The integration does not interpret or repair temperature frames. In particular,
it does not interpolate missing repeats, change source ordering, change Guinier
sequence validity, alter Q* or mask gates, or promote `Unusable`/`Diagnostic`
evidence. Existing physical metrics and quality gates remain authoritative; the
audit only makes their current boundary visible.

## Integration boundary

Only the temperature branch in `polynexus/core/saxs.py` changes. The existing
audit builder, strain branch, static branch, GUI, export roles, rescue path, and
real input files remain outside scope.

## Verification

Tests cover a temperature parameter payload built from an existing failed
validation/evidence state, preservation of the existing Guinier sequence reason,
strict JSON serialization, and the optional real PA6 temperature directory.
The exact SAXS matrix, task-scoped verifier, diff check, and explicit allowlist
checkpoint are required.
