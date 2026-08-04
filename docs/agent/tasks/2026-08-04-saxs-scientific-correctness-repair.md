# SAXS Scientific Correctness Repair

## Goal

Repair the remaining SAXS scientific and input-contract defects identified in
the 2026-08-04 review. Quantitative outputs must either use a documented
physical convention with independent regression evidence or be returned as a
diagnostic/unavailable result with a reason.

## Non-goals

- Implementing new Ruland stripe analysis or Vonk desmearing in this task.
- Inferring detector calibration, absolute contrast, or missing metadata.
- Rewriting historical generated figures or real regression datasets.
- Changes to non-SAXS techniques, push/merge/deployment, or user-owned data.

## Affected boundaries

- Physical core: `core.py`, `saxs_physical_helpers.py`, `saxs_extrapolation_helpers.py`,
  `preprocess.py`, `config.py`.
- Temperature service: `saxs_temperature.py`.
- Input/workflow: `io.py`, `saxs.py`.
- 2D orientation: `saxs_anisotropy.py` and result labels/templates.
- Regression coverage: focused SAXS tests plus existing closure tests.

## Decisions

1. Background subtraction uses the raw-intensity measurement equation. The
   transmission scale is `T_sample/T_background` before sample normalization;
   background thickness is explicit when thickness scaling is selected.
2. `q_unit` is explicit in `SAXSConfig` and reader metadata. A unitless 1D
   file can be loaded for inspection, but absolute length, Porod, invariant,
   and thermodynamic outputs are unavailable unless a unit is declared.
3. The Porod convention follows the documented definitions
   `Q=2*pi^2*drho^2*phi*(1-phi)` and `Kp=2*pi*drho^2*Sv`. The lamellar
   conversion is `phi*(1-phi)=2*Q/(pi*Kp*L)` when `Sv=2/L`, and
   `Sv=pi*phi*(1-phi)*Kp/Q`.
4. The default low-q correlation extension is finite at q=0. If a valid
   Guinier fit cannot be established, the code leaves the measured boundary
   unchanged and records an unavailable reason.
5. Cooling/isothermal crystallinity uses fixed sequence endpoints after the
   complete sequence is known. Avrami requires an explicit seconds axis.
   Gibbs-Thomson requires melting-window evidence and an explicit enthalpy
   parameter; a generic temperature scan is not treated as melting points.
6. Detector-plane orientation remains available as a legacy diagnostic but is
   labeled as a projected 2D order parameter, with complete pi-periodic sector
   masks. Existing aliases remain readable.
7. HDF5/Nexus readers reject multiple equally eligible datasets and select the
   container route before generic image readers.

## Acceptance criteria

- Independent analytic tests catch the background scale, Guinier boundary,
  Porod/`Sv`, and q-unit behaviors.
- Cooling `Q=[1,2,...]` does not produce `[NaN,1,1,...]`; Avrami is invalid
  without supplied seconds; Gibbs-Thomson rejects non-melting windows.
- Unitless 1D input is marked unavailable for absolute metrics, while an
  explicitly declared Angstrom profile converts consistently to nm.
- Each frame receives an isolated geometry config; an incomplete later header
  cannot inherit a previous frame's geometry.
- Uniform full-ring and mirrored sector data produce unbiased orientation and
  anisotropy metrics; projected orientation labels are no longer presented as
  an unqualified 3D Herman factor.
- Duplicate/non-uniform q input is normalized or rejected before operations
  requiring a constant `dq`; ambiguous HDF5 containers raise a typed error.
- `Q_invariant` anomaly confidence checks run after Q is assigned.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_scientific_correctness_repair.py
python scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-scientific-correctness-repair.md --changed --types
python scripts/verify.py --changed --types --full --boundary
git diff --check
```

## Changed-file allowlist

The final allowlist will contain only files changed for this task, the new
focused test module, this task card, its design/plan documents, and durable
memory/acceptance notes updated with actual verification output.

## Known limitations

Absolute contrast, detector calibration, and the physical interpretation of a
lamellar two-phase model remain human scientific review gates. Ruland and Vonk
remain unsupported methods and must not be advertised as implemented.
