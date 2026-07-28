# Native all-mode route reacceptance

The current checkout was re-run through the native Windows Qt route harness
after the NMR solid-C assignment-column checkpoint. The matrix covered every
real DSC/SAXS/WAXS/IR/NMR mode, synthetic Joint, and synthetic IR mapping.

## Evidence

```text
QT_QPA_PLATFORM=windows
python -m pytest -q tests/test_native_gui_real_route_capture.py -vv
17 passed, 15 warnings in 346.78s (0:05:46), exit code 0
```

The D: capture root contains exactly 68 PNGs:
`D:\PolyNexus_native_all_routes_reacceptance_20260729`.
Each of the 17 cases produced Results, Gallery, History, and Editor images;
the Editor Export action exercised the PackageExporter fallback.

Representative current images inspected:

- `nmr_solid_c_editor.png`: spectrum remains editable, with ppm markers on
  the plot and the complete assignment list readable on the right.
- `joint_compare_results.png`: restored `PA6-A` identity and visible Joint
  diagnostic conflicts are aligned in the Results Workbench.
- `ir_mapping_editor.png`: synthetic mapping heatmap and editable object
  surface are constructible.

## Boundaries

The route evidence is automated and native, not a scientific or publication
approval. IR vendor-native mapping/ROI semantics, Joint conflict meaning,
solid-C assignment correctness, SAXS diagnostic interpretation, and final
human visual/scientific/release approval remain open.
