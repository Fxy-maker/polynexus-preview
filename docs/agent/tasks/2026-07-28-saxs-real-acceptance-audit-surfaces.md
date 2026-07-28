---
kind: task
status: completed
date: 2026-07-28
title: Verify real SAXS audit consistency across figures and export
---

# Real SAXS acceptance audit surfaces

## Goal

Replay the repository's real Static, Temperature, and Strain SAXS fixtures and
prove that the final parameter audit, Figure/Manifest audit, and exported
`quality_evidence.json` remain consistent without promoting scientific status.

## Non-goals

- Do not change algorithms, quality thresholds, publication roles, rescue, AI,
  real data, or generated repository outputs.
- Do not turn validation failure into success or infer scientific trends.
- Do not treat automated lifecycle evidence as human scientific or GUI sign-off.

## Affected boundaries

- Real fixture replay through `SAXSEngine.run_pipeline`;
- Figure Manifest documents and bundle `quality_evidence.json` in external
  pytest output roots;
- focused real-data regression and durable task/spec/plan/acceptance records.

## Implementation plan

1. Replay the available real Static, Temperature, and Strain fixtures under an
   external pytest output root and compare the existing audit contracts.
2. If lifecycle ordering leaves Figure documents stale, refresh only their
   existing audit provenance field after final validation.
3. Run the focused regression, structured verifier, diff check, and test-storage
   report, then create the explicit allowlist checkpoint.

## Acceptance criteria

- [x] Real Static, Temperature, and Strain fixtures replay when available and
  expose strict-JSON `scientific_acceptance_audit` parameters.
- [x] Every produced SAXS Figure/Manifest provenance audit equals the final
  parameter audit for that run, without role promotion.
- [x] Exported `quality_evidence.json` carries the same audit and is registered
  in the bundle manifest.
- [x] Existing temperature validation failure and diagnostic evidence remain
  visible; no status is relaxed.
- [x] Focused real test, task verifier, diff check, storage report, and explicit
  allowlist checkpoint are recorded; unavailable fixtures are reported as
  skips, not claimed as passes.

## Verification

```powershell
python -m pytest -q tests/test_saxs_real_acceptance_audit_surfaces.py -vv --basetemp C:\Temp\PolyNexus_saxs_real_acceptance_audit_surfaces
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-real-acceptance-audit-surfaces.md --changed --types
git diff --check
python scripts/test_storage.py report --json
```

## Explicit changed-file allowlist

- `tests/test_saxs_real_acceptance_audit_surfaces.py`
- `polynexus/core/saxs.py`
- this task card
- `docs/superpowers/specs/2026-07-28-saxs-real-acceptance-audit-surfaces-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-real-acceptance-audit-surfaces.md`
- `docs/acceptance/2026-07-28-saxs-real-acceptance-audit-surfaces.md`
- `docs/agent/memory/active-work.md`

Do not include `current-state.md`, real datasets, generated outputs, or
parallel scratch files.
