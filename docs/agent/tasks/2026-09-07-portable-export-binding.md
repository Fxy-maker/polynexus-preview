---
task_id: 2026-09-07-portable-export-binding
kind: architecture
status: complete
date: 2026-09-07
title: Bind portable exports to opaque vendor raw artifacts
---

# Bind portable exports to opaque vendor raw artifacts

## Goal

Provide one shared Core route for Proteus/Origin/vendor exports while retaining
the original private raw artifact as the scientific source reference.

## Non-goals

- Do not decode private binary bytes or claim direct vendor-format support.
- Do not overwrite or mutate the raw source or exported table.
- Do not infer exporter correctness, calibration, or scientific meaning.

## Affected boundaries

- `polynexus/core/canonical_experiments/portable_export.py`: immutable binding
  DTO and bounded hash validation.
- `polynexus/core/canonical_experiments/registry.py`: convert a portable table
  while retaining the raw-source binding in the canonical object.
- Focused canonical and ComputeRun tests.

## Implementation plan

1. Hash and validate the opaque raw source and portable export independently.
2. Convert the portable export through the existing table route using the raw
   artifact identity.
3. Add a binding record to the canonical payload and conversion provenance.
4. Verify replay and ComputeRun preserve the binding without a second result
   store.

## Acceptance criteria

- [x] A valid raw/export pair produces the selected technique's existing
  canonical template with both hashes and exporter metadata.
- [x] Missing, symlinked, oversized, or mismatched inputs fail closed.
- [x] Existing direct conversion remains unchanged.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_portable_export_binding.py tests/test_canonical_converter_registry.py tests/test_compute_service.py
python scripts/verify.py --task docs/agent/tasks/2026-09-07-portable-export-binding.md --changed --types
git diff --check
```

## Completion evidence

- Exact commands and outcomes: portable-export, canonical registry, and
  ComputeRun tests pass (`66 passed, 4 skipped`); direct conversion remains
  green.
- Known limitations or follow-up: this is an explicit export bridge, not a
  private-format decoder. Exporter correctness, calibration, and scientific
  semantics still require instrument-software checks and later review.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  historical superpowers plans/specs, literature text files, and test fixtures.
