# SAXS Workbench Geometry and Mask Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show existing raw-detector geometry and mask provenance in Workbench review text without recomputation or scientific promotion.

**Architecture:** A pure presentation helper consumes the persisted raw detector mapping and returns a localized provenance fragment. The existing detector review formatter appends it only to the raw-detector detail; sector-map evidence and existing quality text remain untouched.

**Tech Stack:** Python, typed mappings, pytest, existing i18n helpers, repository verifier.

---

### Task 1: Add failing Workbench provenance tests

**Files:**
- Modify: `tests/test_saxs_results_table_service.py`

- [x] **Step 1: Test complete and mixed raw provenance.**

Build a raw report with `geometry_provenance.source="mixed"`, two
`header`/two `config_default`/one `invalid_header` field sources, and a mask
mapping with source `saxs_config.dummy_value`, configured `True`, and shape
`[128, 256]`. Assert the English review text includes geometry source,
field-source counts, mask source, shape, and `not_assessed`.

- [x] **Step 2: Test absent and unconfigured provenance.**

Assert a raw report without provenance emits no geometry/mask provenance labels.
Assert a raw report with mask source `none`, configured `False`, and shape
`None` emits those explicit facts without inventing a mask.

- [x] **Step 3: Test bilingual output, separation, and immutability.**

Use a Chinese raw report plus a sector-map report. Assert Chinese labels appear,
English raw labels do not replace them, sector text does not contain raw
provenance fields, and a deep copy of the input equals the original after
formatting.

- [x] **Step 4: Run RED.**

```powershell
python -m pytest -q tests/test_saxs_results_table_service.py -k detector --basetemp C:\Temp\PolyNexus_saxs_workbench_geometry_mask_red
```

Expected: the existing detector tests pass and the new provenance assertions
fail because the Workbench currently ignores the nested provenance mappings.

### Task 2: Implement the presentation-only provenance fragment

**Files:**
- Modify: `polynexus/gui/saxs_results_table_service.py`

- [x] **Step 1: Add a pure nested-mapping summary helper.**

Read `geometry_provenance` and `mask_provenance` only from a raw detector
report. Count only the known string source labels in `field_sources`; preserve
deterministic ordering `header`, `config_default`, `invalid_header`. Render
shape as `heightxwidth` when it is a two-item list, otherwise render the
existing safe scalar. Never derive status from counts.

- [x] **Step 2: Append the fragment to existing detector detail.**

Keep all current level/coverage/reason and risk logic. Add the fragment to the
same `parts` list for the raw report. Include an advisory sentence that
`not_assessed` still requires human review, without changing `needs_review`.

- [x] **Step 3: Run GREEN.**

```powershell
python -m pytest -q tests/test_saxs_results_table_service.py -k detector --basetemp C:\Temp\PolyNexus_saxs_workbench_geometry_mask_green
```

Expected: all focused detector/provenance tests pass.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-28-saxs-workbench-geometry-mask-provenance.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [x] **Step 1: Run consumer matrix and task verifier.**

Run the exact commands in the task card with external basetemps and record
actual counts, warnings, and exit codes. The verifier must report task/memory,
Ruff, compile/type, quality, preprocessing, and whitespace results.

- [x] **Step 2: Review changed paths and diff.**

Confirm only the explicit allowlist changed. Run `git diff --check`.

- [x] **Step 3: Create the checkpoint.**

```powershell
python scripts/auto_commit.py `
  --message "feat(saxs): expose detector provenance in workbench" `
  --files docs/agent/tasks/2026-07-28-saxs-workbench-geometry-mask-provenance.md docs/superpowers/specs/2026-07-28-saxs-workbench-geometry-mask-provenance-design.md docs/superpowers/plans/2026-07-28-saxs-workbench-geometry-mask-provenance.md polynexus/gui/saxs_results_table_service.py tests/test_saxs_results_table_service.py docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```
