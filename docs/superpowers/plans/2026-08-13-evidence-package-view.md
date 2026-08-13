# Evidence Package View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Give the GUI a stable, technique-neutral read model for an immutable
evidence package.

**Architecture:** `evidence_view.py` loads only manifest, techniques,
writing-evidence, citation-metrics, ARS handoff, and limitations JSON. Frozen
records expose package status, technique summaries, evidence rows, metric
provenance, assets, and review actions. A small GUI adapter returns the same
DTOs for presentation and never branches on technique internals.

**Tech Stack:** Python frozen dataclasses, pathlib/JSON, pytest.

---

### Task 1: Failing view contract tests

**Files:**
- Create: `tests/test_evidence_package_view.py`

- [ ] Assert synthetic package loading yields four technique-neutral technique
  rows, metric rows, figures/tables, and human-review rows.
- [ ] Assert tampered metric/evidence references are rejected.
- [ ] Run the tests and observe the missing-module failure.

### Task 2: Implement core view model and GUI adapter

**Files:**
- Create: `polynexus/core/project_workflow/evidence_view.py`
- Create: `polynexus/gui/evidence_package_view.py`
- Modify: `polynexus/core/project_workflow/__init__.py`

- [ ] Implement frozen JSON-safe records and a package-path loader.
- [ ] Validate every writing metric ID and ARS Results/Discussion ID against
  `citation-metrics.json`; reject stale cross-file references.
- [ ] Implement a GUI adapter that only returns the DTO and summary rows.
- [ ] Run focused tests.

### Task 3: PA6 acceptance and checkpoint

**Files:**
- Create: `docs/acceptance/2026-08-13-evidence-package-view.md`
- Modify: `docs/agent/tasks/2026-08-13-evidence-package-view.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Load the latest four-technique PA6 package and verify all four technique
  rows and review actions.
- [ ] Run structured verification and checkpoint the explicit allowlist.
