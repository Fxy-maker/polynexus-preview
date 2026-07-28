# NMR solid-C assignment column acceptance

Dense solid-C spectra now keep the scientific plot readable while preserving
complete assignment text. Each retained peak keeps its vertical line and ppm
marker; each non-empty assignment is also emitted as a deterministic row in a
right-side axes-coordinate column in the same FigureDefinition.

## Evidence

```text
python -m pytest -q tests/test_nmr_figure_provider.py tests/test_nmr_figure_document.py tests/test_figure_render_plan_core.py tests/test_nmr_joint_provenance_matrix.py
37 passed in 8.85s

python -m pytest -q tests/test_native_gui_real_route_capture.py -k 'nmr.solid_c' -vv
1 passed, 16 deselected in 21.57s, exit code 0
```

Fresh native captures are under
`D:\PolyNexus_native_nmr_assignment_column_20260729`. The inspected Editor
image is `nmr_solid_c_editor.png`; it shows the complete assignment list beside
the spectrum and the existing editable object surface. The route also invoked
the PackageExporter fallback.

## Boundaries

No peak fitting, ranking, assignment, Xc, validation, or publication semantics
changed. The assignment column is display/provenance presentation only. Vendor
assignment correctness, restarted-GUI review across all modes, and final
scientific/release approval remain open gates.
