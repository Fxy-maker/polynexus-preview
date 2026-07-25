# IR three-mode vertical slice checkpoint

Date: 2026-07-25
Task: `docs/agent/tasks/2026-07-25-ir-three-mode-vertical-slice.md`

## Code boundary

IR standard, temperature-2D, and mapping/ROI definitions now use an explicit
publication-role contract:

| Mode | Main | SI | Diagnostic |
| --- | --- | --- | --- |
| Standard | first spectrum, crystallinity overview | later spectra, peak fit | experimental/computed comparison |
| Temperature-2D | spectral heatmap | band tracking, band indices | synchronous/asynchronous 2D-COS |
| Mapping/ROI | scalar map | ROI spectra | invalid-pixel map |

The mapping branch still accepts only the validated `IRMappingResult`; its
provenance and invalid-pixel mask remain visible in the generated definitions.
The shared FigurePipeline keeps a failed definition as `generation_failed`
while publishing ready siblings.

## Evidence

Focused command:

```powershell
$base = Join-Path $env:TEMP 'polynexus-ir-three-mode-focused'
$env:PYTEST_ADDOPTS = "--basetemp=$base"
python -m pytest tests/test_ir_complete_figure_provider.py tests/test_ir_figure_provider.py tests/test_ir_mapping.py tests/test_run_figure_manifest.py -q
```

Result: `26 passed`.

Task-scoped verifier result: passed. It included Ruff, compile, memory check,
quality gate (`282 passed`), and preprocessing gate (`103 passed`).

The new role test was first run before the provider change and failed because
all standard figures inherited the default `si` role. After the minimal
provider change, the same focused provider matrix passed. `git diff --check`
also passed.

## Still open

- Vendor-specific mapping reader and input semantics are intentionally not
  implemented.
- Real/Golden IR fixtures, AI-off/failure/fallback scientific review, export
  bundle inspection, and restarted-GUI visual review remain release gates.
- This checkpoint does not claim the full IR mode or full-software goal is
  complete.
