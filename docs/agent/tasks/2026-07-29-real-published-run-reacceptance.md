---
task_id: 2026-07-29-real-published-run-reacceptance
kind: real-data-lifecycle-recheck
status: completed
---

# Real published-run reacceptance

## Goal

Refresh current-checkout backend lifecycle evidence for every available real
published-run mode after the NMR solid-C assignment-column change.

## Non-goals

- Do not change analysis, thresholds, publication roles, real fixtures, or
  scientific interpretation.
- Do not treat backend lifecycle evidence as restarted-GUI or human release
  approval.
- Do not delete or migrate C-drive data or existing scratch directories.

## Affected boundaries

- `tests/test_real_published_run_walkthrough.py` and real fixture engines.
- FigureProductionPublisher, Manifest/Gallery, Editor/project export, and
  History restore contracts exercised by the walkthrough.
- This task's acceptance/task evidence only; no production code.

## Implementation plan

1. Run the complete 15-case real published-run walkthrough with a fresh D:
   pytest basetemp.
2. Record the exact pytest summary, warnings, and mode coverage.
3. Run the task-scoped verifier and diff checks.
4. Create an allowlisted documentation checkpoint while preserving the open
   scientific and human visual gates.

## Acceptance criteria

- [x] All 15 available real published-run cases pass with exit code 0.
- [x] DSC, SAXS, WAXS, IR, and all four NMR partitions are covered, including
      WAXS full-2D strain and IR temperature-2D.
- [x] Manifest/Gallery/Editor/export/History lifecycle evidence is refreshed.
- [x] Warnings and scientific diagnostic-only boundaries remain recorded.
- [x] Task card/memory, Pyright, quality/preprocessing, and whitespace checks
      pass when scoped without unrelated changed-file lint.
- [x] The prescribed `--changed` verifier is fully green on the current
      checkout; the earlier three Ruff `E741` findings were stale evidence from
      the pre-existing worktree state and are not present now.
- [x] Allowlisted documentation checkpoint is created after recording the
      unrelated-worktree limitation.

## Documentation checkpoint allowlist

- `docs/agent/tasks/2026-07-29-real-published-run-reacceptance.md`
- `docs/acceptance/2026-07-29-real-published-run-reacceptance.md`
- `docs/agent/memory/active-work.md`

The earlier changed-file verifier limitation is retained below as historical
evidence only; the current checkpoint includes no SAXS source changes.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_real_walkthrough_current_20260730'
python -m pytest -q tests/test_real_published_run_walkthrough.py -vv
15 passed, 11 warnings in 384.37s, exit code 0

python scripts/verify.py --task docs/agent/tasks/2026-07-29-real-published-run-reacceptance.md --changed --types
```

The earlier changed-file verifier attempt stopped before tests at Ruff `E741`
in the pre-existing SAXS files; that historical result is not attributed to
this task. The current scoped command completed with exit code `0`, including
task/memory checks, Ruff, compile, type baseline, quality `287`, preprocessing
`106`, and whitespace.

## Known limitations

This closes the automated real published-run lifecycle evidence only. Full /
boundary verification remains a tool-level timeout, while IR vendor mapping,
Joint conflict meaning, solid-C assignment correctness, restarted-GUI visual
review, and final release approval remain open.
