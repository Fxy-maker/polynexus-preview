# Fresh native focused visual recheck

Status: automated native route and capture evidence passed; human visual and
scientific release gates remain open.

## Evidence

| Route | Result | Fresh capture directory | Boundary kept open |
|---|---:|---|---|
| Joint synthetic compare | `1 passed, 16 deselected` | `D:\PolyNexus_native_joint_recheck_20260730` | conflict interpretation and release approval |
| IR mapping synthetic | `1 passed, 16 deselected` | `D:\PolyNexus_native_ir_mapping_recheck_20260730` | vendor format, coordinate convention, ROI semantics |
| NMR solid-C | `1 passed, 16 deselected` | `D:\PolyNexus_native_nmr_solid_c_recheck_20260730` | assignment correctness, label policy, scientific approval |

The exact runtimes were 8.16s, 7.07s, and 19.45s respectively. The routes
were run from the current checkout with `QT_QPA_PLATFORM=windows` and D:
basetemp directories.

## Visual review record

- Joint Results is internally consistent in the fresh capture: `PA6-A` appears
  in the project label, breadcrumb, Current task source, and Review focus. The
  visible diagnostic errors/warnings are retained rather than hidden.
- IR mapping Results clearly identifies a structural mapping payload and keeps
  the `Not confirmed yet` review boundary. This is structural GUI evidence, not
  vendor-semantics acceptance.
- NMR solid-C Results and Editor are constructible and editable. The Editor
  exposes assigned and unassigned peak labels; their scientific correctness and
  acceptable density still require an expert review.

## Remaining gates

This note closes no human gate. Restarted-GUI all-mode visual approval, IR
vendor/ROI semantics, NMR solid-C assignment interpretation, Joint conflict
interpretation, and final scientific/release approval remain open.
