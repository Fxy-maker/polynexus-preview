# Joint conflict provenance checkpoint

Date: 2026-07-25
Task: `docs/agent/tasks/2026-07-25-joint-conflict-provenance.md`

## Change

Joint validation rows now expose a JSON-safe `provenance` object containing
the check name and exact source runs. Each source records run ID, technique,
submodule, creation time, evidence status, evidence weight, and evidence
reasons; missing inputs are represented as unavailable with a visible reason.

Joint crystallinity, multiscale, and evidence-coverage FigureDefinition
recipes now carry the same batch-level `run_provenance`, so Gallery/Editor/
export consumers can trace figures back to the runs that supplied their data.
No tolerance, numeric value, severity, publication role, or conflict handling
was changed.

## Evidence

```powershell
$base = Join-Path $env:TEMP 'polynexus-joint-conflict-provenance-green'
$env:PYTEST_ADDOPTS = "--basetemp=$base"
python -m pytest tests/test_joint_hub_dataset.py tests/test_joint_figure_provider.py tests/test_nmr_joint_provenance_matrix.py -q
```

Result: `14 passed`. Focused Ruff, `py_compile`, and `git diff --check` also
passed.

## Still open

Real Joint data, restarted-GUI review, export-bundle manual inspection, and
the complete cross-module AI-off/failure/fallback matrix remain release gates.
