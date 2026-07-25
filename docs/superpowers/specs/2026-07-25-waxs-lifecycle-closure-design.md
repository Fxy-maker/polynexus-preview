# WAXS Lifecycle Closure Design

## Goal

Prove the shared end-to-end lifecycle for WAXS static, temperature, and strain
modes, including the strain mode's editable 2D image-grid route.

## Scope and non-goals

The slice adds regression evidence over the existing WAXS providers and shared
Manifest/Gallery, project, export, and History contracts. It does not change
peak fitting, phase/size/orientation evidence, eligibility gates, or legacy
fallback semantics. It does not claim restarted-GUI visual or scientific
release sign-off.

## Design

Static and temperature use `FigureProjectService` for a working revision and
complete publication. Strain uses the existing `ReactiveFigureProjectService`
when the provider emits an `image_grid`; the test performs a worksheet edit,
saves the reactive revision, and publishes through its V2 renderer. All three
paths are then checked through `build_active_manifest_gallery_entries`, copied
through the export-context helpers, and restored through a Qt MainWindow history
record. Publication roles and run roots remain provider-owned.

## Failure and fallback boundary

Diagnostic-only entries remain diagnostic and are not promoted to Main. A
strain run without valid 2D scans must continue to use its existing 1D fallback;
the lifecycle regression covers the editable 2D branch and leaves fallback
policy assertions to the existing WAXS provider matrix. AI-off/failure/fallback
release review remains a shared cross-technique gate.

## Verification

Run the new WAXS lifecycle regression, the existing WAXS publication/2D/V2 and
history subsets, then the structured task verifier with an external pytest
basetemp.
