---
task_id: 2026-07-28-ir-release-evidence-reconciliation
kind: scientific-release-audit
status: completed
---

# IR release evidence reconciliation

## Goal

Reconcile the current IR three-mode implementation with the full-software
release ledger without promoting provider or synthetic evidence to vendor,
visual, or scientific sign-off.

## Non-goals

- Do not infer an instrument-specific mapping reader, coordinate convention, or
  band meaning.
- Do not change IR analysis, thresholds, publication roles, or fallback
  behavior.
- Do not claim restarted-GUI visual acceptance or human scientific release
  approval from offscreen tests.

## Affected boundaries

- Existing IR FigureDefinition providers and typed mapping handoff.
- Existing Manifest/Gallery/Editor/export/History lifecycle tests.
- `docs/acceptance/2026-07-28-ir-release-evidence-reconciliation.md`.

## Implementation plan

1. Run the focused IR provider, mapping, lifecycle, and real walkthrough
   matrices with external basetemps.
2. Record the automated boundary and the remaining vendor, visual, and
   scientific gates in the acceptance note without changing production code.
3. Run the task-scoped verifier and retain any unrelated-worktree blocker as
   an explicit limitation.

## Acceptance criteria

- [x] The focused IR provider/mapping/lifecycle matrix passes with an external
  pytest basetemp.
- [x] Real standard and temperature-2D published-run walkthroughs pass through
  shared lifecycle, export provenance, and History restore.
- [x] The evidence table distinguishes automated closure from vendor semantics,
  live visual review, and scientific release approval.
- [x] The task-scoped changed/type verifier passes for this checkpoint's
  explicit tracked allowlist; unrelated untracked SAXS work remains outside
  the checkpoint.
- [ ] Human restarted-GUI and vendor/scientific review are completed by an
  authorized reviewer.

## Verification

```powershell
python -m pytest -q --basetemp=C:\Temp\polynexus_ir_release_matrix tests/test_ir_lifecycle_closure.py tests/test_ir_complete_figure_provider.py tests/test_ir_figure_provider.py tests/test_ir_temperature.py tests/test_ir_mapping.py tests/test_ir_nmr_joint_workbench_profiles.py
```

Observed: `31 passed in 37.55s`, exit code `0`.

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-28-ir-release-evidence-reconciliation.md --changed --types
```

```powershell
python -m pytest -q --basetemp=D:\PolyNexus\PolyNexusPolyNexusPolyNexus.pytest_tmp_walkthrough_ir_verified tests/test_real_published_run_walkthrough.py -k ir
```

Observed: `2 passed, 13 deselected in 84.54s`, exit code `0`.

Task-scoped verifier result: passed with exit code `0`; it checked task/memory,
the current tracked changed-file allowlist, Ruff, compile/type baseline,
quality gate (`283`), preprocessing gate (`106`), and whitespace. Unrelated
untracked SAXS edits were intentionally outside this checkpoint's allowlist.

## Known limitations

The automated evidence closes the IR software lifecycle boundary only. A real
vendor mapping reader, vendor-native ROI semantics, restarted canonical-GUI
pixel review, and human scientific/release approval remain open.
