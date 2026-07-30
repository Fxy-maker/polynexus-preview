# SAXS Guinier source-mapping trust boundary

Status: implementation and focused verification complete; the shared quality
gate has an unrelated parallel-NMR failure, and the allowlist checkpoint is
pending.

This slice narrows only the trust boundary for existing temperature Guinier
source-index evidence. Invalid, duplicate, or length-mismatched mappings must
remain visible as diagnostic facts while no longer being emitted as trusted
frame or pair identities. Rg, temperature, quality, physical, rescue, AI, and
publication semantics remain outside the change.

The repository `active-work.md` and `current-state.md` are intentionally not
allowlisted because they contain parallel uncommitted work; this acceptance
note and the independent lesson file are the durable record for this task.

Evidence so far:

- Focused trust and sequence regression: `22 passed, 1 warning`.
- Exact Guinier/sequence/series SAXS matrix: `33 passed, 1 warning`, exit code
  `0`.
- Ruff, compile, and `git diff --check` passed.
- Test-storage report and dry-run clean were non-destructive: `57` artifacts,
  `6` eligible candidates, `removed=0`; no `--apply` was run.
- The task verifier passed task/memory/Ruff/compile/type checks, then reported
  `288 passed, 2 failed, 3 warnings` in its shared quality gate. Both failures
  are existing NMR history-table expectations for English scientific-review
  labels while the parallel NMR implementation emits Chinese labels; no NMR
  files are part of this task.
