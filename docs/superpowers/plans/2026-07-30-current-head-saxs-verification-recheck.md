# Current-head SAXS verification recheck plan

1. Run the SAXS-only matrix on the current checkout with offscreen Qt and a
   writable workspace basetemp.
2. Inspect the full/boundary process outcome and separate Qt native crashes,
   tool aborts, and basetemp setup errors from test failures.
3. Record the exact evidence in the task card, acceptance note, and durable
   active-work memory.
4. Run task-scoped verification and `git diff --check`, then checkpoint only
   the explicit documentation allowlist.

No production behavior or scientific policy is changed by this audit.

Outcome: the SAXS matrix is green, while full/boundary remains unproven due to
the recorded Qt crash/abort. The task-scoped quality gate is also not green:
`288 passed, 2 failed, 3 warnings`, caused by the pre-existing history-table
locale expectation mismatch. Storage inspection remained dry-run only with
`54` artifacts, `6` eligible, and `0` removed.
