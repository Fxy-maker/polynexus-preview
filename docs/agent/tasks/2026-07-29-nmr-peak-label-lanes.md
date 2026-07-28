---
task_id: 2026-07-29-nmr-peak-label-lanes
kind: cross-module-display-regression
status: completed
---

# NMR solid-C peak label lanes

## Goal

Make dense NMR solid-C peak labels readable in the shared FigureDefinition
rendering path while preserving every assignment and all scientific values.

## Non-goals

- Do not change peak detection, ranking, fitting, assignment, or Xc semantics.
- Do not remove, truncate, or silently hide peak labels.
- Do not add a NMR-specific GUI rendering fork or alter real regression data.

## Affected boundaries

- `polynexus/core/nmr_engine/figure_provider.py`: emit lane-aware label objects.
- `polynexus/core/figures/renderer.py`: render mixed x-data/y-axes text.
- `tests/test_nmr_figure_provider.py` and `tests/test_figure_render_plan_core.py`.
- Shared document, Editor, Manifest, and Export consumers through the existing
  FigureDefinition/renderer contracts.

## Implementation plan

1. Add provider and renderer regressions for complete assignments, deterministic
   lanes, and the mixed x-data/y-axes transform.
2. Implement the display-only lane metadata and shared renderer transform.
3. Run the focused matrix and structured verifier, record acceptance evidence,
   and create an explicit allowlist checkpoint.

## Acceptance criteria

- [x] NMR peak labels retain the complete assignment text.
- [x] Peak label x positions remain ppm data coordinates.
- [x] Peak label y positions use deterministic axes-relative lanes.
- [x] The shared renderer supports the mixed coordinate mode without changing
      legacy data-coordinate or axes-coordinate text behavior.
- [x] Provider and renderer regressions pass, including definition validation
      and the existing NMR figure matrix.
- [x] Task-scoped verifier and whitespace checks pass.
- [x] An explicit allowlist checkpoint is created locally; no push, merge,
      release, or scientific approval is implied.

## Verification

```powershell
python -m pytest -q tests/test_nmr_figure_provider.py tests/test_figure_render_plan_core.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-nmr-peak-label-lanes.md --changed --types
```

## Known limitations

Lane placement improves automated rendering readability but does not replace
human review of assignment semantics or final restarted-GUI scientific sign-off.
