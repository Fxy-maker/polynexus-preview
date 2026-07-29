# IR Mapping Scientific Review Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate IR mapping/ROI publication promotion on an immutable, accepted,
source-matching scientific review record while preserving the typed mapping
boundary and invalid-pixel mask.

**Architecture:** `IRMappingResult.provenance` is the only input boundary for
an optional serialized `ScientificReviewRecord`. The mapping provider restores
that record, calls the shared fail-closed `promotion_decision`, and uses the
result only to select publication roles and emit JSON-safe evidence. The
engine copies the same snapshot into `AnalysisResult` so history/export can
trace the decision without reimplementing scientific rules in the GUI.

**Tech Stack:** Python dataclasses, NumPy, pytest, shared FigureDefinition and
AnalysisResult contracts.

---

### Task 1: Define the RED contract

**Files:**
- Modify: `tests/test_ir_mapping.py`
- Reference: `polynexus/core/scientific_review.py`

- [ ] **Step 1: Add fixtures for pending and accepted review payloads.**
  Use a dictionary shaped exactly like `ScientificReviewRecord.to_dict()` and
  attach it under `provenance["scientific_review"]`.
- [ ] **Step 2: Add tests for no review, accepted review, source mismatch, and
  JSON round-trip.** Assert denied roles, promoted roles, decision reason, and
  `json.dumps(..., allow_nan=False)` success.
- [ ] **Step 3: Run the focused tests and verify the new assertions fail because
  the provider currently always publishes Main/SI.**

### Task 2: Implement the smallest provider gate

**Files:**
- Modify: `polynexus/core/ir_engine/ir_mapping.py`
- Modify: `polynexus/core/ir.py`

- [ ] **Step 1: Restore a review record from the optional provenance mapping.**
  Missing/invalid payloads become `None` for the shared fail-closed decision;
  valid records are reconstructed with normalized tuple fields.
- [ ] **Step 2: Build one decision snapshot containing `allowed`, `reason`,
  `record_id`, `scope`, and `source_ref`; never mutate mapping arrays.
- [ ] **Step 3: Apply roles: accepted/source-matching map=`main`, ROI=`si`;
  every denied map/ROI=`diagnostic`; invalid-pixels always=`diagnostic`.
- [ ] **Step 4: Add the decision snapshot to evidence and every mapping recipe,
  and copy it into the engine's `analysis_evidence` and metadata handoff.

### Task 3: GREEN and compatibility verification

**Files:**
- Modify: `tests/test_ir_mapping.py`
- Create: `docs/acceptance/2026-07-29-ir-mapping-scientific-review-gate.md`

- [ ] **Step 1: Run the focused IR and shared scientific-review tests.**
- [ ] **Step 2: Run the structured changed/type verifier and boundary audit.**
- [ ] **Step 3: Record exact outputs, limitations, and pre-existing changes in
  the acceptance note.
- [ ] **Step 4: Create one explicit-allowlist checkpoint with
  `scripts/auto_commit.py`; do not stage unrelated worktree artifacts.

### Self-review checklist

- [ ] Coordinates are consumed as supplied.
- [ ] Invalid pixels remain masked and diagnostic.
- [ ] Only accepted + matching + complete review records promote.
- [ ] Figure recipes/evidence are JSON-safe and source-traceable.
- [ ] No GUI-specific scientific branching was added.
