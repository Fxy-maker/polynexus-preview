# Release Evidence Refresh Design

## Decision

Maintain the full-goal acceptance record as an evidence ledger. Add the latest
SAXS 2D reviewer-context checkpoint and its independently verified test counts,
while retaining the formal full/boundary timeout and all source-specific and
human release gates.

## Boundaries

- A complete pytest summary with exit `0` is required for a test-pass claim.
- A tool timeout or child manifest exit caused by timeout remains incomplete
  evidence, not a product failure or pass.
- Automated review-context transport does not promote diagnostic,
  review-required, assignment-limited, or conditional science.
- No analysis, threshold, publication role, or scientific interpretation is
  changed by this refresh.
