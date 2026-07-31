---
task_id: 2026-07-31-nmr-vendor-real-case-registry
kind: real-data-evaluation
status: completed
date: 2026-07-31
title: Register NMR vendor real-engine cases
---

# NMR vendor real-case registry

## Goal

Register the existing liquid H/C and solid H/C NMR inputs as real-engine
evaluation cases while preserving the absence of reviewer-approved scientific
ground truth.

## Non-goals

- No changes to `测试数据/NMR`, NMR algorithms, assignment readiness, ppm
  calibration, Xc, Figure roles, or publication promotion.
- No scientific score or acceptance conclusion for `vendor_unreviewed` cases.
- No storage apply, deletion, migration, push, merge, or deployment.

## Affected boundaries

- `tests/eval/runner.py` provenance schema only.
- Four JSON descriptors under `tests/eval/cases/real`.
- One focused real-engine regression using external pytest output.

## Implementation plan

1. Add the registry test and confirm the expected RED state.
2. Add `vendor_unreviewed` and four relative source descriptors.
3. Run the four real NMR inputs through the existing engine into `tmp_path`.
4. Run structured verification, storage dry-run, diff check, and one explicit
   allowlist checkpoint.

## Acceptance criteria

- [x] Exactly four NMR vendor cases are loadable: liquid H/C and solid H/C.
- [x] Each case resolves to an existing input and `_uses_real_engine` is true.
- [x] Each case runs through the real NMR engine with output outside the source
      tree and preserves engine/submodule/source provenance.
- [x] Every case has `source: vendor_unreviewed` and `ground_truth: {}`; no
      scientific score is interpreted as reviewer approval.
- [x] Existing NMR bridge regression remains green.
- [x] Task verifier, diff check, storage report/dry-run, and allowlist checkpoint
      have exact outcomes.

## Explicit changed-file allowlist

- `tests/eval/runner.py`
- `tests/eval/test_nmr_vendor_real_case_registry.py`
- `tests/eval/cases/real/nmr_real_liquid_h_vendor.json`
- `tests/eval/cases/real/nmr_real_liquid_c_vendor.json`
- `tests/eval/cases/real/nmr_real_solid_h_vendor.json`
- `tests/eval/cases/real/nmr_real_solid_c_vendor.json`
- `docs/superpowers/specs/2026-07-31-nmr-vendor-real-case-registry-design.md`
- `docs/superpowers/plans/2026-07-31-nmr-vendor-real-case-registry.md`
- `docs/agent/tasks/2026-07-31-nmr-vendor-real-case-registry.md`
- `docs/acceptance/2026-07-31-nmr-vendor-real-case-registry.md`

Pre-existing memory edits, parallel SAXS changes, real dataset files, and
scratch/test-storage directories are excluded.

## Verification

```powershell
python -m pytest -q tests/eval/test_nmr_vendor_real_case_registry.py tests/eval/test_runner_real_nmr.py -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-31-nmr-vendor-real-case-registry.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

The storage commands are dry-run only.

## Evidence

- RED: before the registry implementation, the focused test collected 6 items
  and failed all 6 because the four case descriptors were absent.
- GREEN registry: `6 passed in 116.32s`, exit `0`.
- Registry plus existing NMR bridge: `7 passed in 118.12s`, exit `0`.
- The real tests wrote figures only below pytest-owned external `tmp_path`
  directories; no files under `测试数据/NMR` were edited.
- Solid-C output remained `Xc_assignment_status=assignment_limited`; the empty
  truth set did not create a scientific acceptance score.
- Task verifier exited `0`; quality `297 passed`, preprocessing `106 passed`,
  task/memory, Ruff, compile, type baseline, and whitespace checks passed.
- Storage report and dry-run clean both exited `0`: `62` artifacts,
  `8,885,679,473` bytes in the report, `eligible_bytes=0`, `10` emergency
  candidates with `0` eligible bytes, and `removed=0`. No `--apply` was run.
- `git diff --check` exited `0`.
