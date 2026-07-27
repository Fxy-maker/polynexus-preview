# SAXS real data and Workbench acceptance

## Goal

Close the automated acceptance slice for the SAXS static, temperature, and
strain modes after the quality-evidence and export-provenance checkpoints.

## Non-goals

- Do not change SAXS algorithms, quality thresholds, evidence states, or
  publication roles.
- Do not modify the real datasets or repository-generated outputs.
- Do not auto-accept scientific trends, execute AI rescue candidates, or
  replace human scientific review.

## Affected boundaries

- Real fixture replay through `SAXSEngine.run_pipeline`.
- `SAXSEngine.export_bundle` and `quality_evidence.json` audit output.
- SAXS Results Workbench profile and figure-link contracts.
- `scripts/launch_gui.py --diagnose` source/worktree identity boundary.
- Durable acceptance and agent-memory records only; diagnostic output is kept
  outside the repository under `C:\Temp`.

## Implementation plan

1. Replay the real static, temperature, and strain SAXS lifecycle using an
   external temporary output root.
2. Export each real result and assert mode-scoped quality evidence plus bundle
   manifest registration.
3. Run the SAXS Workbench contract suites and the launcher source-identity
   diagnostic.
4. Record automated evidence and leave visual/scientific sign-off as an
   explicit human gate.

## Acceptance criteria

- [x] Real static, temperature, and strain SAXS lifecycle tests pass without
  writing to the real fixture directories.
- [x] Real static, temperature, and strain runs export an `ok` SAXS bundle and
  register `quality_evidence.json` in the bundle manifest.
- [x] Static evidence contains quality, Guinier, and metric evidence; the
  temperature series contains sequence Guinier evidence; absent evidence is
  not fabricated or promoted.
- [x] SAXS Workbench profile and figure-link regression tests pass for all
  three modes.
- [x] Restart-boundary diagnosis resolves `D:\PolyNexus`, branch
  `codex/origin-editor-usable-controls`, commit `41588a0`, and the package
  under that same worktree.
- [ ] A human reviews the rendered GUI and real-data scientific meaning before
  any release or automatic publication claim.

## Verification evidence (2026-07-27)

- `python -m pytest tests/test_real_published_run_walkthrough.py -k 'saxs' -q`:
  **3 passed, 12 deselected**.
- `python -m pytest tests/test_saxs_workbench_figure_contracts.py tests/test_results_workbench_profiles.py -q`:
  **9 passed**.
- Real replay/export diagnostic under
  `C:\Temp\PolyNexus_saxs_stage9_real_bundle`: static, temperature, and
  strain each returned `bundle_status=ok`; each manifest pointed to
  `quality_evidence.json`. The temperature run retained its existing
  validation errors and did not get promoted.
- `python scripts/launch_gui.py --diagnose`: resolved source root
  `D:\PolyNexus`, package `D:\PolyNexus\polynexus\__init__.py`, and commit
  `41588a0`.

## Known limitations

The automated checks do not constitute scientific sign-off. A restarted GUI
visual inspection and expert review of the real temperature/strain trends,
quality downgrades, and publication roles remain required. The temperature
fixture currently reports validation errors; this is preserved as a visible
gate rather than hidden by export.

## Verification

The focused and structured checks are:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest tests/test_real_published_run_walkthrough.py -k 'saxs' -q
python -m pytest tests/test_saxs_workbench_figure_contracts.py tests/test_results_workbench_profiles.py -q
python scripts/launch_gui.py --diagnose
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-real-workbench-acceptance.md --changed --types
```

## Changed-file allowlist

- this task card
- `docs/superpowers/specs/2026-07-27-saxs-real-workbench-acceptance-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-real-workbench-acceptance.md`
- `docs/acceptance/2026-07-27-saxs-real-workbench-acceptance.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
