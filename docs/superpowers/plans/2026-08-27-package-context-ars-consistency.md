# Package Context and ARS Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carry explicit project grouping context from run manifests into the ARS handoff.

**Architecture:** Package creation owns context collection; ARS handoff projects a validated additive view. No provider or scientific eligibility code changes.

**Tech Stack:** Python, JSON-safe mappings, pytest.

---

### Task 1: Regression tests

- [ ] Add a handoff test proving confirmed context is included and labeled non-instrument fact.
- [ ] Add a package test proving context is collected from request parameters.
- [ ] Run tests and observe failure.

### Task 2: Implement projection

- [ ] Collect deduplicated context in `ProjectEvidencePackager`.
- [ ] Add `project_context` to `build_ars_writing_input` and validate it.
- [ ] Run focused tests.

### Task 3: Verify and checkpoint

- [ ] Run structured verifier and diff check.
- [ ] Record acceptance and create allowlisted local checkpoint.
