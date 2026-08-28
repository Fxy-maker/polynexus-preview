# Generic isothermal DSC candidate acceptance — 2026-08-28

The Core now detects and computes every shape-derived event candidate in each
isothermal segment. Boundary switching transients remain visible as
`transient` candidates, while the compatibility `avrami` projection selects a
settled non-transient candidate when available. Avrami fitting records the
shared Xt=0.05–0.80 window.

Verification:

- `python -m pytest -p no:cacheprovider -q tests/test_dsc_kinetics.py tests/test_dsc_canonical_isothermal_conversion.py`
  → 28 passed.
- `python -m pytest -p no:cacheprovider -q tests/test_dsc_kinetics.py tests/test_compute_service.py tests/test_dsc_publication_isothermal_provider.py`
  → 66 passed, 3 skipped.
- Real six-sample isothermal ComputeRun smoke over PA6, PA6-50, PA11,
  PA11-50, PA12, and PA12-50 → all six `completed`; candidate rows and
  provenance were retained in the shared result projection.
- `git diff --check` → passed.

For the real PA6-DWJJ source, the 180–184 °C settled candidates produce
half-times approximately 1.93, 1.97, 2.53, 3.16, and 3.82 min; the initial
sub-minute switching spikes remain separately labeled `transient` and no
longer become the compatibility best result.

Scientific promotion and paper-use decisions remain human/ARS review
boundaries; this acceptance only covers deterministic computation and shared
provenance.
