# Scientific Review Promotion Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce one shared, fail-closed scientific-review promotion contract
for IR mapping, NMR solid-C, and Joint while preserving existing results and
the manifest lifecycle.

**Architecture:** The shared review module restores serialized immutable
records and emits a small JSON-safe decision snapshot. Each technique core
attaches the snapshot to evidence/provenance and each provider derives only
publication roles from it. The GUI remains a consumer of persisted
FigureDefinition/Manifest data.

**Tech Stack:** Python dataclasses, NumPy, pytest, FigureDefinition,
AnalysisResult, JointBatchRow, and existing lifecycle services.

---

### Task 1: Shared review payload and snapshot

**Files:**
- Modify: `polynexus/core/scientific_review.py`
- Modify: `polynexus/core/__init__.py`
- Test: `tests/test_scientific_review.py`

- [x] Add restoration for JSON payloads and a normalized decision snapshot.
- [x] Make `promotion_decision` reject records that fail JSON-safe validation.
- [x] Cover accepted, missing, invalid, scope/source mismatch, and non-finite
  values.

### Task 2: IR mapping gate

**Files:**
- Modify: `polynexus/core/ir_engine/ir_mapping.py`
- Modify: `polynexus/core/ir.py`
- Test: `tests/test_ir_mapping.py`, `tests/test_ir_lifecycle_closure.py`

- [x] Restore `provenance["scientific_review"]` and keep raw map geometry and
  masks unchanged.
- [x] Gate map/ROI roles and preserve invalid-pixels diagnostic.
- [x] Persist the decision in mapping evidence, recipes, and engine metadata.

### Task 3: NMR solid-C gate

**Files:**
- Modify: `polynexus/core/nmr.py`
- Modify: `polynexus/core/nmr_engine/figure_provider.py`
- Test: `tests/test_nmr_figure_provider.py`, `tests/test_nmr_lifecycle_closure.py`,
  `tests/test_nmr_joint_provenance_matrix.py`

- [x] Attach source identity and optional review payload to analyzed results.
- [x] Persist the decision in shared NMR evidence and metadata.
- [x] Keep solid-C figures diagnostic by default; accepted review promotes the
  spectrum to Main and supporting figures to SI.
- [x] Preserve non-solid-C roles and verify real solid-C diagnostic-only output.

### Task 4: Joint gate

**Files:**
- Modify: `polynexus/core/joint/dataset.py`
- Modify: `polynexus/core/joint/figure_provider.py`
- Test: `tests/test_joint_figure_provider.py`, `tests/test_joint_lifecycle_closure.py`

- [x] Add an explicit batch-row review payload and source reference.
- [x] Require accepted source-matching records for every selected row.
- [x] Persist one aggregate decision in the hub report and every figure recipe.
- [x] Keep values/conflicts/provenance unchanged while gating roles.

### Task 5: Verification, acceptance, checkpoint

**Files:**
- Create: `docs/acceptance/2026-07-29-scientific-review-promotion-gates.md`
- Modify: durable memory only to record this verified state.

- [x] Run focused matrix and real solid-C lifecycle; capture exact summaries.
- [x] Run task-scoped and boundary verification; classify full/boundary timeout
  honestly.
- [ ] Create one explicit-allowlist checkpoint with `scripts/auto_commit.py`.

### Self-review checklist

- [x] No scientific values are inferred or overwritten.
- [x] No accepted record can promote a different source or scope.
- [x] Missing/invalid records remain available but diagnostic.
- [x] Fresh verification evidence is recorded before handoff.
