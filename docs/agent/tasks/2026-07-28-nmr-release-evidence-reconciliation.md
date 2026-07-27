---
task_id: 2026-07-28-nmr-release-evidence-reconciliation
kind: scientific-release-audit
status: completed
---

# NMR release evidence reconciliation

## Goal

Reconcile the four NMR partitions with the full-software release ledger using
fresh provider, provenance, evaluation, and real published-run evidence while
preserving assignment-gated solid-state semantics.

## Non-goals

- Do not change peak fitting, assignment thresholds, solvent handling, or
  solid-state Xc gates.
- Do not promote assignment-limited solid-C evidence to a paper-ready claim.
- Do not infer vendor semantics or claim restarted-GUI or human scientific
  acceptance from automated tests.

## Affected boundaries

- Existing NMR engine, FigureDefinition provider, evidence/eval bridge, and
  shared Manifest/Gallery/Editor/export/History consumers.
- `docs/acceptance/2026-07-28-nmr-release-evidence-reconciliation.md`.

## Implementation plan

1. Run the NMR provider/provenance/eval/profile matrix with an external
   basetemp.
2. Run the four-partition real published-run walkthrough independently and
   record its exact result.
3. Separate software lifecycle evidence from solid-C assignment and human
   release gates in the acceptance note.
4. Run the task-scoped verifier and create an allowlisted documentation
   checkpoint without mixing parallel SAXS work.

## Acceptance criteria

- [x] NMR provider, provenance, eval bridge, and profile matrix passes.
- [x] Liquid H/C and solid H/C real walkthroughs pass shared lifecycle,
  export provenance, and History restore.
- [x] Solid-C assignment-limited status remains explicitly provisional.
- [x] Remaining vendor, restarted-GUI, scientific, and release gates are
  listed separately.
- [x] Task-scoped verifier and whitespace checks pass for the checkpoint.

## Verification

```powershell
python -m pytest -q --basetemp=C:\Temp\polynexus_nmr_release_matrix tests/test_nmr_engine.py tests/test_nmr_figure_provider.py tests/test_nmr_joint_provenance_matrix.py tests/eval/test_runner_real_nmr.py tests/test_ir_nmr_joint_workbench_profiles.py
```

Observed: `26 passed in 106.03s`, exit code `0`.

```powershell
python -m pytest -q --basetemp=C:\Temp\polynexus_nmr_release_walkthrough tests/test_real_published_run_walkthrough.py -k nmr
```

Observed: `4 passed, 11 deselected in 125.71s`, exit code `0`.

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-28-nmr-release-evidence-reconciliation.md --changed --types
```

## Known limitations

The automated evidence closes the NMR software route only. Solid-C Xc remains
assignment-limited, real vendor evaluation coverage is not a substitute for
scientific review, and restarted canonical-GUI visual inspection plus human
release approval remain open.
