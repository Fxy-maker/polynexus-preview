# SAXS 1D Figure Dirty Projection Design

## Goal

Make the temperature and strain SAXS Figure providers, including the legacy
temperature/strain Figure route, tolerate malformed per-element q/intensity
tokens after analysis has already retained explicit dirty-data provenance.

## Scope

Add one detached elementwise numeric projection helper to
`figure_common.py`. Use it for 1D q/intensity and derived 1D trace pairs in the
static, temperature, strain, and legacy Figure providers. Existing pair-length,
finite, positivity, minimum-point, sorting, uniqueness, and cross-frame overlap
rules remain the eligibility rules at each call site.

## Invariants and non-goals

- A conversion failure becomes `NaN` at the same position in a fresh array.
- No caller-owned array is mutated; no observation is interpolated, padded,
  inferred, duplicated, or automatically rescued by this boundary.
- Existing common-q interpolation in the strain heatmap remains unchanged and
  is used only after the existing valid curves have been selected.
- No condition-axis conversion, temperature/time/strain semantics, 2D image or
  azimuthal chi conversion, detector quality, analysis algorithm, DataQuality-
  Report level, physical threshold, AI/rescue decision, or publication role is
  changed.
- Completely invalid or undersized curves continue to be omitted or reported
  unavailable according to the existing provider contract.

## Design

`figure_common._coerce_numeric_array()` will create a one-dimensional float
array with `NaN` defaults and convert each source element independently,
catching `OverflowError`, `TypeError`, and `ValueError`. The static provider's
existing helper will use this shared projection. The temperature provider will
use it in `_positive_curve()` and `_mapping_curve()`, the strain provider in
its 1D profile/heatmap/trace paths, and the legacy provider in `_clean_frame()`.
No caller receives the projected array, so the helper cannot mutate source
data.

## Verification

TDD regressions will call the real public providers with object arrays containing
numeric strings and malformed tokens. They will assert that valid positions
survive, dirty source arrays remain unchanged, fully invalid curves remain
fail-closed, and existing clean definitions/roles stay unchanged. The task
requires focused GREEN, the task-scoped structured verifier, the exact SAXS
matrix with a final pytest summary, `git diff --check`, and report/clean
storage dry-runs. `test_storage.py --apply` is prohibited.
