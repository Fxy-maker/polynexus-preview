# Optional Project Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional, hashed project context and eliminate the DSC implicit PE reference fallback.

**Architecture:** A small immutable loader validates `.polynexus/project-context.json` or a mapping. `ComputeRunService` stores the sanitized snapshot/hash on `AnalysisPlan` and projects only explicit DSC reference enthalpy into the provider config. DSC returns NaN/unavailable for Xc without that parameter while retaining Tg/Tm/enthalpy calculations.

**Tech Stack:** Python dataclasses, standard-library JSON/SHA-256, pytest.

---

### Task 1: Context contract and loader

**Files:**
- Create: `polynexus/core/project_context.py`
- Test: `tests/test_project_context.py`

- [ ] Write tests for empty/missing context, valid DSC reference, malformed schema, and non-positive reference.
- [ ] Run `python -m pytest -q tests/test_project_context.py` and observe the missing-module failure.
- [ ] Implement `ProjectContext` with `load(value)`, optional project-file loader, frozen snapshot, and SHA-256.
- [ ] Re-run the focused tests and verify they pass.

### Task 2: Shared plan/run provenance

**Files:**
- Modify: `polynexus/core/compute/models.py`
- Modify: `polynexus/core/compute/service.py`
- Test: `tests/test_compute_service.py`

- [ ] Add optional `project_context` and `project_context_sha256` fields to `AnalysisPlan` with stable defaults.
- [ ] Add `project_context` argument to `run_direct`; validate before engine creation and include the snapshot/hash in the plan identity.
- [ ] Add tests proving context is optional, invalid context blocks provider execution, and valid context is serialized/hash-linked.
- [ ] Run the focused compute tests red, implement, then green.

### Task 3: DSC consumes explicit context only

**Files:**
- Modify: `polynexus/core/dsc_engine/config.py`
- Modify: `polynexus/core/dsc_engine/core.py`
- Modify: `polynexus/core/dsc.py`
- Test: `tests/test_dsc_engine.py`

- [ ] Add a failing test that unknown material/reference leaves `DHm0_source` as `missing` and Xc as NaN, while explicit `DHm0_override` still computes Xc.
- [ ] Remove the PE `293.0` fallback; return NaN when no explicit reference exists.
- [ ] Make `DSCEngine` accept an existing `DSCConfig` and apply only the explicit context reference before analysis.
- [ ] Run DSC tests and update only assertions that encode the removed implicit fallback.

### Task 4: Cross-entry wiring and verification

**Files:**
- Modify: `polynexus/core/compute/service.py` (only if needed for provider projection)
- Modify: `polynexus/core/compute/__init__.py`
- Test: `tests/test_compute_service.py`

- [ ] Verify existing GUI/CLI/Batch calls work unchanged without context.
- [ ] Add one service-level test proving context reference reaches DSC and no context does not require GUI/CLI input.
- [ ] Run the task verifier and `git diff --check`.
- [ ] Create the allowlisted local checkpoint with `scripts/auto_commit.py`.
