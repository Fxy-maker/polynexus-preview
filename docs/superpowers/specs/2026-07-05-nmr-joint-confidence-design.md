# ssNMR and Joint Confidence Correction Design

## Goal

Add the two missing confidence-correction workstreams for PolyNexus:

- Stage J: ssNMR confidence correction.
- Stage K: Joint cross-technique confidence correction.

The implementation order is intentionally J first, K second. Joint analysis consumes single-technique evidence, so NMR needs a structured evidence contract before Joint can make reliable cross-technique claims involving NMR.

## Scope

Stage J covers NMR as a single-technique chain:

- Input and partition trust: liquid/solid, 1H/13C, JEOL/table/FID source.
- Signal evidence: point count, ppm range, polarity, noise, SNR.
- Peak evidence: peak count, line width, deconvolution fit quality, residual hints.
- Assignment evidence: generic region assignment, polymer DB assignment, solvent risk.
- Solid 13C crystallinity evidence: whether `Xc_NMR` is usable or only assignment-limited.
- Optional computed-shift evidence: match count and delta ppm when DFT/reference shifts exist.

Stage K covers Joint as a cross-technique chain:

- Dataset row completeness and condition alignment.
- Crystallinity consistency across DSC/WAXS/SAXS/IR/NMR.
- Tm versus SAXS long-period/lc checks.
- SAXS-WAXS multiscale consistency.
- IR/NMR calibration and assignment status before treating their indices as crystallinity.
- Export and AI context that explain conflicts without replacing user judgment.

## Architecture

The implementation should follow existing patterns:

- Extend `polynexus/core/analysis_evidence.py` for NMR evidence sections, constraints, symptoms, and summary text.
- Add focused NMR tests in `tests/test_analysis_evidence.py` and, only where needed, `tests/test_nmr_engine.py`.
- Extend `polynexus/core/joint/dataset.py` for Joint confidence context and row-level evidence, keeping current hub/report APIs backward compatible.
- Add Joint tests in `tests/test_joint_hub_dataset.py` and GUI-facing tests only if user-visible fields change.

No large GUI redesign is needed for the first pass. Existing Results, Joint Hub, work memory, and export summary paths can consume richer evidence dictionaries.

## Deliverables

Documentation deliverables:

- `方案/PolyNexus 番外阶段J ssNMR可信度矫正清单.md`
- `方案/PolyNexus 番外阶段J-T1 ssNMR当前基线台账.md`
- `方案/PolyNexus 番外阶段K Joint可信度矫正清单.md`
- `方案/PolyNexus 番外阶段K-T1 Joint当前基线台账.md`

Implementation deliverables:

- NMR evidence fields and constraints.
- NMR symptom/action bridge for low SNR, broad linewidth, weak assignment, fit instability, and unsupported Xc.
- Joint confidence context fields and issue families.
- Tests that demonstrate conservative behavior for low-confidence NMR and cross-tech conflicts.

## Acceptance

The work is complete when:

- NMR output can explain why a spectrum is trustworthy, provisional, or unusable without opening the figure.
- Solid 13C `Xc_NMR` is not promoted unless crystalline/amorphous assignment support exists.
- Joint reports distinguish single-technique local quality from cross-technique consistency.
- AI tuning context receives structured NMR and Joint confidence signals.
- Targeted tests pass and the work is committed in small, readable commits.
