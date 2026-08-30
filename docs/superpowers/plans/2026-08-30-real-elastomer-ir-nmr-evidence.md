# Real elastomer IR/NMR evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) to implement this plan task-by-task.

**Goal:** Make confirmed headerless NMR column mappings replayable and build a real IR/NMR article evidence package.

**Architecture:** Preserve the existing canonical template and evidence contracts. Carry a validated `MappingProposal` through the single-input adapter and replay path, then invoke the existing project packager for real-data runs.

**Tech Stack:** Python, dataclasses, pytest, existing `CanonicalExperiment`, `ProjectWorkflowService`, and `ProjectEvidencePackager`.

---

### Task 1: Add proposal deserialization and converter replay support

**Files:**
- Modify: `polynexus/core/canonical_experiments/models.py`
- Modify: `polynexus/core/canonical_experiments/registry.py`
- Modify: `polynexus/core/agent_workflow/service.py`
- Test: `tests/test_canonical_one_dimensional.py`

- [ ] Add `MappingProposal.from_dict()` using the existing validated selection parsing.
- [ ] Add optional `mapping_proposal` parameters to `convert_path()` and `replay_path()` and pass them to the generic table converter.
- [ ] During replay, pass `registered.mapping_proposal` back to the registry and compare the resulting content hash.
- [ ] Test round-trip and successful replay for a headerless NMR table.

### Task 2: Propagate confirmed mappings through the project adapter

**Files:**
- Modify: `polynexus/core/project_workflow/adapters.py`
- Modify: `polynexus/core/project_workflow/service.py`
- Test: `tests/test_project_workflow_adapters.py`
- Test: `tests/test_ai_native_project_entrypoint.py`

- [ ] Read an optional mapping proposal from a single-input manifest and pass it to canonical conversion.
- [ ] Carry request parameter `mapping_proposal` into planning and single-run manifests.
- [ ] Keep NMR submodule explicit and reject malformed proposals before provider execution.
- [ ] Test a public one-file NMR project run with the confirmed mapping.

### Task 3: Verify and materialize real evidence

**Files:**
- No raw-data edits.
- Generated: external user dataset `.polynexus` evidence workspace.

- [ ] Run focused tests and structured verifier.
- [ ] Build mapping proposals from the confirmed two-column convention and run all six IR series plus liquid/solid NMR files.
- [ ] Validate package manifest, source hashes, canonical templates, and evidence view.
- [ ] Record package path and counts in the completion report and durable memory.
