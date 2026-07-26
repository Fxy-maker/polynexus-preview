# NMR plot sentinel compatibility acceptance

`NMREngine.plot()` now checks that every result exposes the typed
`parameters` and `peaks` payloads before invoking the legacy compatibility CSV
writers. Shared Manifest publication still runs for sentinel-marked tests,
and real NMR result collections retain the existing parameter/peak exports.

## Verification evidence

```text
python -m pytest --basetemp=C:\Temp\PolyNexus_nmr_plot_cutover tests/test_engine_figure_production_cutover.py -q
5 passed in 1.77s

python -m pytest --basetemp=C:\Temp\PolyNexus_nmr_engine_final tests/test_nmr_engine.py -q
18 passed in 79.10s

python -m pytest --basetemp=C:\Temp\PolyNexus_nmr_figures_final tests/test_nmr_figure_document.py tests/test_nmr_figure_provider.py tests/test_nmr_joint_provenance_matrix.py tests/test_nmr_lifecycle_closure.py -q
14 passed in 253.00s

python -m pytest --basetemp=C:\Temp\PolyNexus_nmr_preprocess_profiles_final tests/test_preprocess_nmr_adapter.py tests/test_ir_nmr_joint_workbench_profiles.py -q
5 passed in 0.26s
```

The compatibility guard does not constitute real-vendor or restarted-GUI
scientific acceptance; those remain in the full-software ledger.
