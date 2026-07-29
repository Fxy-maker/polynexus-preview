# Scientific Review native reacceptance

Status: automated acceptance passed; human scientific/release gates remain open.

This record will contain only current-checkout native route evidence for the
Scientific Review visibility checkpoint. It will not close IR vendor semantics,
NMR solid-C assignment/Xc policy, Joint conflict interpretation, or final
release approval.

## Evidence

The exact three-route selector passed in one fresh run:

```text
3 passed, 14 deselected in 31.78s, exit code 0
```

Selected cases were NMR solid-C, synthetic Joint, and synthetic IR mapping. The
command was:

```text
python -m pytest -q tests/test_native_gui_real_route_capture.py -k "solid_c or native_windows_gui_joint_synthetic_route or native_windows_gui_synthetic_ir_mapping_route" -vv
```

Capture root:
`D:\PolyNexus_scientific_review_native_reacceptance_20260730`

It contains 12 PNGs: Results, Gallery, History, and Editor for NMR solid-C,
synthetic Joint, and synthetic IR mapping. Each route also completed the
no-Origin PackageExporter fallback. Current Results captures visibly show
`Scientific review: Review required | reason=review_missing` for NMR solid-C
and IR mapping. The Joint synthetic fixture shows an accepted snapshot; that
is fixture provenance only and is not scientific conflict approval.

## Current-checkout recheck

A fresh rerun of the same selector passed:

```text
3 passed, 14 deselected in 35.98s, exit code 0
```

Command:

```text
python -m pytest -q tests/test_native_gui_real_route_capture.py -k "solid_c or native_windows_gui_joint_synthetic_route or native_windows_gui_synthetic_ir_mapping_route" -vv
```

Capture root: `D:\PolyNexus_native_recheck_current_20260730`.
The routes and PackageExporter fallback remained constructible. This does not
close IR vendor semantics, NMR solid-C assignment/Xc policy, Joint conflict
interpretation, or final release authorization.

## Limitations

The capture proves native route construction and display propagation only. IR
vendor coordinate/ROI semantics, NMR solid-C assignment/Xc policy, Joint
conflict interpretation, and final release authorization remain open.
