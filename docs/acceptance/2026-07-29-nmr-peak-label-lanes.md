# NMR solid-C peak label lanes acceptance

The shared NMR FigureDefinition path now preserves complete peak assignments
and places labels in deterministic axes-relative lanes while keeping each label
x coordinate in ppm data space. Matplotlib renders the portable
`coordinate_space="xdata_yaxes"` object with its blended x-data/y-axes
transform. No peak fitting, ranking, assignment, or Xc behavior changed.

## Evidence

```text
python -m pytest -q tests/test_nmr_figure_provider.py tests/test_nmr_figure_document.py tests/test_figure_render_plan_core.py tests/test_nmr_joint_provenance_matrix.py
37 passed in 8.26s

python scripts/verify.py --task docs/agent/tasks/2026-07-29-nmr-peak-label-lanes.md --changed --types
task-check valid; Ruff passed; compile passed; quality-gate 287 passed;
preprocess_optimization 106 passed; whitespace passed; verifier exit 0
```

The end-to-end diagnostic render from FigureDefinition through document,
RenderPlan, and Matplotlib was inspected at:
`D:\PolyNexus_nmr_peak_label_lanes_capture_20260729\nmr_solid_c_spectrum.png`.
It contains seven complete assignments and the lane sequence
`0.96, 0.84, 0.72, 0.60, 0.48, 0.96, 0.84`.

## Limitations

This closes the display regression only. Solid-C assignment meaning, real
vendor coverage, restarted-GUI review across all modes, and final scientific /
release approval remain separate open gates in the full-software ledger.
