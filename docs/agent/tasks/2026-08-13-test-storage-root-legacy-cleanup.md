---
task_id: 2026-08-13-test-storage-root-legacy-cleanup
kind: daily
status: complete
date: 2026-08-13
title: Recognize and remove historical root-level test artifacts
---

# Recognize and remove historical root-level test artifacts

## Goal

Allow the storage tool to discover known historical pytest basetemp directories
when a drive root is explicitly supplied, without treating evidence, archives,
baselines, PA6 projects, or worktrees as disposable output.

## Non-goals

- Do not scan arbitrary drives unless the caller explicitly supplies
  `--legacy-root`.
- Do not delete protected artifacts or change the retention of managed runs.
- Do not bypass Windows ACL failures for zero-byte historical directories.

## Shared objects and entry points

- Objects: none; test-storage directories are local runtime artifacts.
- AI/Codex/CLI: updates the explicit `test_storage.py` maintenance CLI only.
- GUI: unchanged.
- Cross-entry rule: isolated local maintenance behavior; no project, run,
  chart, evidence package, or export contract changes.

## Affected boundaries

- `scripts/test_storage.py` legacy-root discovery and live-pytest protection.
- `tests/test_test_storage.py` regression coverage for historical root names.
- Explicit local maintenance under `D:\`; managed pytest retention remains
  unchanged.

## Acceptance criteria

- [x] Historical `PolyNexus-test-runs-*`, `PolyNexus_full_*`,
      `PolyNexus_joint_*`, `PolyNexus_dsc_*`, and `PolyNexus_nmr_*` roots are
      discoverable only from an explicit legacy root.
- [x] Known dated or specifically marked SAXS temporary roots are discoverable.
- [x] Evidence, archives, baselines, ordinary review directories, PA6 projects,
      and the canonical source worktree remain protected.
- [x] Shell text that merely contains `pytest` does not block legacy cleanup as
      though a pytest process were active.
- [x] The D-drive dry run identifies the historical SAXS basetemps and the
      apply run removes them while retaining recent managed output.

## Implementation plan

1. Reproduce the stale-output inventory with an explicit D-drive legacy root
   and identify why prior cleanup excluded those roots.
2. Add failing regression coverage for known historical root names and actual
   pytest-process detection.
3. Narrow the classifier to admit only known temporary naming patterns while
   preserving evidence, archive, baseline, and project protections.
4. Run focused tests, inspect the JSON dry run, then apply cleanup only to the
   reviewed eligible inventory.
5. Run the full storage-tool test file and structured changed-file verifier.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_test_storage.py
python scripts/test_storage.py report --legacy-root 'D:\' --older-than-hours 24 --json
python scripts/verify.py --task docs/agent/tasks/2026-08-13-test-storage-root-legacy-cleanup.md --changed --types
git diff --check
```

## Completion evidence

- Exact commands and outcomes: focused discovery/process tests passed before
  cleanup; the D-drive report identified 22,656,582,359 bytes of eligible
  historical output; `clean --apply` removed the eight large SAXS roots and
  left only 23 zero-byte ACL-denied legacy directories.
- Known limitations or follow-up: `WinError 5` prevents deletion of the
  zero-byte historical directories under the current token. They consume no
  material disk space and should only be removed by their ACL owner if visual
  cleanup is required.
- Pre-existing changes left untouched: `.superpowers/` and
  `tests/_tmp_phase3/`.
