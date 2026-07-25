# NMR Lifecycle Closure Design

## Goal

Prove the complete automated lifecycle for NMR liquid/solid 1H/13C partitions
using the repository's real NMR fixtures and the existing shared services.

## Scope and non-goals

Run each registered submodule through `NMREngine.run_pipeline`, then verify
evidence, active Manifest/Gallery, editor working save and publish, export
provenance, and History restore. Read the real fixtures only; write outputs to
pytest temporary roots. Do not modify peak fitting, assignment gates, or
assignment-limited solid-state Xc semantics.

## Design

The test parameterizes four source paths: liquid H, liquid C, solid H, and
solid C. Each engine run must emit a shared `AnalysisEvidence` payload and a
manifest-backed Gallery with Main and diagnostic roles. The first Main figure
is saved and republished with `FigureProjectService`, then the run tree and
active pointer are copied into an export bundle. A Qt MainWindow history record
restores the same run and checks the Gallery and submodule.

Existing assignment-limited solid 13C evidence remains visible and provisional;
the test never promotes it to a strong scientific conclusion.

## Verification

Run the real four-partition lifecycle test with the existing NMR engine/provider
and provenance/history suites, then the structured verifier with an external
pytest basetemp.
