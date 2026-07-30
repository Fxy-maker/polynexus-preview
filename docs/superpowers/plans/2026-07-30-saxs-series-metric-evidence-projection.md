# SAXS Series Metric Evidence Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve existing SAXS series metric source-index integrity evidence across Figure/Manifest and Export boundaries.

**Architecture:** Add the three existing summary keys to the common Figure evidence allowlist. Use focused tests for direct Figure projection, manifest persistence, and Export JSON; leave the core summary contract and Export serializer unchanged.

**Tech Stack:** Python 3.14, dataclasses, pytest, existing FigurePipeline, SAXS export bundle, strict JSON serialization.

---

### Task 1: Reproduce the projection loss

**Files:**
- Create: `tests/test_saxs_series_metric_evidence_projection.py`
- Reference: `polynexus/core/saxs_engine/figure_evidence.py`
- Reference: `polynexus/core/saxs_export_bundle.py`

- [x] **Step 1: Write the failing Figure, Manifest, and Export tests**

Use a `MetricEvidenceSummary`-shaped mapping containing the three source-index
fields. Assert that `build_saxs_figure_evidence()` keeps the fields in its
series record, that a FigurePipeline document keeps them in persisted recipe
provenance, and that `export_saxs_bundle()` keeps them in
`quality_evidence.json`. Also assert strict JSON serialization and source
mapping detachment.

- [x] **Step 2: Run the focused tests to verify RED**

Run:

```powershell
python -m pytest -q tests/test_saxs_series_metric_evidence_projection.py -o addopts= --basetemp=D:\PolyNexus_saxs_series_metric_evidence_projection_red
```

Expected: the direct Figure and persisted Manifest assertions fail because
the current common evidence allowlist omits the three new fields; Export is
expected to remain green.

### Task 2: Add the minimal Figure projection fields

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_evidence.py:23-37`
- Test: `tests/test_saxs_series_metric_evidence_projection.py`

- [x] **Step 1: Extend the explicit allowlist**

Append `duplicate_source_index_indices`,
`invalid_source_index_indices`, and `source_index_order_reordered` to
`_COMMON_EVIDENCE_FIELDS`. Do not change `_project_mapping()` or add any
special-case source-index logic.

- [x] **Step 2: Run the focused tests to verify GREEN**

Run:

```powershell
python -m pytest -q tests/test_saxs_series_metric_evidence_projection.py tests/test_saxs_figure_evidence_binding.py tests/test_saxs_export_bundle.py -o addopts= --basetemp=D:\PolyNexus_saxs_series_metric_evidence_projection_green
```

Expected: all focused Figure/Manifest/Export tests pass with no new warning
or mutation failures.

### Task 3: Verify and checkpoint the atomic task

**Files:**
- Modify: `docs/agent/tasks/2026-07-30-saxs-series-metric-evidence-projection.md`
- Modify: `docs/acceptance/2026-07-30-saxs-series-metric-evidence-projection.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run task-scoped verification and the exact SAXS matrix**

Run the commands recorded in the task card. Count a matrix as passed only when
pytest reports a complete summary and exits `0`; record any timeout or abort as
a limitation.

- [x] **Step 2: Inspect test storage without deletion**

Run `python scripts/test_storage.py report --json` and
`python scripts/test_storage.py clean --older-than-hours 24`. Do not run
`test_storage.py --apply`.

- [x] **Step 3: Run diff checks and create one explicit allowlist checkpoint**

Run `git diff --check`, review the allowlist against `git diff`, and call
`scripts/auto_commit.py` with only the source, test, task, spec, plan,
acceptance, and `active-work.md` paths.
