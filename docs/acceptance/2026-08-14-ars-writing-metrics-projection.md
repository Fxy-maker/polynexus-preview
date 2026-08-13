# ARS Writing Metrics Projection Acceptance

Date: 2026-08-14

`writing-evidence.json` now provides a compact writing-facing projection for
each evidence item. It preserves package-relative figure/table paths and
extracts finite scalar provider values under `observed_metrics`, while keeping
the complete `observed_results` payload for auditability.

No provider output is interpreted, calibrated, merged across techniques, or
turned into manuscript prose by this projection. ARS and the writing skills
remain responsible for narrative selection and scientific review.

Verification: project writing/package/figure matrix `32 passed`; structured
quality/preprocessing gates `303` / `157` passed.
