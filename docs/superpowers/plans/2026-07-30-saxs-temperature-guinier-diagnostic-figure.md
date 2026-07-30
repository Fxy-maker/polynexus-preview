# SAXS Temperature Guinier Diagnostic Figure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an evidence-preserving temperature Rg diagnostic figure to the existing SAXS Figure provider.

**Architecture:** Extend the existing temperature summary provider with one
diagnostic-only definition. The definition consumes the public
`TempSeriesResult` arrays and frame DTOs, stores nullable values for missing
frames, and uses the existing V2 figure contracts and evidence attachment.

**Tech Stack:** Python, NumPy, Pytest, existing FigureDefinition contracts, Ruff, and PolyNexus verification scripts.

---

### Task 1: Define the Figure boundary with RED tests

**Files:**
- Modify: `tests/test_saxs_temperature_figure_provider.py`

- [x] **Step 1: Write the failing tests**

Add coverage for a temperature result with finite and missing `Rg_array`
values. Assert the new figure id, diagnostic role, nullable data values,
source indices, frame levels/reason codes, no-interpolation recipe metadata,
strict JSON-safe source values, and V2 readiness. Add a compatibility test
that the existing fixture without `Rg_array` does not emit the new figure.

- [x] **Step 2: Run the focused RED command**

```powershell
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k "guinier_diagnostic" -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-temperature-guinier-diagnostic-red
```

Expected result: the new test fails because the provider has no
`saxs.series.temperature.guinier` definition.

### Task 2: Emit the diagnostic definition from existing evidence

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_provider.py`
- Test: `tests/test_saxs_temperature_figure_provider.py`

- [x] **Step 1: Add nullable evidence projection helpers**

Read the existing Rg and frame metadata without recomputation. Convert only
non-finite numeric values to `None`; keep frame order and use `None` for absent
source identity or reason metadata.

- [x] **Step 2: Add the diagnostic FigureDefinition**

Append `saxs.series.temperature.guinier` to the existing temperature summary
definitions only when `Rg_array` is available. Use a one-panel `plot_series`
definition with a `temperature_C` x column and `Rg_nm` y column, plus source
index, frame level, and reason-code columns. Set `publication_role="diagnostic"`
and record `missing_values_preserved=True` and `interpolation=False` in the
recipe.

- [x] **Step 3: Run focused GREEN**

```powershell
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k "guinier_diagnostic or temperature_provider" -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-temperature-guinier-diagnostic-green
```

Expected result: all selected tests pass.

### Task 3: Verify and checkpoint

**Files:**
- Create: `docs/agent/tasks/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md`
- Create: `docs/acceptance/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run structured verification and diff checks**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md --changed --types
git diff --check
```

- [x] **Step 2: Run the exact current SAXS matrix and storage dry-run**

Require a complete pytest summary and exit code `0`. Run
`python scripts/test_storage.py report --json` and
`python scripts/test_storage.py clean --older-than-hours 24`; never run
`test_storage.py --apply` for this task.

- [x] **Step 3: Create one explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(saxs): expose temperature guinier diagnostic figure" --files polynexus/core/saxs_engine/figure_provider.py tests/test_saxs_temperature_figure_provider.py docs/superpowers/specs/2026-07-30-saxs-temperature-guinier-diagnostic-figure-design.md docs/superpowers/plans/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md docs/agent/tasks/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md docs/acceptance/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md docs/agent/memory/active-work.md
```
