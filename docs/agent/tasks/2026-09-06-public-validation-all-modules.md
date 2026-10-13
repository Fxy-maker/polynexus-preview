---
task_id: 2026-09-06-public-validation-all-modules
kind: scientific
status: completed
date: 2026-09-06
title: Run public validation pack across all technique routes
---

# Run Public Validation Pack Across All Technique Routes

## Goal

Execute a bounded, reproducible smoke/replay-preparation pass over the
downloaded public validation pack for every PolyNexus technique route and
record whether each route completed, produced diagnostic output, or was
unavailable because the archive lacks a supported portable input.

## Non-goals

- Do not call public files certified standards or promote a capability.
- Do not infer polymer science conclusions from non-polymer SAXS/WAXS data.
- Do not bulk-extract archives or commit third-party raw data.
- Do not add vendor readers, calibration models, uncertainty models, or new
  scientific thresholds in this validation pass.

## Shared objects and entry points

- Objects: external validation archive, selected extracted input, run report;
  future replay cases remain separate until expected metrics and tolerances
  are reviewed.
- AI/Codex/CLI: use the same public engine/CLI routes and external data root.
- GUI: unchanged; this is a headless validation run.
- Cross-entry rule: no shared result contract changes; reports must retain
  source archive/member, route, status, and limitation provenance.

## Affected boundaries

- External data root `D:\PolyNexus-validation-data` and its run report.
- Existing CLI/Core routes for DSC, FTIR, SAXS, WAXS, NMR, TGA, DMA,
  rheology, SEC/GPC, and mechanics.
- This task records observed support; it does not alter provider algorithms.

## Implementation plan

1. Inspect the locked external manifest and selected archive members without
   adding third-party raw data to the repository.
2. Execute one bounded CLI/Core route per technique, retaining exit code,
   Core status, output location, and diagnostic limitations.
3. Re-run WAXS with an explicit portable-table header after the original
   headerless input is rejected, and record the derivation provenance.
4. Correct the external all-module report so unavailable inputs, diagnostic
   output, and valid computed output are represented separately.
5. Run manifest, focused regression, task, and diff verification, then create
   an allowlisted local checkpoint without push or merge.

## Acceptance criteria

- [x] Each technique has one explicit attempted route or an explicit
  `unavailable` record with a source/format reason.
- [x] Successful routes retain run status, input member, output path, and
  diagnostic metric summary; failures retain the exception/status without
  inventing values.
- [x] Non-polymer scattering and processed/vendor-only files are labelled as
  format/replay preparation evidence, not standard-sample validation.
- [x] The report is reproducible from the locked external manifest and no raw
  archive is added to Git.

## Verification

```powershell
python scripts/validation_pack.py --data-root D:/PolyNexus-validation-data validate --require-local
python -m pytest -p no:cacheprovider -q tests/test_validation_pack_manifest.py
python scripts/verify.py --task docs/agent/tasks/2026-09-06-public-validation-all-modules.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "test(validation): run public pack across technique routes" `
  --files docs/agent/tasks/2026-09-06-public-validation-all-modules.md `
          docs/agent/memory/active-work.md `
          docs/agent/memory/current-state.md
```

## Completion evidence

- External report: `D:/PolyNexus-validation-data/public/runs/2026-09-06-all-modules/all-modules-report.json`.
- Ten technique routes are represented. IR, SAXS, WAXS, and NMR produced
  diagnostic Core output; DSC, TGA, DMA, SEC/GPC, and Mechanics are recorded
  as unavailable for the selected input rather than successful analyses;
  Rheology is explicitly unavailable because no suitable public input exists.
- WAXS was rerun with the header-normalized derived CSV. The report retains
  the original `.dat` mapping-ambiguity attempt and the derivation provenance.
- `python scripts/validation_pack.py --data-root D:/PolyNexus-validation-data validate --require-local` passed (`12` manifest entries).
- `python -m pytest -p no:cacheprovider -q tests/test_validation_pack_manifest.py tests/test_waxs_loader_regression.py` passed (`6 passed`).
- `python scripts/verify.py --task docs/agent/tasks/2026-09-06-public-validation-all-modules.md --changed --types` and `git diff --check` passed.
- Limitations: this is parser/Core route smoke testing, not certified-standard
  validation, independent replay, uncertainty validation, or capability
  promotion. SAXS/WAXS inputs are non-polymer datasets; NMR contains an
  implausible observed ppm axis; the selected thermal/DMA files are vendor
  binaries; SEC/GPC has only `.opju`; the selected Mechanics file is
  ellipsometry; no raw rheology export was present.
- Pre-existing workspace changes were left untouched, including
  `polynexus/core/agent_workflow/service.py`, the existing plans/specs,
  `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/`.
