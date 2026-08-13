# ARS Writing Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a validated ARS-ready claim/evidence map from an immutable
PolyNexus evidence package.

**Architecture:** A narrow `ars_handoff` module builds JSON only from package
manifest, writing evidence, citation metrics, and limitations.  It classifies
metric IDs using the already-published eligibility field, then validates all
references against those immutable artifacts.  The packager writes it atomically.

**Tech Stack:** Python dataclasses/mappings, canonical JSON, pytest.

---

### Task 1: Failing contract test

**Files:**
- Create: `tests/test_project_ars_writing_handoff.py`

- [ ] Write a package-level test that expects `ars-writing-input.json`, a
  manifest link, Result-only citable metrics, diagnostic Discussion entries,
  and human-review requirements.
- [ ] Run it and verify failure because the artifact does not exist.

### Task 2: Build and validate the handoff

**Files:**
- Create: `polynexus/core/project_workflow/ars_handoff.py`
- Modify: `polynexus/core/project_workflow/package.py`

- [ ] Implement a deterministic builder and validator using no provider
  internal data.
- [ ] Wire atomic materialization and manifest projection.
- [ ] Add validator regression cases for invalid references and attempted
  diagnostic promotion.
- [ ] Run focused tests.

### Task 3: PA6 acceptance and checkpoint

**Files:**
- Create: `docs/acceptance/2026-08-13-ars-writing-handoff.md`
- Modify: `docs/agent/tasks/2026-08-13-ars-writing-handoff.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Run the real read-only four-technique PA6 replay, validate its handoff,
  and record the package path and boundaries.
- [ ] Run structured verification and create an allowlisted local checkpoint.
