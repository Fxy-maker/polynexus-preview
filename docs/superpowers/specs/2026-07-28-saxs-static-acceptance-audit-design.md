# SAXS Static Scientific Acceptance Audit Design

**Date:** 2026-07-28
**Status:** Approved working design for the active SAXS quality goal

## Problem

Static SAXS already emits quality and metric evidence and uses an explicit
publication gate, but Static parameters do not expose the unified read-only
scientific acceptance audit used by temperature and strain. Consumers must
branch on mode to distinguish software validation from evidence readiness.

## Design

Add a private SAXS payload helper that attaches
`build_saxs_scientific_acceptance_audit(result.validation_passed, payload)` and
returns the same payload. Call it only at the existing Static batch, Static
single-analysis, and Static single-profile return boundaries. Temperature and
strain retain their current direct attachment paths.

Static publication flags are not synthesized. Because the existing Static
publication gate is owned by the Figure eligibility/provider boundary, the
audit reports those fields as `None` unless already present and never promotes
an asset.

## Safety boundary

The helper only reads and detaches existing fields. It does not run analysis,
change metric quality, alter `_batch_data`, or modify the Static publication
decision. The existing SAXS validation-hook refresh keeps the audit snapshot
consistent after final validation.

## Verification

Tests cover a Static single `SAXSResult`, an aligned batch with a missing frame,
strict JSON, and an optional real `普通小角` directory. The exact SAXS matrix,
task verifier, diff check, and explicit allowlist checkpoint are required.
