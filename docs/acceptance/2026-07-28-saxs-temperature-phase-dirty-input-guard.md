# SAXS temperature-phase dirty-input guard acceptance

Date: 2026-07-28

## Delivered behavior

`detect_temperature_phase()` now applies the existing `_coerce_optional_float()`
policy to Q*, solid Q*, L, and solid L before the unchanged phase classifier.
Numeric strings and malformed/non-finite values no longer raise. Existing
normalization, heating/cooling/isothermal thresholds, cold-crystallization
check, enum values, and default fallback remain unchanged.

No phase inference, frame substitution, interpolation, AI/rescue behavior,
new threshold, or publication change was introduced.

## Evidence

- RED: `3 failed, 2 passed`.
- GREEN: `5 passed in 0.10s`.
- Temperature matrix: `53 passed in 19.94s`.
- Exact SAXS matrix: `518 passed, 6 warnings in 256.45s`.
- Task verifier without changed-file lint: exit code `0`; Pyright `0 errors`,
  quality `287`, preprocessing `106`, compile, whitespace, memory/task, and
  diff checks passed.
- Targeted Ruff/compile for the task files passed.
- Storage dry-run: `526` artifacts, `192` eligible, `334` protected, `0`
  removed.

## Verification limitation

The exact `--changed --types` verifier variant exited `1` on ten pre-existing
Ruff findings in parallel-modified `polynexus/core/saxs_engine/io.py`. That
file is outside the explicit allowlist and was intentionally left untouched.
No fresh full/boundary result is attributed to this atomic task.
