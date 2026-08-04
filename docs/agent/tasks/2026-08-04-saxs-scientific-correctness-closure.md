# SAXS Scientific Correctness Closure

## Goal

Close the 14 known SAXS findings across physical core, I/O/workflow, and figure/result contracts with regression evidence and fail-closed behavior.

## Non-goals

- Detector calibration inference, AI rescue, historical output regeneration, push, merge, or deployment.
- Changing unrelated techniques or GUI infrastructure outside SAXS result/figure eligibility.

## Affected boundaries

- Physical core: `polynexus/core/saxs_engine/core.py`, `saxs_physical_helpers.py`, `saxs_temperature.py`, `saxs_strain.py`, `saxs_quality_contracts.py`, and `preprocess.py`.
- I/O/workflow: `polynexus/core/saxs_engine/io.py`, `config.py`, and `polynexus/core/saxs.py`.
- Figure/result semantics: `figure_eligibility.py`, `gui/result_table_templates.py`, and `gui/saxs_results_table_service.py`.
- Regression coverage: `tests/test_saxs_scientific_correctness_closure.py` and affected SAXS contract tests.

## Implementation plan

1. Lock unit-safe invariant, cooling, signed-profile, and positive-fit behavior with RED/GREEN tests.
2. Route strain scalar metrics through total profiles and sectors through orientation-only consumers.
3. Align declared I/O extensions, HDF5/Nexus errors, and configurable batch limits with provenance.
4. Require physical/geometry evidence for figure roles and demote relative/invalid GUI fields to diagnostics.
5. Run task/full verification, refresh durable memory and acceptance evidence, review the cumulative diff, and checkpoint the explicit allowlist.

## Acceptance criteria

- [x] Unit-equivalent Porod invariant inputs return the same crystallinity or fail closed with the same reason.
- [x] Cooling high/low invariant labels and acquisition ordering match the low-temperature solid reference.
- [x] Signed residuals remain in corrected/raw profiles while positive-only fits use explicit masks.
- [x] Strain invariant/structure metrics use total profiles; sector changes affect orientation only.
- [x] Declared I/O formats either load through the matching route or return a typed actionable error.
- [x] Default batch loading is unlimited; configured limits are recorded as skipped provenance.
- [x] Incomplete geometry and missing physical gates cannot produce Main/publication eligibility.
- [x] Relative Q-star and unavailable void fraction remain diagnostic rather than misleading primary fields.
- [ ] Fresh task and full/boundary verification commands pass; any timeout is recorded as incomplete.

## Scope and acceptance

### Physical core

- [ ] Porod invariant crystallinity is unit-invariant or explicitly unavailable.
- [ ] Cooling phase labels and acquisition order match low-temperature solid semantics.
- [ ] Full-channel metrics are independent of equatorial-sector changes.
- [ ] Signed corrected residuals survive quality/raw payload; positive-only fits mask explicitly.
- [ ] Existing q-min, Gibbs–Thomson, polarization, control-parameter, and single/batch smoothing fixes remain green.

### I/O and workflow

- [ ] Declared extensions and single-file/directory readers agree, including actionable HDF5/Nexus errors.
- [ ] Batch limits are configurable; any configured truncation is recorded in sequence QA/provenance.

### Geometry and GUI

- [ ] Incomplete geometry cannot receive complete/header confidence or main figure eligibility.
- [ ] Figure role requires explicit physical eligibility, not only `quality_flag=OK`.
- [ ] `Q_star_rel` is diagnostic/relative; `phi_void` is primary only when finite and valid.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-scientific-correctness-closure.md --changed --types
python scripts/verify.py --changed --types --full --boundary
python -m pytest -q tests/test_saxs_scientific_correctness_closure.py
git diff --check
```

## Changed-file allowlist

- `docs/agent/tasks/2026-08-04-saxs-scientific-correctness-closure.md`
- `docs/superpowers/specs/2026-08-04-saxs-scientific-correctness-closure-design.md`
- `docs/superpowers/plans/2026-08-04-saxs-scientific-correctness-closure.md`
- `polynexus/core/saxs_engine/saxs_physical_helpers.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/preprocess.py`
- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `polynexus/core/saxs_engine/io.py`
- `polynexus/core/saxs_engine/config.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/core/saxs_engine/figure_eligibility.py`
- `polynexus/core/saxs.py`
- `polynexus/gui/result_table_templates.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_scientific_correctness_closure.py`
- affected SAXS regression tests updated for the corrected contract
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`

## Known limitations

- Full verification may exceed the Windows command timeout; an incomplete run is not a pass.
- Historical generated figures must be regenerated after the implementation checkpoint.
- Human scientific review remains required for absolute-contrast/Porod interpretation.
