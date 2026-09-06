---
task_id: 2026-09-05-public-validation-pack
kind: scientific
status: implementation_complete_review_required
date: 2026-09-05
title: Build public polymer-data validation pack
---

# Build Public Polymer-Data Validation Pack

## Goal

Create a reproducible, externally stored validation-data pack whose manifest
records public source metadata, license evidence, source checksums, local
checksums, rawness, material context, and the expected PolyNexus replay route.

## Non-goals

- Do not commit third-party raw data, personal data, generated figures, or
  downloaded archives to the repository.
- Do not call non-polymer or processed files standard samples.
- Do not promote a capability or change scientific thresholds based only on
  downloaded data.
- Do not add accounts, access control, or a new persistence representation.

## Shared objects and entry points

- Objects: validation manifest, source raw artifact, future replay case.
- AI/Codex/CLI: reads the same manifest and external data root; no private
  dataset index.
- GUI: unchanged in this task; future import/replay consumers use the same
  manifest and canonical routes.
- Cross-entry rule: this task adds source metadata and an inspection utility;
  it does not change ComputeRun, Evidence Package, or GUI contracts.

## Affected boundaries

- External validation-data root and public source manifest.
- `scripts/validation_pack.py` download, checksum, archive inspection, and
  lock-manifest commands.
- Focused manifest tests and validation documentation only.

## Implementation plan

1. Record openly licensed source archives and expected PolyNexus routes in a
   repository manifest.
2. Download selected archives into an external root with checksum verification
   and resumable temporary files.
3. Inspect archive members and write external reports and a local-hash lock
   manifest.
4. Verify manifest safety, checksum drift detection, and task quality gates.

## Acceptance criteria

- [x] Selected public archives are downloaded only when license and source
  checksum are recorded.
- [x] Each file is classified as acquisition raw, instrument export, processed
  curve, or reference-only after archive inspection.
- [x] A manifest validator rejects missing identity, checksum, license, or
  route fields and detects local checksum drift.
- [x] The README names material and metadata limitations and identifies
  missing technique coverage without overstating validation claims.
- [x] Repository contains scripts and small manifest tests only; third-party
  data remains outside Git.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_validation_pack_manifest.py
python scripts/verify.py --task docs/agent/tasks/2026-09-05-public-validation-pack.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(validation): add public data pack manifest" `
  --files docs/agent/tasks/2026-09-05-public-validation-pack.md `
          scripts/validation_pack.py `
          tests/test_validation_pack_manifest.py `
          docs/validation/public-validation-pack.json `
          docs/validation/public-validation-pack.md `
          docs/agent/memory/active-work.md `
          docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes:
  - `python -m pytest -p no:cacheprovider -q tests/test_validation_pack_manifest.py` - 5 passed.
  - `python scripts/validation_pack.py --data-root D:/PolyNexus-validation-data download --technique dsc` - downloaded and verified the DSC archive against Zenodo MD5.
  - `python scripts/validation_pack.py --data-root D:/PolyNexus-validation-data download --technique saxs` - verified the first SAXS archive and downloaded the second against Zenodo MD5.
  - `python scripts/validation_pack.py --data-root D:/PolyNexus-validation-data inspect` - wrote the external archive report; 12 inspected, 0 checksum mismatches, 0 missing.
  - `python scripts/validation_pack.py --data-root D:/PolyNexus-validation-data lock` - wrote the external SHA-256 lock manifest with 12 inspected entries.
  - `python scripts/validation_pack.py --data-root D:/PolyNexus-validation-data validate --require-local` - valid: 12 manifest entries.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-05-public-validation-pack.md --changed --types` - passed Ruff, compile, quality 313, preprocessing 157, and whitespace.
  - `git diff --check` - passed.
- Known limitations or follow-up: all 12 planned archives are now acquired and inspected, but they remain candidates until selected members are bound to canonical replay cases. The non-polymer SAXS/WAXS data is format-only. SEC/GPC and rheology still need portable polymer instrument exports. No archive member is yet bound to a formal replay case or capability-promotion evidence.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`, manuscript plans/specs, `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/`.
