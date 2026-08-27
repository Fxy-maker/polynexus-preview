# Architecture and Scientific Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair directory provenance consistency, enforce shared ComputeRun package provenance, and make DSC metric eligibility quality-aware and non-duplicative.

**Architecture:** Introduce one public directory-manifest hash helper and reuse it in every producer/validator. Treat `analysis_run.steps[*].compute_run` as mandatory for migrated package runs and validate its artifact/template identity against the recipe. Keep provider calculations unchanged; filter only the ARS citation projection using explicit DSC quality flags and segment identity.

**Tech Stack:** Python, dataclasses/JSON contracts, pytest, existing `scripts/verify.py` and `scripts/auto_commit.py`.

---

### Task 1: Unify directory manifest hashing

**Files:**
- Modify: `polynexus/core/canonical_experiments/registry.py`
- Create: `tests/test_directory_manifest_hash.py`

- [x] **Step 1: Write the failing cross-entry test**

```python
def test_converter_directory_hash_matches_raw_artifact(tmp_path):
    from polynexus.core.compute.models import RawArtifact
    from polynexus.core.canonical_experiments.registry import default_converter_registry
    source = tmp_path / "series"
    source.mkdir()
    (source / "a.dat").write_bytes(b"1,2\n")
    artifact = RawArtifact.from_path(source, technique="saxs")
    outcome = default_converter_registry().convert_path(
        source, technique="saxs", source_artifact_id=artifact.artifact_id
    )
    assert outcome.template is not None
    assert outcome.template.payload["source_sha256"] == artifact.sha256
```

- [x] **Step 2: Run the focused test and confirm it fails**

Run: `python -m pytest -q tests/test_directory_manifest_hash.py`

Expected: FAIL because the registry hashes bare entries while `RawArtifact`
uses the `directory_manifest` envelope.

- [x] **Step 3: Implement the minimal shared contract in the registry**

Change the registry directory digest to hash:

```python
{"kind": "directory_manifest", "entries": entries}
```

through the existing canonical JSON helper, preserving sorted entries and all
existing rejection behavior.

- [x] **Step 4: Run the test and the adjacent directory matrix**

Run: `python -m pytest -q tests/test_directory_manifest_hash.py tests/test_agent_directory_compute_run.py tests/test_agent_workflow_contracts.py`

Expected: PASS.

### Task 2: Enforce ComputeRun provenance at package validation

**Files:**
- Modify: `polynexus/core/project_workflow/package.py`
- Modify: `tests/test_project_workflow_package.py`

- [x] **Step 1: Add a failing test for a missing migrated ComputeRun**

Create a valid packageable `ProjectWorkflowRun` fixture, remove
`analysis_run.steps[0].compute_run` from its manifest payload while retaining
the old canonical hash fields, and assert `ProjectEvidencePackager.create`
raises `ValueError` matching `compute_run`.

- [x] **Step 2: Run the test and confirm it fails**

Run: `python -m pytest -q tests/test_project_workflow_package.py -k compute_run`

Expected: FAIL because `_validate_run` currently validates only the
`AnalysisRun` and evidence item hashes.

- [x] **Step 3: Implement validation**

For each analysis step, require a mapping `compute_run` with status
`completed`, an artifact matching the recipe artifact ID and SHA-256, and a
canonical template whose `source_artifact_id` matches that artifact. Keep the
existing DSC compatibility exception only for explicitly non-migrated legacy
manifests, and reject malformed migrated projections.

- [x] **Step 4: Run package and consumer tests**

Run: `python -m pytest -q tests/test_project_workflow_package.py tests/test_project_workflow_adapters.py tests/test_evidence_package_view.py`

Expected: PASS.

### Task 3: Make DSC citation eligibility quality-aware and deduplicated

**Files:**
- Modify: `polynexus/core/project_workflow/writing_metrics.py`
- Modify: `tests/test_project_workflow_package.py`

- [x] **Step 1: Add failing metric tests**

Assert that a segment with `quality_flags` containing
`event_starts_at_segment_boundary` or `low_avrami_r_squared` is not a
`results_candidate`, and that `best_avrami` with the same `(T_iso_C, values)`
as a segment does not create duplicate metric records.

- [x] **Step 2: Run the tests and confirm they fail**

Run: `python -m pytest -q tests/test_project_workflow_package.py -k dsc`

Expected: FAIL because `_dsc` currently emits every finite segment and
`best_avrami` unconditionally.

- [x] **Step 3: Implement deterministic filtering**

Read each record's `quality_flags`; any non-empty quality flag makes its
metrics `diagnostic_only` with the flags as reason codes. Emit `best_avrami`
only when it is not value-equivalent to an already emitted segment; retain
finite values and methods for review-only records.

- [x] **Step 4: Run the focused scientific matrix**

Run: `python -m pytest -q tests/test_project_workflow_package.py tests/test_analysis_evidence.py -k "dsc or writing or metric"`

Expected: PASS, with FTIR/SAXS/WAXS eligibility unchanged.

### Task 4: Update acceptance evidence and checkpoint

**Files:**
- Create: `docs/acceptance/2026-08-27-architecture-scientific-repair.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Record exact verification counts and remaining review limits**
- [x] **Step 2: Run `python scripts/verify.py --task docs/agent/tasks/2026-08-27-architecture-scientific-repair.md --changed --types`**
- [x] **Step 3: Run `git diff --check`**
- [ ] **Step 4: Create the allowlisted checkpoint with `scripts/auto_commit.py`**
