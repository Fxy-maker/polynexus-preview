# Task: SAXS EDF metadata and pixel-quality classification

**Status:** in progress

## Goal

Extend the existing SAXS EDF quality report so the program shows which detector
metadata is present, classifies processed-image sentinel values, and avoids
misreading `Saturation=0`, while preserving conservative scientific gates.

## Non-goals

- No new `DetectorMetadata` DTO.
- No automatic calibration approval from EDF header fields.
- No new publication, rescue, or quality-level promotion rule.
- No inference of a mask from image statistics.
- No changes to real EDF files or generated outputs.
- No refactor of the unused duplicate reader under `polynexus/readers/`.

## Affected boundaries

- EDF normalization: `polynexus/core/saxs_engine/io.py`
- Detector report and pixel classification: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Header/mask extraction and report construction: `polynexus/core/saxs_engine/preprocess.py`
- Existing SAXS raw-detector transport: `polynexus/core/saxs.py`
- Focused regressions: `tests/test_saxs_raw_detector_quality_transport.py` and a new real-style EDF fixture test module if required

## Acceptance criteria

- [x] The supplied 4-frame `610` sequence can be loaded and each frame retains
  independent header-backed detector metadata and quality counts.
- [x] The report includes detector model/serial, geometry source, threshold/cutoff,
  flat-field, dummy, and background-correction metadata.
- [x] Background-floor, configured dummy-sentinel, and unexpected-negative counts
  are distinguishable; the existing conservative `nonpositive_pixels` reason
  is retained.
- [x] `Saturation=0` is treated as unresolved/status-like unless an explicit
  positive saturation threshold is supplied; `ThresholdSetting` is not used as
  a saturation threshold.
- [x] Geometry and mask scientific validity remain `not_assessed`, but metadata
  presence is not reported as missing.
- [ ] Existing focused SAXS tests and repository verification pass.

## Implementation plan

1. Add real-style EDF header and four-frame regression tests for normalized
   metadata, processed-image pixel classifications, and `Saturation=0`.
2. Normalize known EDF detector fields in the active SAXS reader and apply
   explicit `Dummy`/`DDummy` values to a per-frame copied configuration.
3. Extend the existing detector quality report with metadata and conservative
   pixel classifications while preserving calibration validity and quality
   gates.
4. Run focused tests, real four-frame replay, the structured verifier, and a
   diff allowlist review before creating the local checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_edf_metadata_quality.py tests/test_saxs_raw_detector_quality_transport.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_2d_evidence_propagation.py -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-edf-metadata-quality-classification.md --changed --types
git diff --check
```

The full `tests/test_saxs_*.py` matrix is additionally attempted with an
explicit file list; a timeout is reported as incomplete rather than a pass.

## Verification record

- TDD RED: `python -m pytest -q tests/test_saxs_edf_metadata_quality.py
  tests/test_saxs_raw_detector_quality_transport.py -vv` -> 4 new tests failed
  on the expected missing metadata/classification/saturation behavior; the
  existing 9 transport tests passed.
- Focused GREEN: the same command after implementation -> `13 passed, 2
  warnings`.
- Focused 2D matrix -> `50 passed, 2 warnings`.
- Real read-only replay of `C:\Users\Fan Xuyi\Desktop\edf\610` -> 4 frames
  loaded; all reports have `metadata_status=complete`, header geometry, model
  `Dectris EIGER2 Si 500K`, serial `E-01-0419`, and independent pixel counts.
- Full SAXS matrix using an explicit file list timed out after 244 seconds with
  no reported failing test; it is incomplete, not a pass.
- Structured verifier initially failed task-card validation, then failed Ruff
  because the changed `io.py` also contains pre-existing E402/E741/F401
  baseline findings. Targeted Ruff (ignoring those baseline codes), compileall,
  and `git diff --check` pass.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_raw_detector_quality_transport.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_2d_evidence_propagation.py -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-edf-metadata-quality-classification.md --changed --types
git diff --check
```

Real-file probe (read-only, no repository output):

```powershell
python -c "from pathlib import Path; from polynexus.core.saxs_engine.io import read_image; root=Path(r'C:\Users\Fan Xuyi\Desktop\edf\610'); print([(p.name, read_image(str(p))[0].shape) for p in sorted(root.glob('*.edf'))])"
```

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-31-saxs-edf-metadata-quality-classification.md`
- `docs/superpowers/specs/2026-07-31-saxs-edf-metadata-quality-classification-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-edf-metadata-quality-classification.md`
- `polynexus/core/saxs_engine/io.py`
- `polynexus/core/saxs_engine/preprocess.py`
- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `tests/test_saxs_edf_metadata_quality.py`
