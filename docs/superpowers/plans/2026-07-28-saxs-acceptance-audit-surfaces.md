# SAXS Acceptance Audit Surface Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carry the existing SAXS scientific acceptance audit into Workbench, Figure/Manifest, and quality export consumers.

**Architecture:** Consumers read only the already-attached audit mapping from `result.parameters`. Workbench formats a bounded advisory string; Figure and Export use existing detached JSON conversion boundaries. No consumer recalculates science or publication status.

**Tech Stack:** Python mappings, existing SAXS FigureDefinition/Manifest contracts, JSON-safe export, Pytest, Ruff, and repository verifier.

---

### Task 1: Establish RED surface coverage

**Files:**
- Create: `tests/test_saxs_acceptance_audit_surfaces.py`
- Modify: `tests/test_saxs_figure_evidence_binding.py` for production-provider
  route coverage

- [x] **Step 1: Write failing tests**

Cover four real boundaries: Workbench must include audit status/reason text
without mutating parameters; Figure attachment must retain roles and expose a
strict-JSON audit; Export quality payload must expose the same audit; and all
three consumers must omit the field when no existing snapshot is available.

- [x] **Step 2: Run RED**

```powershell
python -m pytest -q tests/test_saxs_acceptance_audit_surfaces.py -vv --basetemp C:\Temp\PolyNexus_saxs_acceptance_audit_surfaces_red
```

Expected: failures are limited to missing Workbench audit text, Figure audit
attachment, and Export audit field.

### Task 2: Implement the additive consumer bindings

**Files:**
- Modify: `polynexus/gui/saxs_results_table_service.py`
- Modify: `polynexus/core/saxs_engine/figure_evidence.py`
- Modify: `polynexus/core/saxs_engine/figure_provider.py`
- Modify: `polynexus/core/saxs_engine/figure_static.py`
- Modify: `polynexus/core/saxs_engine/figure_temperature.py`
- Modify: `polynexus/core/saxs_engine/figure_strain.py`
- Modify: `polynexus/core/saxs_export_bundle.py`

- [x] **Step 1: Add the Workbench audit formatter**

Read `payload.get("scientific_acceptance_audit")`, show status and up to the
existing bounded reason list as advisory text, and include the section in the
existing risk/next ordering. Return empty text for a missing or malformed
mapping.

- [x] **Step 2: Extend Figure attachment**

Add an optional `acceptance_audit` mapping to
`build_saxs_figure_evidence()`/`attach_saxs_figure_evidence()`. When it is a
mapping, copy it under `quality_provenance["scientific_acceptance_audit"]`.
Pass `result.parameters`' existing audit from static, temperature, strain, and
compatibility provider calls; do not call `get_parameters()` from a provider.

- [x] **Step 3: Extend quality export**

Read the existing audit from `engine.result.parameters` and, when it is a
mapping, place a strict-JSON detached copy at the top level of
`_quality_evidence_payload()`. Do not synthesize an audit for lightweight
callers that have no parameter snapshot.

- [x] **Step 4: Run focused GREEN**

```powershell
python -m pytest -q tests/test_saxs_acceptance_audit_surfaces.py -vv --basetemp C:\Temp\PolyNexus_saxs_acceptance_audit_surfaces_green
```

Expected: all surface tests pass and existing role/evidence payloads are
unchanged except for the additive audit mapping.

### Task 3: Verify and checkpoint

**Files:**
- Modify: this task card, acceptance record, and `active-work.md`.

- [x] **Step 1: Run exact SAXS matrix and structured verifier**

Record exact counts, warnings, quality/preprocessing gates, Ruff, compile,
type baseline, memory/task checks, and whitespace outcome.

- [x] **Step 2: Run diff and test-storage checks**

Run `git diff --check` and the prescribed dry-run test-storage report. Do not
delete pre-existing artifacts.

- [x] **Step 3: Create one explicit allowlist checkpoint**

Use `scripts/auto_commit.py` with exactly the task-card allowlist and no push.
