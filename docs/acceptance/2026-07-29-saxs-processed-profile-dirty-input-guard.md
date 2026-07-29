# SAXS ProcessedProfile dirty-input guard acceptance

Date: 2026-07-29

Task: `docs/agent/tasks/2026-07-29-saxs-processed-profile-dirty-input-guard.md`
Status: automated acceptance complete; explicit checkpoint created

The projection now converts each numeric layer element independently. Failed
conversions remain `NaN` in place, are counted under
`diagnostics["invalid_numeric_values"]`, and set `quality_status` to `WARN`.
Clean profiles remain `OK`; caller-owned inputs and all analysis behavior are
unchanged.

## Evidence

- RED: `2 failed, 3 passed`; failures were the expected dirty whole-array
  conversion exceptions.
- GREEN: `5 passed in 0.13s`.
- Structured verification: exit code `0`; quality `287 passed`, preprocessing
  `106 passed`, task/memory, Ruff, compile, type baseline, and whitespace all
  passed.
- Exact SAXS matrix: timeout after `184s` with no pytest final summary, so no
  SAXS matrix pass is asserted.
- Test storage: report-only dry-run with `562` artifacts, `42` eligible, `520`
  protected, and `0` removed. No `--apply` was executed.

No scientific threshold, analysis route, AI/rescue path, Figure/Manifest/Export
contract, or publication decision changed. The explicit allowlist checkpoint
was created; its final commit hash is reported in the handoff. No push or merge
was performed.
