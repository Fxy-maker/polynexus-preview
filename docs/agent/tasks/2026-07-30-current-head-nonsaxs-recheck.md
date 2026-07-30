---
task_id: 2026-07-30-current-head-nonsaxs-recheck
kind: verification-audit
status: completed
date: 2026-07-30
title: Recheck current non-SAXS software and native NMR routes
---

# Current HEAD Non-SAXS Recheck

## Goal

Record current-checkout regression and native GUI route evidence after the
NMR solid-C readiness checkpoint, while keeping SAXS and scientific approval
outside this recheck.

## Non-goals

- Do not modify production code, SAXS code/tests, real datasets, or review
  decisions.
- Do not treat native route construction as scientific or release approval.
- Do not delete, migrate, or apply-clean test data.

## Affected boundaries

- Non-SAXS test matrices and current Windows Qt native route harness.
- Acceptance and durable memory records only; no production behavior.
- External pytest basetemps and native capture artifacts.

## Implementation plan

1. Run current non-SAXS recursive regression shards with external basetemps.
2. Run the Windows Qt NMR native route and inspect representative captures.
3. Run boundary/diff checks and record exact results and remaining gates.
4. Verify this audit card and create one documentation-only checkpoint.

## Acceptance criteria

- [x] Current DSC/WAXS, IR, and NMR/Joint shard results include complete
      pytest summaries and exit code 0.
- [x] Current Windows Qt NMR route covers all four partitions and exits 0.
- [x] Boundary audit and diff hygiene pass without production/data changes.
- [x] Remaining human scientific and release gates remain explicit.
- [x] Task verifier and final diff/boundary checks are recorded below; the
      explicit documentation-only checkpoint is this task's commit.

## Verification

```powershell
$env:POLYNEXUS_TEST_ROOT='D:\PolyNexus-test-runs-current-audit'
$env:POLYNEXUS_TEST_RETENTION='review'
python scripts/verify.py --task docs/agent/tasks/2026-07-30-current-head-nonsaxs-recheck.md --changed --types
python scripts/boundary_audit.py --root D:\PolyNexus --json
git diff --check
```

## Evidence

| Scope | Result |
| --- | --- |
| DSC/WAXS recursive shard | `118 passed in 63.02s`, exit 0 |
| IR recursive shard | `55 passed in 55.38s`, exit 0 |
| NMR/Joint recursive shard | `70 passed in 561.47s`, exit 0 |
| Windows Qt native NMR route | `4 passed, 13 deselected in 137.74s`, exit 0 |
| Boundary audit | JSON inventory emitted, exit 0 |
| `git diff --check` | exit 0 |

All pytest shards used `-p no:cacheprovider` and external D: test roots. The
native run used `QT_QPA_PLATFORM=windows`. Offscreen mode was separately
classified as `4 skipped` because the native test explicitly requires the
Windows platform; it was not counted as acceptance evidence.

## Native capture

The NMR native route generated Results, Gallery, History, and Editor captures
under:

`D:\PolyNexus-test-runs-current-native\pytest\run-20260730T105557316506Z-51536\test_native_windows_gui_real_r3\native_gui_captures`

The solid-C Results surface visibly retains `Review required |
reason=review_missing`. The figure/editor route is constructible, but peak
assignment truth, label policy, and Xc promotion remain reviewer-owned.

## Remaining gates

This recheck does not close the full four-mode visual audit, IR sample-level
ROI/calibration confirmation, NMR solid-C assignment policy, Joint conflict
precedence, or final release authorization. Those fields remain explicit in
`docs/agent/tasks/2026-07-29-release-decision-packet.md`.

## Verification log

- Task verifier exited `0`; quality gate `292 passed`, preprocessing gate
  `106 passed`, Ruff, compile, memory/task, type baseline, and whitespace all
  passed.
- Boundary audit and `git diff --check` were run before the final documentation
  update and returned exit `0`; they are rerun after this update before the
  checkpoint.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-30-current-head-nonsaxs-recheck.md`
- `docs/acceptance/2026-07-30-current-head-nonsaxs-recheck.md`
- `docs/superpowers/specs/2026-07-30-current-head-nonsaxs-recheck-design.md`
- `docs/superpowers/plans/2026-07-30-current-head-nonsaxs-recheck.md`
- `docs/agent/memory/active-work.md`
