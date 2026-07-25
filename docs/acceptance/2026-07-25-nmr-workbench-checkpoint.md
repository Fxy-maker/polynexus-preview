# NMR Workbench checkpoint

## Delivered

Liquid H/C and solid H/C NMR modes are registered in the typed Results
Workbench profile system with distinct review narratives. The existing NMR
analysis result carries peak, assignment, linewidth, SNR, fit, solvent, and
assignment-limited crystallinity fields. The shared NMR FigureDefinition
provider publishes spectrum, deconvolution, comparison, region-integral, and
assignment-gated crystallinity figures; `NMREngine.plot()` also restores the
legacy parameters/peaks CSV exports under the same run root.

The solid-state crystallinity figure remains evidence-gated by the existing
`Xc_assignment_status`; an unsupported or assignment-limited Xc is not promoted
to a strong Joint conclusion by this checkpoint.

## Verification evidence

- NMR engine, provider, legacy document compatibility, NMR preprocessing
  adapter, and all four profile registrations: 29 passed.
- The preceding IR/NMR/Joint profile/lifecycle matrix: 55 passed.
- Changed/type verifier and shared quality gates remain green at the latest
  Joint checkpoint: quality gate 282, preprocessing gate 103.

## Remaining acceptance boundary

- Four-partition real-data and restarted-GUI visual review is pending.
- NMR export bundle, Gallery/Editor routing, AI-off/failure/fallback, and
  history/provenance walkthroughs need a dedicated end-to-end matrix.
- This is a Workbench/Figure lifecycle checkpoint, not a complete NMR vertical
  release claim.

## Evidence persistence follow-up (2026-07-25)

The ordinary `NMREngine.analyze()` path now attaches the shared
`AnalysisEvidence` payload to `AnalysisResult`, including peak count, signal
quality, assignment evidence, and assignment-gated Xc status. This is the
payload consumed by the existing GUI `AnalysisRunPersistenceContext`, so it is
available to SampleDB and History without a technique-specific GUI branch.

The focused regression passed, and the real reader/core matrix remains green
(`17 passed`). This closes the code-level evidence handoff only; four-partition
real GUI/export/restart review and scientific acceptance remain open.

## Real-engine smoke evidence (2026-07-25)

The existing repository fixtures were run through `NMREngine.run_pipeline()`
to external output roots, without modifying the fixtures:

- liquid 1H: validation passed, 10 peaks, 4 published figures;
- liquid 13C: validation passed with one fit-quality warning, 18 peaks, 4
  published figures;
- solid 1H: validation passed with seven fit-quality warnings across seven
  spectra, 28 published figures;
- solid 13C: validation passed with fit-quality and assignment warnings,
  6--18 peaks across seven spectra, assignment-limited Xc, and 28 published
  figures.

Each run emitted `AnalysisEvidence` with signal, peak, assignment, and
structure sections and an active Manifest run. This is real engine/core and
publication evidence; GUI restart, Editor/export inspection, and human review
remain open.
