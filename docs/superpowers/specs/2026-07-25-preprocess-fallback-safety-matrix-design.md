# Preprocessing Fallback Safety Matrix Design

## Goal

Ensure AI-assisted preprocessing cannot auto-accept a candidate whose analysis
still depends on an explicit fallback path.

## Design

`PreprocessEvidence` gains optional, backward-compatible `fallback_active` and
`fallback_reason` fields. The shared technique adapter derives these fields
from known output/evidence keys (`fallback_active`,
`calibrated_fallback_active`, `temperature_calibration_fallback_active`, and
their reason fields) without interpreting technique-specific values. The
decision layer adds a hard guard before scoring; active fallback forces
`keep_original`, `low`, and reason code `fallback_active`.

The matrix covers the five supported single-technique optimization policies and
adapters. AI-off remains the existing deterministic path with default shadow
policy; engine failure remains the existing failed-run guard. Joint is not a
single-technique preprocessing target, so its matrix row is explicit N/A and
its existing report-level AI context remains review-only.

## Compatibility and testing

All new evidence fields have defaults, so old serialized payloads remain
readable. Tests assert the shared guard for every supported technique, reason
round-tripping, and byte-equivalent deterministic AI-off behavior. Existing
fault-injection tests continue to cover rollback and audit failures.
