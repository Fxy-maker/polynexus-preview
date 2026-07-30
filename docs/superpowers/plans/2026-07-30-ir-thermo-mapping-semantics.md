# IR Thermo/OMNIC Mapping Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the official Thermo/OMNIC Picta mapping coordinate and ROI rules visible in IR mapping evidence and figure recipes without inventing sample-specific metadata.

**Architecture:** Keep the existing `IRMappingResult` as the data contract. Add a small immutable semantics factory in the IR mapping module, attach its JSON-safe payload to evidence and figure recipes, and use it only as documented semantic context. Existing arrays, masks, and review gating remain authoritative for data and release status.

**Tech Stack:** Python dataclasses, NumPy, pytest, existing FigureDefinition contracts.

---

### Task 1: Add the official semantics profile contract

**Files:**
- Modify: `polynexus/core/ir_engine/ir_mapping.py`
- Test: `tests/test_ir_mapping.py`

- [x] **Step 1: Write the failing tests**

Add tests that call `official_thermo_omnic_picta_semantics()` and assert the
profile id, X/Y row-column mapping, origin, `um` unit, unknown serialization
order, unverified status, and JSON round-trip.

- [x] **Step 2: Run the focused tests and verify the expected failure**

Run:
`python -m pytest tests/test_ir_mapping.py -k thermo_omnic_picta -q`

Expected: failure because the semantics factory does not yet exist.

- [x] **Step 3: Implement the minimal JSON-safe profile**

Add a function returning a new dictionary on every call with stable keys:
`profile_id`, `spatial_axes`, `origin`, `roi`, `serialization`, and `status`.
Use `origin.kind = "stage_home"`, `origin.x = 0.0`, `origin.y = 0.0`,
`spatial_axes.x.coordinate_role = "column"`,
`spatial_axes.y.coordinate_role = "row"`, and
`serialization.order = "unknown_without_vendor_map"`.

- [x] **Step 4: Run the focused tests and verify they pass**

Run the same focused command and expect all selected tests to pass.

### Task 2: Publish semantics through evidence and figure recipes

**Files:**
- Modify: `polynexus/core/ir_engine/ir_mapping.py`
- Test: `tests/test_ir_mapping.py`

- [x] **Step 1: Write failing assertions**

Assert `IRMappingResult.to_evidence()` exposes `mapping_semantics`, and every
figure definition recipe exposes the same profile. Assert map source column
units are `um` and the map layout labels are `X position (um)` and
`Y position (um)`.

- [x] **Step 2: Run the focused tests and verify the expected failure**

Run:
`python -m pytest tests/test_ir_mapping.py -k "semantics or axis" -q`

Expected: failure because the existing evidence and recipes do not expose the
official profile or labels.

- [x] **Step 3: Implement the handoff**

Create one profile per result build, put it in `mapping_evidence`, copy it into
`recipe_base`, use it for the map and invalid-pixel source units, and update the
map/invalid-pixel layouts. Keep the profile status unverified and do not alter
the `scientific_review` decision.

- [x] **Step 4: Run mapping and lifecycle tests**

Run:
`python -m pytest tests/test_ir_mapping.py tests/test_ir_lifecycle_closure.py -q`

Expected: all tests pass.

### Task 3: Record acceptance evidence

**Files:**
- Create: `docs/acceptance/2026-07-30-ir-thermo-mapping-semantics.md`

- [x] **Step 1: Record the official source and data boundary**

Document the exact official URLs, the relevant printed pages, the absence of
vendor-native 2D files under `测试数据/IR`, and the resulting unverified fields.

- [x] **Step 2: Run the task verifier**

Run:
`python scripts/verify.py --task docs/agent/tasks/2026-07-30-ir-thermo-mapping-semantics.md --changed --types`

Expected: exit code 0 with Ruff, compile, type, quality, preprocessing, and
whitespace checks passing.

- [x] **Step 3: Create one explicit allowlist checkpoint**

After reviewing `git diff --check` and the verifier output, run
`python scripts/auto_commit.py --message "feat(ir): document thermo mapping semantics" --files polynexus/core/ir_engine/ir_mapping.py tests/test_ir_mapping.py docs/agent/tasks/2026-07-30-ir-thermo-mapping-semantics.md docs/superpowers/specs/2026-07-30-ir-thermo-mapping-semantics-design.md docs/superpowers/plans/2026-07-30-ir-thermo-mapping-semantics.md docs/acceptance/2026-07-30-ir-thermo-mapping-semantics.md`.

The checkpoint commit uses the explicit allowlist above and message
`feat(ir): document thermo mapping semantics`.
