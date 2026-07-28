---
task_id: 2026-07-29-test-storage-dry-run-audit
kind: release-verification-audit
status: completed
---

# Test-storage dry-run audit

## Goal

Run the AGENTS.md storage report after tests are idle and classify the current
managed/legacy artifacts without deleting or migrating anything.

## Non-goals

- Do not pass `--apply`.
- Do not remove protected, active, tracked, source, real-data, or scratch paths.
- Do not alter repository files or test fixtures.

## Affected boundaries

- `scripts/test_storage.py report --json`
- Managed D: test root and discovered legacy C: test directories.

## Implementation plan

1. Confirm no Python/pytest process is active.
2. Run the report in dry-run mode with captured JSON output.
3. Summarize total and C:-drive eligible/protected counts and bytes.
4. Leave all artifacts untouched and record that apply authorization is absent.

## Acceptance criteria

- [x] The report completes with JSON output and no stderr.
- [x] Dry-run mode and removed count are explicit.
- [x] C: legacy counts are separated from total counts.
- [x] No deletion or migration is performed.

## Verification

```powershell
python scripts/test_storage.py report --json
# mode=dry-run; artifacts=556; eligible=236; protected=320;
# eligible_bytes=90330056419; removed=0
# C: artifacts=306; eligible=212; protected=94;
# C: eligible_bytes=76691802567; C: removed=0

python scripts/verify.py --task docs/agent/tasks/2026-07-29-test-storage-dry-run-audit.md --changed --types
git diff --check
```

Captured report: `D:\PolyNexus_storage_audit_20260729_run2.json`; stderr was
empty. Actual deletion still requires an explicit user-authorized `--apply`.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-29-test-storage-dry-run-audit.md`
- `docs/acceptance/2026-07-29-test-storage-dry-run-audit.md`
- `docs/agent/memory/active-work.md`
