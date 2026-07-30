# Current-head full/boundary post-cleanup recheck

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-30-current-head-full-boundary-post-cleanup-recheck.md`
Status: partial automated audit; full verifier result unavailable

## Scope

This audit rechecks the current checkout after the test-storage rule update.
It is documentation-only. No production code, test, scientific policy, real
dataset, or parallel SAXS worktree was changed.

## Evidence

- Full/boundary command started with an isolated test root:
  `POLYNEXUS_TEST_ROOT=D:\PolyNexus-test-runs-full-current-20260730`
  and `POLYNEXUS_TEST_RETENTION=review`.
- Command:
  `python scripts/verify.py --changed --types --full --boundary`
- The wrapper returned `command timed out` with exit `124` after its 30-minute
  tool limit and no complete pytest summary. The child process was later
  confirmed absent. This is recorded as a timeout/incomplete result, not as a
  pass. A separate shared verifier was intentionally excluded from this
  result.
- Boundary audit:
  `python scripts/boundary_audit.py --root D:\PolyNexus --json`
  returned exit code `0`; no boundary failures were reported. The audit
  reported 15 large-file entries and 15 broad-exception hotspots as the
  repository baseline inventory.
- Storage report:
  `python scripts/test_storage.py report --json` returned exit code `0` in
  dry-run mode. It found `82` artifacts totaling `24,069,383,574` bytes;
  `38` emergency-eligible artifacts totaling `14,710,294,260` bytes.
- Storage clean plan:
  `python scripts/test_storage.py clean --older-than-hours 24 --json`
  returned exit code `0` in dry-run mode with the same inventory and
  `removed=0`. No `--apply` operation was run.
- `git diff --check` returned exit code `0`.

## Acceptance classification

- [ ] Fresh full verification has a complete pytest summary and exit code;
  this remains open because the wrapper timed out with exit `124`.
- [x] Boundary outcome is recorded separately from full verification.
- [x] Incomplete full-verifier output is explicitly classified as a
  limitation, not a pass.
- [x] Storage report and clean plan are non-destructive and record eligible
  and removed counts.
- [x] Diff whitespace check passed.
- [x] Task-scoped verifier passed: quality `296`, preprocessing `106`, Ruff,
  compile/type baseline, memory/task checks, and whitespace all passed.
- [x] This document, task card, plan, spec, and active-work entry are the
  explicit documentation-only checkpoint allowlist.

## Limitations and next action

The current full/boundary release gate remains open because its authoritative
pytest summary was not returned before the wrapper timeout. The emergency
storage candidates also remain untouched by design. The audit task itself is
complete with this limitation; do not promote the overall release beyond
`conditional`.
