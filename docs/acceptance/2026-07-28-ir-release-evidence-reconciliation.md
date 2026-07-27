# IR release evidence reconciliation

Date: 2026-07-28
Task: `docs/agent/tasks/2026-07-28-ir-release-evidence-reconciliation.md`

This note separates current automated software evidence from the release gates
that require vendor knowledge, a restarted native GUI, or an authorized
scientific reviewer.

| Mode | Automated software evidence | Current release boundary |
| --- | --- | --- |
| `ir.standard` | Explicit Main/SI/diagnostic roles; FigureDefinition validation; Manifest sibling-failure visibility; real published-run walkthrough; Gallery/Editor/export/History lifecycle | Real scientific band meaning, native-GUI visual review, and release approval |
| `ir.temperature_2d` | Heatmap Main, tracking/index SI, 2D-COS diagnostic roles; bounded correlation data; real published-run walkthrough; shared lifecycle | Condition/sequence scientific interpretation, native-GUI visual review, and release approval |
| `ir.mapping` | Typed map/coordinate/mask/ROI handoff; Main map, SI ROI spectra, diagnostic invalid-pixel figure; provenance and masked-cell evidence; synthetic lifecycle | Vendor file reader, coordinate convention, ROI semantics, real mapping fixture, native-GUI visual review, and release approval |

## Fresh automated evidence

The focused current-head matrix was run with an external basetemp:

```powershell
python -m pytest -q --basetemp=C:\Temp\polynexus_ir_release_matrix tests/test_ir_lifecycle_closure.py tests/test_ir_complete_figure_provider.py tests/test_ir_figure_provider.py tests/test_ir_temperature.py tests/test_ir_mapping.py tests/test_ir_nmr_joint_workbench_profiles.py
```

Result: `31 passed in 37.55s`, exit code `0`.

The real published-run walkthrough for IR standard and temperature-2D was
rerun separately:

```powershell
python -m pytest -q --basetemp=D:\PolyNexus\PolyNexusPolyNexusPolyNexus.pytest_tmp_walkthrough_ir_verified tests/test_real_published_run_walkthrough.py -k ir
```

Result: `2 passed, 13 deselected in 84.54s`, exit code `0`.

These results prove the shared software route and conservative evidence roles;
they do not prove vendor semantics or human visual/scientific acceptance.

## Verification boundary

The task-scoped changed/type verifier passed with exit code `0`; it checked the
task and memory contracts, the current tracked changed-file allowlist, Ruff,
compile/type baseline, quality gate (`283`), preprocessing gate (`106`), and
whitespace. Unrelated untracked SAXS figure-provider work was intentionally
outside this checkpoint's allowlist and remains owned by its parallel task.

No production IR code, scientific threshold, or vendor interpretation changed
in this reconciliation.
