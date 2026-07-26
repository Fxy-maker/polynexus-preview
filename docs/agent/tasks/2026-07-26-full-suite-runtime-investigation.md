# Full-suite runtime and editor regression investigation

## Goal

Close the remaining automated release-verification gap without masking test
failures: identify whether the full verifier timeout is a true hang or an
accumulated runtime issue, and repair regressions exposed by the first Qt
shard.

## Scope

- Full-suite pytest runtime profiling by independent test-file shards.
- `ChartEditor` mixin ownership and compact inspector layout regressions.
- Verifier/boundary behavior only when runtime evidence demonstrates a tooling
  problem.

## Non-goals

- No deletion of existing scratch or regression data.
- No changes to scientific semantics, publication roles, or vendor mappings.
- No claim of release approval before full/boundary verification and human
  acceptance gates are complete.

## Acceptance criteria

- [x] The reproduced ChartEditor and figure-overlay failures have focused
  red/green evidence.
- [x] Runtime shards record pass/fail status and elapsed time with external
  basetemp directories.
- [x] Any verifier change has a regression test and an explicit rationale.
- [x] `python scripts/verify.py --task docs/agent/tasks/2026-07-26-full-suite-runtime-investigation.md --changed --types`
  passes before checkpoint.
- [x] Durable audit and memory notes state remaining release limitations.

## Affected boundaries

- `ChartEditor` mixin ownership, responsive inspector layout, and live text
  selection overlays.
- Shared figure render adapter coordinate transforms and fallback geometry.
- Pytest logging isolation for GUI-created global logger state.
- `scripts/verify.py` runtime evidence and release audit documentation.

## Implementation plan

1. Reproduce the first failing Qt shard and trace each failure to its owning
   mixin, layout constraint, or renderer coordinate contract.
2. Add the smallest production/test-bootstrap fixes and preserve focused
   regression coverage for normal and fallback paths.
3. Run every test file in independent external-basetemp shards, recording
   elapsed time and failures without deleting existing scratch data.
4. Run the task-scoped verifier and the full boundary verifier, then update
   audit and memory status with any remaining human acceptance gates.

## Initial evidence

The Qt chart shard collected and ran 511 tests in 67.83 seconds: 509 passed,
with failures in `test_chart_editor_annotation_controls_mixin.py` and
`test_chart_editor_workflow.py`. A direct widget-tree diagnostic showed the
inspector page minimum widths were 266, 366, 730, and 318 px for viewports of
260, 260, 274, and 274 px; making nested row containers and interactive
controls width-ignored reduced them to 224, 188, 200, and 176 px.

## Verification

The required verification command is:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-26-full-suite-runtime-investigation.md --changed --types
```

The release verification command is:

```powershell
python scripts/verify.py --changed --types --full --boundary
```

| Check | Result |
|---|---|
| Chart/Qt shard before fix | 509 passed, 2 failed, 67.83 s |
| Chart/Qt shard after fix | 511 passed, 67.49 s |
| Core/service shard after fix | 724 passed, 85.53 s |
| Technique/eval shard | 450 passed, 522.67 s |
| Figure/export shard after fix | 481 passed, 27.38 s |
| Remaining shard | 196 passed, 79.05 s |
| Task verifier | Passed; quality 282, preprocessing 103 |
| Full boundary verifier | Passed; 2587 passed, 8 warnings, 1042.86 s |

The full command completed with exit code 0:

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_full_boundary_after_runtime_fixes'
python scripts/verify.py --task docs/agent/tasks/2026-07-26-full-suite-runtime-investigation.md --changed --types --full --boundary
```

The long runtime is expected: NMR real lifecycle tests dominate the suite.
The remaining release decision is still gated by restarted-GUI visual review,
publication-role review, and human scientific confirmation.

## Changed-file allowlist

- `polynexus/gui/widgets/chart_editor.py`
- `polynexus/gui/figure_render_adapter.py`
- `polynexus/gui/widgets/chart_editor_generated_preview_mixin.py`
- `polynexus/gui/widgets/chart_editor_edit_session_mixin.py`
- `polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py`
- `tests/conftest.py`
- `tests/test_chart_editor_annotation_controls_mixin.py`
- `tests/test_chart_editor_workflow.py`
- this task card
- release audit/memory files only when new evidence changes their status
