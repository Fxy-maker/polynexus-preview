# Capability Evidence Projection

## Goal

Make deterministic canonical capability items visible in the shared project
evidence and ARS citation ledger without duplicating provider calculations.

## Design

`ComputeRunService` remains the sole capability producer. The Agent workflow
step projection copies its JSON-safe `capability_items` into the public step
summary. Evidence extraction then emits generic citation metrics for completed
capability items, preserving the item id, measurement id, source locator, and
capability method. Items that are `not_applicable`, `needs_input`, or `failed`
are retained in the run projection but do not create numeric citation metrics.

Capability metrics are diagnostics by default: they document observed
deterministic calculations and do not promote a provider result into a paper
claim. Existing technique-specific eligibility rules remain authoritative.

## Boundaries

- No provider algorithm, material lookup, or fixed temperature rule changes.
- No new GUI material database.
- No reconstruction of raw data; all values come from the immutable
  `CapabilityItemResult` already attached to `ComputeRun`.
- Historical steps without capability items remain readable unchanged.

## Acceptance

- Agent/CLI/GUI shared step summaries expose capability items identically.
- Project evidence packages contain citable generic metrics for completed items.
- Metric IDs are deterministic and link back to run, source hash, and item id.
- Unsupported/failed capability items remain explicit and produce no fabricated
  numeric values.
