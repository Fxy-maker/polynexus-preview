# SAXS 1D Figure Dirty Projection Acceptance

Status: accepted for this automated 1D Figure boundary; scientific/release
gates remain separate.

`figure_common._coerce_numeric_array()` now creates a detached float vector,
preserving positions and representing malformed tokens as `NaN`. Static,
temperature, strain, and legacy 1D q/I or trace paths reuse it; existing
finite/positive/minimum/sort/overlap and fail-closed rules remain authoritative.

Evidence:

- RED: `3 failed, 21 deselected` for q/I provider paths; trace RED after
  restoring old conversions: `2 failed, 15 deselected`.
- GREEN: `7 passed, 22 deselected`; complete provider files `29 passed`.
- Structured verifier: exit `0`, quality `287`, preprocessing `106`, with
  Ruff/compile/type/memory/task/whitespace checks passing.
- Exact SAXS matrix: `540 passed, 6 warnings in 315.38s`, exit `0`.
- Storage report/clean: dry-run `302 artifacts, 40 eligible, 262 protected,
  0 removed`; no `--apply`, delete, move, or migration.
- Explicit allowlist implementation checkpoint: `957e6ce`; no push or merge
  was performed.

Limitations: condition/result arrays in the legacy provider and 2D detector,
azimuthal chi, geometry, mask, saturation, and orientation paths are not part
of this task. Analysis semantics, quality levels, physical thresholds,
AI/rescue, publication roles, and human scientific/release approval remain
unchanged/open.
