# NMR solid-C peak label lanes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox syntax for tracking.

**Goal:** Make dense NMR solid-C labels readable through a portable mixed-coordinate figure object.

**Architecture:** The NMR provider owns deterministic lane assignment; the shared Matplotlib renderer owns the `xdata_yaxes` transform. Existing FigureDefinition, document, V2, Editor, Manifest, and Export boundaries remain unchanged.

**Tech Stack:** Python, Matplotlib, pytest, existing FigureDefinition and render-plan contracts.

---

### Task 1: Establish the failing provider and renderer regressions

**Files:**
- Modify: `tests/test_nmr_figure_provider.py`
- Modify: `tests/test_figure_render_plan_core.py`

- [x] Add a provider test with six assigned peaks that asserts complete
      assignments and the five-lane y sequence.
- [x] Add a renderer test that asserts `xdata_yaxes` text uses the blended
      x-data/y-axes transform and preserves its position.
- [x] Run both new tests and record the expected RED failures.

### Task 2: Implement the smallest display-only change

**Files:**
- Modify: `polynexus/core/nmr_engine/figure_provider.py`
- Modify: `polynexus/core/figures/renderer.py`

- [x] Remove assignment truncation while preserving the existing peak limit.
- [x] Emit deterministic lane coordinates and the explicit coordinate-space
      marker for peak labels.
- [x] Add the renderer branch for `xdata_yaxes` using
      `axis.get_xaxis_transform()`.
- [x] Run the focused tests and confirm GREEN.

### Task 3: Recheck shared consumers and checkpoint

**Files:**
- Create: `docs/acceptance/2026-07-29-nmr-peak-label-lanes.md`
- Modify: `docs/agent/tasks/2026-07-29-nmr-peak-label-lanes.md`

- [x] Run the NMR provider/shared renderer matrix.
- [x] Run `python scripts/verify.py --task docs/agent/tasks/2026-07-29-nmr-peak-label-lanes.md --changed --types`.
- [x] Run whitespace/diff checks and inspect the cumulative diff.
- [x] Create one allowlisted local checkpoint with `scripts/auto_commit.py`.
- [x] Record remaining scientific/restarted-GUI limitations; do not claim the
      overall software goal complete.
