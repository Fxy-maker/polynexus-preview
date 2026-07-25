---
task_id: 2026-07-25-joint-conflict-provenance
kind: scientific-cross-module
status: completed
---

# Joint conflict provenance

## Goal

Attach stable source-run and evidence-weight provenance to Joint validation
conflicts and to the shared Joint figure recipes, without changing computed
values or silently resolving disagreements.

## Non-goals

- Change any cross-technique tolerance or physics formula.
- Promote low-confidence, diagnostic-only, or assignment-limited values.
- Add a new database schema or infer missing instrument provenance.
- Replace the existing Joint Workbench, Gallery, Editor, or export contracts.

## Affected boundaries

- `polynexus/core/joint/dataset.py`: validation-row source provenance.
- `polynexus/core/joint/figure_provider.py`: recipe-level run provenance.
- `tests/test_joint_hub_dataset.py` and `tests/test_joint_figure_provider.py`:
  regression coverage.

## Acceptance criteria

- [x] Each emitted Joint validation row has a JSON-safe provenance object with
  the relevant source run IDs, techniques, submodules, and evidence weights.
- [x] Joint crystallinity, multiscale, and coverage recipes preserve the same
  source-run provenance for every batch row.
- [x] Existing conflict severity, numeric details, publication roles, and
  Manifest output are unchanged.
- [x] Focused tests, task verifier, changed/type verifier, and diff checks pass.

## Implementation plan

1. [x] Add failing tests for conflict-row provenance and figure-recipe provenance.
2. [x] Implement small read-only provenance builders at the Joint dataset/provider
   boundaries and attach them to existing payloads.
3. [x] Run the Joint focused matrix and repository verifier, then checkpoint only
   the explicit task allowlist.

## Verification

```powershell
$base = Join-Path $env:TEMP 'polynexus-joint-conflict-provenance'
$env:PYTEST_ADDOPTS = "--basetemp=$base"
python -m pytest tests/test_joint_hub_dataset.py tests/test_joint_figure_provider.py tests/test_nmr_joint_provenance_matrix.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-25-joint-conflict-provenance.md --changed --types
python scripts/verify.py --changed --types
git diff --check
```

## Known limitations

Real-data and restarted-GUI review remain release gates. A missing upstream
run ID remains visibly empty rather than being synthesized.
