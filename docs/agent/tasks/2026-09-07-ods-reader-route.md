---
task_id: 2026-09-07-ods-reader-route
kind: architecture
status: complete
date: 2026-09-07
title: Add a bounded native ODS table reader route
---

# Add a bounded native ODS table reader route

## Goal

Read standard OpenDocument Spreadsheet files through the existing generic table
conversion contract without requiring `odfpy` or creating a second result
representation.

## Non-goals

- Do not infer polymer technique, units, or scientific meaning from arbitrary
  spreadsheet cells.
- Do not execute macros, external links, embedded objects, or user-provided
  code.
- Do not claim support for proprietary Origin/Netzsch project formats.

## Affected boundaries

- `polynexus/readers/ods_reader.py`: bounded ZIP/XML table reader.
- `polynexus/core/canonical_experiments/one_dimensional.py`: route ODS sheets
  into the existing table mapping contract.
- `polynexus/core/input_formats/registry.py`: promote verified ODS containers.
- Focused reader, canonical, input-inspection, and ComputeRun tests.

## Implementation plan

1. Validate the ODS ZIP container, member paths, size budget, and XML payload.
2. Expand repeated rows/cells and preserve each sheet as a table of raw values.
3. Route sheets through the existing observed/proposed mapping logic.
4. Verify malformed containers fail closed and a valid ODS file reaches
   `CanonicalExperiment` and `ComputeRun`.

## Acceptance criteria

- [x] A valid ODS spreadsheet with a labelled curve converts to the existing
  technique template and retains sheet/source provenance.
- [x] Repeated rows/cells, numeric values, and text cells are handled without
  fabricated units or columns.
- [x] Invalid, oversized, path-traversal, and malformed ODS files fail closed.
- [x] No external code or embedded object is executed.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_ods_reader.py tests/test_input_formats.py tests/test_canonical_one_dimensional.py tests/test_compute_service.py
python scripts/verify.py --task docs/agent/tasks/2026-09-07-ods-reader-route.md --changed --types
git diff --check
```

## Follow-up

Netzsch `.ngb-sd7`/`.ngb-ds1` and Origin `.opju` still require independent
format validation or official portable-export bridges.

## Completion evidence

- Exact commands and outcomes: focused ODS, TA DMA, input-format, canonical,
  ComputeRun, CLI, and DMA tests pass (`122 passed, 3 skipped`); Ruff and
  whitespace checks pass.
- Known limitations or follow-up: formulas are not evaluated, only cell values
  are read, and arbitrary spreadsheets still require observed or explicit
  technique mapping. Netzsch and Origin private formats remain separate
  follow-up work.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  historical superpowers plans/specs, literature text files, and test fixtures.
