# SAXS Temperature Method Evidence Diagnostic Figure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only temperature 1D method-evidence diagnostic Figure
without changing SAXS analysis semantics.

**Architecture:** Extend the existing portable temperature summary provider with
one helper that projects per-frame `MetricEvidence` payloads into detached
nullable audit sources and finite plotting sources. Keep the method list
explicit and reuse existing Figure contracts and evidence attachment.

**Tech Stack:** Python, NumPy, Pytest, existing FigureDefinition contracts,
Ruff, and PolyNexus verification scripts.

---

### Task 1: Define the Figure boundary with RED tests

**Files:**
- Modify: `tests/test_saxs_temperature_figure_provider.py`

- [ ] Add coverage for four existing method payloads, missing/non-finite values,
  source identity, levels, reasons, strict JSON, detached values, and legacy
  compatibility.
- [ ] Run the focused RED command and record the expected missing Figure.

### Task 2: Emit the diagnostic Figure from existing evidence

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_provider.py`
- Test: `tests/test_saxs_temperature_figure_provider.py`

- [ ] Add explicit nullable and finite-pair projection helpers.
- [ ] Add `saxs.series.temperature.method_evidence` to the existing summary
  definitions only when at least one supported method has frame evidence.
- [ ] Keep the role diagnostic and record the no-interpolation boundary in the
  recipe.
- [ ] Run focused GREEN and the complete temperature provider regression.

### Task 3: Verify and checkpoint

**Files:**
- Create: `docs/agent/tasks/2026-07-30-saxs-temperature-method-evidence-diagnostic-figure.md`
- Create: `docs/acceptance/2026-07-30-saxs-temperature-method-evidence-diagnostic-figure.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Run the structured verifier, exact SAXS matrix, storage report/clean
  dry-run, and `git diff --check`.
- [ ] Require a complete pytest summary and exit code `0`; record timeout or
  no-summary runs only as limitations.
- [ ] Create one explicit allowlist checkpoint with `scripts/auto_commit.py`.

`test_storage.py --apply` is outside this task.
