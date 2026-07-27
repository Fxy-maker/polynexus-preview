# NMR release evidence reconciliation

Date: 2026-07-28
Task: `docs/agent/tasks/2026-07-28-nmr-release-evidence-reconciliation.md`

## Mode evidence ledger

| Partition | Automated evidence | Release boundary |
| --- | --- | --- |
| `nmr.liquid_h` | Engine/eval/provider/provenance matrix; real published-run shared lifecycle; Main/diagnostic figures; Gallery/Editor/export/History restore | Vendor assignment semantics, restarted-GUI visual review, and scientific release approval |
| `nmr.liquid_c` | Same shared route with real liquid-C fixture; fit-quality warnings remain visible in result/evidence payloads | Assignment and fit-quality scientific review, restarted-GUI visual review, and release approval |
| `nmr.solid_h` | Same shared route with solid-H fixture; broad-line/fit diagnostics remain diagnostic | Solid-state phase/assignment scientific review, restarted-GUI visual review, and release approval |
| `nmr.solid_c` | Same shared route with solid-C fixture; assignment-gated crystallinity behavior remains in the result and figure contract | `Xc_assignment_status` remains assignment-limited/provisional; no strong Xc conclusion or final release approval |

## Fresh automated evidence

The focused current-head matrix was run with an external basetemp:

```powershell
python -m pytest -q --basetemp=C:\Temp\polynexus_nmr_release_matrix tests/test_nmr_engine.py tests/test_nmr_figure_provider.py tests/test_nmr_joint_provenance_matrix.py tests/eval/test_runner_real_nmr.py tests/test_ir_nmr_joint_workbench_profiles.py
```

Result: `26 passed in 106.03s`, exit code `0`.

The four real partitions were then run through the shared published-run
walkthrough independently:

```powershell
python -m pytest -q --basetemp=C:\Temp\polynexus_nmr_release_walkthrough tests/test_real_published_run_walkthrough.py -k nmr
```

Result: `4 passed, 11 deselected in 125.71s`, exit code `0`.

That walkthrough verifies the run ID, Manifest/Gallery entries, Editor working
and published revisions, export `metadata/runs` plus active pointer, and
History restore for all four partitions. It is software-route evidence, not a
vendor or human scientific sign-off.

## Explicit scientific boundary

Solid-state C assignment is intentionally conservative. The real fixture may
complete the software pipeline while `Xc_assignment_status` remains
assignment-limited; the system must keep that result provisional and must not
turn it into a strong Joint or publication conclusion. Fit-quality, solvent,
overlap, broad-line, and weak-assignment warnings remain review evidence.

Restarted native-GUI visual review, vendor-specific assignment interpretation,
real-data scientific review, and final release approval remain open in the
full-software ledger.

No NMR production code, assignment threshold, or scientific interpretation
changed in this reconciliation.
