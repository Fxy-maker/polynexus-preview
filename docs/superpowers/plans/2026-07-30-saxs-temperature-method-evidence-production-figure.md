# SAXS Temperature Method Evidence Production Figure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind already-emitted temperature method evidence to the production
SAXS Figure path without changing scientific semantics.

**Architecture:** Add a pure production-provider projection helper. It resolves
one temperature point only when its existing `source_index` uniquely matches a
frame view, emits nullable audit sources and finite plotting sources, and adds
an independent diagnostic Figure after the existing waterfall. The existing
evolution Figure and evidence attachment remain unchanged.

**Tech Stack:** Python, NumPy, dataclasses, Pytest, existing Figure contracts,
Ruff, and PolyNexus verification scripts.

---

### Task 1: Define the production boundary with RED tests

**Files:**
- Modify: `tests/test_saxs_temperature_figure_panels.py`

- [ ] Add a production-engine fixture case with existing per-frame method
  evidence, missing values, and source-index ordering.
- [ ] Add a duplicate-source-index case that must remain fail-closed.
- [ ] Run focused RED and record the missing production Figure.

### Task 2: Emit the production diagnostic Figure

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_temperature.py`
- Test: `tests/test_saxs_temperature_figure_panels.py`

- [ ] Add a pure unique-source binding helper and method evidence projection.
- [ ] Emit `saxs.series.temperature.method_evidence` only on the temperature
  axis, after the existing waterfall, with diagnostic role and no new gates.
- [ ] Run focused GREEN and the complete temperature Figure/evidence suite.

### Task 3: Verify and checkpoint

**Files:**
- Create: `docs/agent/tasks/2026-07-30-saxs-temperature-method-evidence-production-figure.md`
- Create: `docs/acceptance/2026-07-30-saxs-temperature-method-evidence-production-figure.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Run the structured verifier, exact SAXS matrix, storage report/clean
  dry-run, and `git diff --check`.
- [ ] Create one explicit allowlist checkpoint with `scripts/auto_commit.py`.

`test_storage.py --apply` is outside this task.
