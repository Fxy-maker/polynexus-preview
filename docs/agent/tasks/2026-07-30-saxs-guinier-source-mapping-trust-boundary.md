---
task_id: 2026-07-30-saxs-guinier-source-mapping-trust-boundary
kind: scientific-core-contract
status: complete
date: 2026-07-30
title: Make Guinier sequence source mappings trusted only after validation
---

# SAXS Guinier source-mapping trust boundary

## Goal

Prevent malformed temperature Guinier source indices from appearing as trusted
frame or pair identities while preserving diagnostic facts.

## Non-goals

- No changes to q/I, Rg values, temperature values, frame ordering, quality
  levels beyond the existing invalid-mapping Diagnostic downgrade, or physical
  thresholds.
- No interpolation, frame fabrication, deletion, sorting, source-index repair,
  AI call, rescue action, or publication-role change.
- No changes to the parallel NMR files, `active-work.md`, `current-state.md`,
  generated outputs, real datasets, or test-storage directories.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`: raw source mapping
  validation and trusted pair/frame identity projection.
- `tests/test_saxs_guinier_source_mapping_trust.py`: focused regression tests.
- `tests/test_saxs_guinier_sequence_evidence.py`: existing length-mismatch
  expectation updated to the trusted-mapping contract.
- Existing Guinier sequence DTO consumers, through the unchanged public field
  names and reason codes.

## Implementation plan

1. Add RED coverage for complete valid, reordered, duplicate, invalid, and
   length-mismatched source mappings.
2. Validate raw mapping tokens before normalization and clear trusted mapping
   fields when any source identity defect exists.
3. Run focused sequence regressions, the exact SAXS matrix, task verifier,
   storage dry-run, diff checks, and one explicit allowlist checkpoint.

## Acceptance criteria

- [x] Complete valid mappings preserve frame and pair source identities.
- [x] Invalid, duplicate, and length-mismatched mappings retain diagnostic
  facts while emitting no trusted frame or pair identities.
- [x] Omitted mappings remain empty and all evidence remains strict-JSON safe.
- [x] Task-scoped verification and the explicit allowlist checkpoint complete.

Checkpoint: `b47f84e` (local only; no push).

## Verification

```powershell
python -m pytest -q tests/test_saxs_guinier_source_mapping_trust.py -o addopts= --basetemp=D:\PolyNexus_saxs_guinier_source_mapping_trust_red
python -m pytest -q tests/test_saxs_guinier_source_mapping_trust.py tests/test_saxs_guinier_sequence_evidence.py tests/test_saxs_series_metric_source_integrity.py -o addopts= --basetemp=D:\PolyNexus_saxs_guinier_source_mapping_trust_green
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-guinier-source-mapping-trust-boundary.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
```

The exact SAXS matrix requires a complete pytest summary and exit code `0`.
Full/boundary verification is reported only if it has both a pytest summary
and boundary result. `test_storage.py --apply` is not part of this task.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `tests/test_saxs_guinier_source_mapping_trust.py`
- `tests/test_saxs_guinier_sequence_evidence.py`
- `docs/superpowers/specs/2026-07-30-saxs-guinier-source-mapping-trust-boundary-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-guinier-source-mapping-trust-boundary.md`
- `docs/agent/tasks/2026-07-30-saxs-guinier-source-mapping-trust-boundary.md`
- `docs/acceptance/2026-07-30-saxs-guinier-source-mapping-trust-boundary.md`
- `docs/agent/memory/lessons/2026-07-30-saxs-guinier-source-mapping-trust-boundary.md`
