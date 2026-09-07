---
task_id: 2026-09-07-ta-dma-reader-route
kind: architecture
status: complete
date: 2026-09-07
title: Add a bounded native reader route for TA Instruments DMA binary exports
---

# Add a bounded native reader route for TA Instruments DMA binary exports

## Goal

Turn the already identified TA Instruments DMA Q800 `.001`/`.002`/`.003`/`.004`/`.005`
exports into canonical DMA measurements while preserving the raw artifact,
header signals, units, and binary-reader provenance.

## Non-goals

- Do not claim support for every vendor `.001` file or for proprietary Netzsch,
  Origin, or undocumented formats.
- Do not infer missing geometry, calibration, or material interpretation.
- Do not mutate or rewrite the original binary source.
- Do not dynamically load third-party code.

## Affected boundaries

- `polynexus/readers/ta_dma_reader.py`: bounded, deterministic TA DMA binary
  reader.
- `polynexus/core/canonical_experiments/one_dimensional.py`: route the reader
  into the existing `CanonicalExperiment`/`Measurement` contract.
- `polynexus/core/input_formats/registry.py`: promote only a verified TA DMA
  signature to the built-in reader route; other `.001` files stay actionable.
- Focused reader, canonical conversion, inspection, and ComputeRun tests.

## Implementation plan

1. Add bounded TA Q800 binary decoding with strict signature, record, and
   sentinel validation.
2. Convert decoded time-axis channels into the existing DMA canonical
   measurement contract with source-bound provenance.
3. Register the reader only for matching `.001`–`.005` signatures and route
   ComputeRun through the shared canonical path.
4. Verify synthetic malformed/valid fixtures and replay one public Q800 file
   without adding validation data to the repository.

## Acceptance criteria

- [x] A valid TA DMA binary signature and signal header convert to a
  `dma_curve_1d.v1` template without a temporary export or a second result store.
- [x] All unambiguously labelled `SigN` channels are retained as separate
  measurements with source units and header provenance.
- [x] Truncated, malformed, or non-DMA `.001` files fail closed with an
  actionable reason and never reach provider execution.
- [x] Existing generic `.001` compatibility tests and all shared ComputeRun
  consumers remain compatible.
- [x] No proprietary format claim is broadened beyond the verified signature.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_ta_dma_reader.py tests/test_input_formats.py tests/test_compute_service.py tests/test_cli_run_single_service.py
python scripts/verify.py --task docs/agent/tasks/2026-09-07-ta-dma-reader-route.md --changed --types
git diff --check
```

## Follow-up

Netzsch `.ngb-sd7`/`.ngb-ds1`, Origin `.opju`, and other vendor formats still
need independent reader implementations or portable export bridges, plus
isolated execution, licensing, real-instrument replay, uncertainty, and human
scientific review before formal capability promotion.

## Completion evidence

- Exact commands and outcomes: focused TA DMA, input-format, canonical, and DMA
  tests pass; real public Q800 replay produced 17 decoded channels, 1041 rows,
  9 canonical measurements, and a completed ComputeRun.
- Known limitations or follow-up: only the observed TA Q800 `CLOSED`/UTF-16LE,
  `Nsig`, `SigN`, float32 layout is supported. Other `.001` vendor files,
  alternate TA versions, and all Netzsch/Origin opaque formats remain outside
  this reader. Formal DMA models, uncertainty, and capability promotion remain
  review-required.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`,
  historical superpowers plans/specs, literature text files, and test fixtures.
