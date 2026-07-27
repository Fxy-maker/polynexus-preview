# SAXS Automatic In-Plane Orientation Axis

## Goal

Make SAXS Herman orientation analysis usable when the tensile/sample axis is
not known in advance by detecting the dominant in-plane scattering axis, while
preserving an explicit configured axis when one is supplied.

## Non-goals

- Do not infer a three-dimensional tensile direction from one 2D detector
  image.
- Do not silently equate the dominant scattering-vector axis with the polymer
  chain axis or lamellar normal.
- Do not change q* selection, detector calibration, GUI event handlers, table
  formatting, or publication approval rules.
- Do not modify real EDF datasets or pre-existing release-audit/memory files.

## Affected boundaries

- `polynexus/core/saxs_engine/config.py`: optional explicit orientation-axis
  configuration and automatic-detection thresholds.
- `polynexus/core/saxs_engine/saxs_anisotropy.py`: second-harmonic in-plane
  axis detection, configured-axis precedence, 2D Herman calculation metadata.
- `polynexus/core/saxs_engine/saxs_strain.py`: pass the existing SAXS config
  into the canonical orientation consumer.
- Existing orientation evidence contract: retain detected-axis
  source/strength/confidence in the existing JSON-safe fit evidence without
  changing the shared contract implementation.
- Focused SAXS orientation and strain tests.

## Scientific contract

The detector azimuth is 180-degree periodic. Automatic detection uses the
complex second harmonic of a baseline-subtracted azimuthal profile:

```text
z2 = integral(w(chi) * exp(2 i chi) dchi) / integral(w(chi) dchi)
axis = 0.5 * arg(z2)
strength = abs(z2)
```

An explicit finite `orientation_axis_deg` wins over automatic detection. With
no explicit axis, a low `strength` or insufficient valid bins makes the axis
unavailable and the Herman cell remains unavailable rather than fabricating a
direction. Automatic results are labeled as `auto_detected` and exposed in
orientation evidence; they are a principal scattering-axis result, not proof
of a three-dimensional tensile-axis assignment.

The 2D azimuthal Herman calculation uses the configured/detected axis and
direct azimuthal intensity weighting after baseline removal. It does not apply
the legacy `abs(sin(chi))` polar-angle weight to a detector-plane azimuthal
profile; consequently a uniform 2D ring has the Herman-form baseline `f=0.25`,
not the 3D random-orientation baseline `f=0`.

## Acceptance criteria

- [x] An explicit finite axis is used and reported as `configured`.
- [x] Missing axis information produces a finite auto-detected axis for a
  sufficiently anisotropic synthetic ring.
- [x] Detector-plane axis detection handles 180-degree periodicity and axes
  away from the default vertical direction.
- [x] Isotropic/weak profiles remain unavailable in auto mode with an explicit
  low-confidence reason.
- [x] Orientation evidence contains the axis, source, strength, and confidence
  without breaking existing JSON-safe contracts.
- [x] Existing strain transport and unavailable behavior remain intact.
- [x] Focused tests, full SAXS matrix, and structured verifier pass.
- [x] One atomic checkpoint is created with an explicit changed-file allowlist.

## Implementation plan

1. Add explicit orientation-axis and conservative auto-detection settings to
   the SAXS configuration and write regression tests first.
2. Resolve a configured or second-harmonic detector-plane axis in the core
   anisotropy analyzer and compute the Herman factor without the legacy polar
   weight.
3. Pass the existing SAXS config through the canonical strain consumer and
   retain axis provenance in the existing JSON-safe orientation evidence.
4. Run focused tests, the complete SAXS matrix, and the structured verifier;
   inspect the cumulative diff and checkpoint only the explicit allowlist.

## Verification commands

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_auto_axis_focus'
python -m pytest tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_batch_parameters.py tests/test_saxs_results_table_service.py -q
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-auto-orientation-axis.md --changed --types
```

## Verification

The task is accepted only when the focused orientation/strain/table tests, the
complete `tests/test_saxs_*.py` matrix, and the command above all pass. Existing
Arial CJK glyph warnings are recorded but are not introduced by this task.

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-auto-orientation-axis.md --changed --types
```

## Verification evidence (2026-07-27)

- Focused orientation/strain/table regression: `77 passed`.
- Complete SAXS matrix: `353 passed, 4 warnings`; warnings are the existing
  Arial CJK glyph warnings from SAXS figure layout.
- Structured verifier: task card, memory, Ruff, compile/type baseline, quality
  `282`, preprocessing `106`, and whitespace checks all passed.
- Real EDF diagnostic rerun with automatic axis: `—`, `0.4371`, `0.5582`,
  `0.4616`, `0.4737`; the first frame is unavailable because its second
  harmonic strength is below the conservative auto-detection threshold. Each
  finite result also carries a detected axis angle and strength.

## Known limitations

Automatic detection cannot resolve whether the measured scattering axis is
parallel or perpendicular to the physical tensile/chain direction without
sample geometry or loading metadata. Out-of-plane geometry and tilted samples
need a calibrated 3D/tilted-detector treatment.

## Pre-existing workspace changes

Many untracked pytest diagnostics and unrelated Origin/editor/release-audit
artifacts exist in the worktree. They remain untouched and outside this task's
checkpoint.

## Changed-file allowlist

- `polynexus/core/saxs_engine/config.py`
- `polynexus/core/saxs_engine/saxs_anisotropy.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_2d_detector_orientation_evidence.py`
- `tests/test_saxs_batch_parameters.py`
- `docs/agent/tasks/2026-07-27-saxs-auto-orientation-axis.md`
- `docs/superpowers/specs/2026-07-27-saxs-auto-orientation-axis-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-auto-orientation-axis.md`
