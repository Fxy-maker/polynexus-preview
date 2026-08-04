# SAXS Scientific Correctness Closure Acceptance

## Status

Implementation and focused verification are complete; task-level and full /
boundary verification remain pending in this checkpoint.

## Evidence

- `python -m pytest -q tests/test_saxs_scientific_correctness_closure.py`: 9 passed.
- Focused SAXS/GUI/strain matrix: 159 passed, 3 warnings.
- `python scripts/quality_gate.py --root D:\\PolyNexus`: quality 297 passed,
  preprocessing 106 passed, compile and whitespace passed.
- `ruff check` on the changed source/tests: passed.

## Changes accepted for review

- Porod-invariant crystallinity uses a dimensionless, explicit-unit contract.
- Cooling uses the low-temperature solid reference and preserves acquisition
  order; heating remains temperature-sorted.
- Signed corrected residuals remain available to raw/quality consumers;
  positive-only fits mask non-positive observations explicitly.
- Strain scalar scattering metrics use total profiles; sector data is restricted
  to orientation/anisotropy.
- Declared HDF5/Nexus inputs have deterministic dataset selection and typed
  actionable errors; batch limits are unlimited by default and provenance-
  visible when configured.
- Figure roles require physical and geometry evidence; relative Q-star and
  unavailable void fraction are diagnostic rather than misleading primary
  fields.

## Open gates

- Fresh task verification passed. Full/boundary verification reached pytest but
  timed out after 3600 seconds with exit `124` and no summary; it remains
  incomplete rather than accepted.
- Historical figure regeneration and human scientific review of absolute
  intensity/contrast assumptions.
