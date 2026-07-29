# SAXS export fallback dirty-provenance acceptance

Date: 2026-07-29

Task: `docs/agent/tasks/2026-07-29-saxs-export-fallback-dirty-provenance.md`

Status: automated acceptance complete; explicit checkpoint created

Fallback dirty q/raw export now succeeds with unchanged positions; invalid
counts are recorded under `diagnostics["invalid_numeric_values"]` and profile
status becomes `WARN` when the prior fallback status was `OK`/unknown.

Evidence:

- RED: `1 failed, 12 deselected`; the fallback export lacked conversion
  diagnostics before the change.
- GREEN: `2 passed, 11 deselected in 0.26s`, exit code `0`.
- Consumer matrix: `18 passed in 0.53s`, exit code `0`.
- Exact SAXS matrix: `533 passed, 6 warnings in 295.48s`, exit code `0`.
- Structured verifier: exit code `0`; quality `287`, preprocessing `106`,
  task/memory, Ruff, compile, type baseline, and whitespace passed.
- At task verification time, storage remained a dry-run with `282` artifacts,
  `40` eligible, `242` protected, and `0` removed. The later user-authorized
  storage apply is recorded separately and does not change this code evidence.

No scientific, rescue, AI, or publication behavior changed. The final
checkpoint hash is reported in the handoff; no push or merge was performed.
