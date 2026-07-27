# SAXS EDF Herman Orientation Source

## Goal

Make anisotropic EDF frames produce the azimuthal evidence required for the
existing Herman orientation factor and strain result-table transport.

## Non-goals

- Do not change the Herman mathematical convention or GUI table formatting.
- Do not derive orientation from the `.edf` filename or `orientation_evidence`.
- Do not modify real EDF datasets, detector calibration files, GUI handlers, or
  parallel release-audit memory files.
- Do not push, merge, deploy, or send external messages.

## Affected boundaries

- `polynexus/core/saxs_engine/preprocess.py`: 2D azimuthal source data.
- `polynexus/core/saxs_engine/saxs_strain.py`: canonical payload consumer.
- Existing `polynexus/core/saxs.py` transport and GUI table contract: expected
  to remain unchanged unless a focused compatibility issue is found.
- `tests/test_saxs_preprocess.py` and `tests/test_saxs_batch_parameters.py`.

## Acceptance criteria

- [x] `preprocess_pipeline()` emits canonical `I_2d`, `q_2d`, and `chi_rad` for
  anisotropic EDF-shaped input when geometry is valid.
- [x] Existing `analyze_anisotropy()` produces a finite Herman factor from that
  canonical payload.
- [x] Existing strain rows publish finite `f_Herman` values for valid 2D data.
- [x] 1D/isotropic/invalid/insufficient data remain explicit unavailable cells.
- [x] Existing SAXS regression matrix remains green.
- [x] Structured task verifier passes.
- [x] One atomic checkpoint is created with the explicit allowlist below.

## Implementation plan

1. Add failing preprocessing and strain-consumer regressions for canonical
   azimuthal data.
2. Add a manual geometry fallback to `integrate_chi_sectors()` and attach the
   canonical 2D payload during anisotropic preprocessing.
3. Reuse `analyze_anisotropy()` from the strain Herman adapter and preserve
   unavailable behavior for malformed or non-2D input.
4. Run focused tests, the complete SAXS matrix, and the structured verifier.
5. Review the cumulative diff and create one explicit-allowlist checkpoint.

## Verification commands

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_edf_herman_focus'
python -m pytest tests/test_saxs_preprocess.py tests/test_saxs_batch_parameters.py tests/test_saxs_results_table_service.py -q
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-edf-herman-source.md --changed --types
```

## Verification evidence (2026-07-27)

- TDD RED: preprocessing lacked `I_2d`; the strain consumer returned a
  non-finite factor for the canonical payload.
- Focused EDF/preprocess/strain/table/2D matrix: `82 passed`.
- Complete SAXS matrix: `344 passed, 4 warnings`; warnings are the existing
  Arial CJK glyph warnings from SAXS figure layout.
- Structured verifier with an isolated basetemp passed task/memory, Ruff,
  compile/type baseline, quality `282`, preprocessing `106`, and whitespace.

## Verification

```powershell
python -m pytest tests/test_saxs_preprocess.py tests/test_saxs_batch_parameters.py tests/test_saxs_results_table_service.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_mode_evidence_propagation.py -q
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-edf-herman-source.md --changed --types
```

## Known limitations

The factor remains unavailable when geometry is invalid, an image cannot be
read, the image is explicitly isotropic, or the azimuthal signal has too few
valid bins. A finite factor is an analysis result, not publication approval.

## Pre-existing workspace changes

The worktree contains tracked release-audit memory edits and many untracked
Origin/editor and pytest diagnostics. They remain untouched and outside this
task checkpoint.

## Changed-file allowlist

- `polynexus/core/saxs_engine/preprocess.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_preprocess.py`
- `tests/test_saxs_batch_parameters.py`
- `docs/agent/tasks/2026-07-27-saxs-edf-herman-source.md`
- `docs/superpowers/specs/2026-07-27-saxs-edf-herman-source-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-edf-herman-source.md`
