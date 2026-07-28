---
task_id: 2026-07-28-test-storage-legacy-roots
kind: repository-maintenance
status: completed
---

# Manage legacy test storage roots

## Goal

Bring historical Windows `TempPolyNexus*` test-output directories into the
existing dry-run-first storage report and cleanup flow so stale pytest output
does not silently consume the system drive.

## Non-goals

- Do not delete system files, Codex data, user documents, worktrees, or real
  regression datasets.
- Do not change pytest's new external D-drive basetemp allocation.
- Do not auto-push, merge, or deploy.

## Affected boundaries

- `scripts/test_storage.py`: legacy-root discovery, configuration, and active
  pytest protection.
- `tests/test_test_storage.py`: discovery and safety regressions.
- `README.md` and `AGENTS.md`: operator contract.
- `docs/superpowers/plans/2026-07-28-test-storage-legacy-roots.md`: execution
  plan and evidence.

## Implementation plan

1. Define exact legacy-root patterns and explicit root overrides.
2. Protect externally discovered roots while pytest is active and keep cleanup
   dry-run by default.
3. Add focused discovery/protection regressions and run the task verifier.
4. Create one explicit allowlist checkpoint without touching unrelated work.

## Acceptance criteria

- [x] The system drive's exact historical test-output naming patterns are
  discoverable without scanning arbitrary user directories.
- [x] `POLYNEXUS_LEGACY_TEST_ROOTS` and `--legacy-root` support explicit roots.
- [x] Externally discovered legacy directories remain protected while pytest
  is active, and cleanup remains dry-run by default.
- [x] Focused tests and `python scripts/verify.py --changed --types` pass.
- [x] Any cleanup uses the explicit `--apply` switch and the 24-hour cooldown.

## Verification

```powershell
python -m pytest -q tests/test_test_storage.py
python scripts/test_storage.py clean --older-than-hours 24 --json
python scripts/verify.py --changed --types
git diff --check
```

Focused evidence: `10 passed` on 2026-07-29. Ruff, compile, whitespace, task
card, and the changed/type verifier passed; the quality gate reported `283
passed` and the preprocessing gate reported `106 passed`.

## Apply follow-up (2026-07-29)

After explicit user authorization, a fresh `--apply` run returned exit code
`0`: it scanned `445` artifacts, removed `4` eligible directories, and
released approximately `6.87 GiB`. The final report contains `441` artifacts
(`154.15 GiB`); all are younger than the 24-hour retention window and
`eligible=0`. The final drive check showed approximately `105.28 GB` free on
C: and `191.42 GB` free on D:. No source, real dataset, worktree, or pytest
process was targeted.

## Known limitations

The automatic legacy scan is intentionally restricted to exact historical
test-output prefixes. It does not infer whether unrelated large directories
are disposable. Remaining artifacts stay protected until they exceed the
24-hour retention window and a later cleanup is explicitly authorized.
