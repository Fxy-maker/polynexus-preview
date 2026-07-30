# NMR embedded axis declaration

## Goal

Expose the unit-bearing JEOL/Delta acquisition declaration found in the
checked-in JDF/JDFF payloads so Results and export provenance can state which
vendor dimension is represented, its physical domain, origin field, sweep, and
point count.

## Non-goals

- Do not change the current solid-C assignment-limited policy or promote Xc.
- Do not infer a polymer assignment, phase split, or scientific calibration
  from the declaration alone.
- Do not modify SAXS, real fixture bytes, or generated test output.

## Affected boundaries

- `polynexus/core/nmr_engine/io.py`: parse the vendor acquisition declaration.
- `polynexus/core/nmr.py`: carry the declaration into run-level evidence.
- `polynexus/core/analysis_evidence_nmr.py`: publish it under axis evidence.
- `polynexus/gui/results_review_service.py` and `polynexus/gui/i18n.py`: render
  a compact, explicit review line.
- Focused NMR parser, evidence, Results, lifecycle, and native route tests.

## Evidence boundary

The declaration is parsed only from the vendor's `acquisition` text block:
`x_domain`, `x_offset`, `x_sweep`, and `x_points`. It is retained as source
provenance with the vendor field names and the dimension label `x` (the only
dimension in these 1D files). Numeric binary record fields remain raw
metadata.

## Implementation plan

1. Add real-file parser, malformed-input, evidence, and Results RED tests.
2. Parse complete ppm declarations from the vendor acquisition block and
   retain them as `declared_not_applied` metadata.
3. Project the declaration through NMR evidence and render its dimension,
   domain, origin, sweep, point count, and status.
4. Run focused/lifecycle/native verification, task checks, storage report, and
   an explicit allowlist checkpoint.

## Acceptance criteria

- [x] A real solid 13C file exposes a JSON-safe declaration for vendor
  dimension `x` / dimension 1, `Carbon13`, origin `x_offset=100 ppm`, sweep
  `x_sweep=300 ppm`, and `x_points=1024`.
- [x] A real solid 1H file exposes the analogous `Proton`, `0 ppm`, `200 ppm`,
  and `2048` values.
- [x] Missing, malformed, or mismatched declarations are omitted or marked
  unconfirmed without changing the existing default axis or assignment gate.
- [x] Focused tests, structured verification, diff check, storage report, and
  an explicit allowlist checkpoint are recorded.

## Verification

```powershell
python -m pytest -q tests/test_nmr_engine.py -k embedded_axis_declaration
python -m pytest -q tests/test_nmr_engine.py tests/test_analysis_evidence.py tests/test_results_review_service.py
python scripts/verify.py --task docs/agent/tasks/2026-07-30-nmr-embedded-axis-declaration.md --changed --types
git diff --check
python scripts/test_storage.py report --json
```

## Observed results

- `tests/test_nmr_engine.py`: `22 passed in 95.19s`.
- NMR evidence slice: `14 passed, 129 deselected in 0.58s`.
- NMR Results review slice: `3 passed, 30 deselected in 0.23s`.
- Real NMR lifecycle: `4 passed in 243.02s`.
- Native Windows `nmr.solid_c` route: `1 passed, 16 deselected in 19.06s`;
  four captures are in `D:\PolyNexus_native_nmr_embedded_axis_20260730_v2`.
- Task verifier: selected checks passed, including quality `296 passed`,
  preprocessing `106 passed`, Ruff, compile, type baseline, memory/task, and
  whitespace.
- `git diff --check`: exit code `0`.
- Storage report: `79` artifacts, `eligible_bytes=0`, `emergency=false`; no
  apply or deletion was performed.
- Explicit allowlist checkpoint: final `HEAD` commit
  (`feat(nmr): expose embedded JEOL axis declaration`); no push was performed.
