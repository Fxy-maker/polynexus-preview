# NMR Vendor Real-Case Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Register the existing liquid/solid H/C NMR vendor inputs for real-engine evaluation while keeping their scientific truth unreviewed.

**Architecture:** Extend only the evaluation provenance schema and add immutable JSON case descriptors. A focused test loads all four descriptors and sends each source through the NMR engine into a pytest-owned external output directory; no source data or generated repository output is touched.

**Tech Stack:** Python, JSON Schema, pytest, existing NMR engine and EvalRunner.

---

### Task 1: Define the registry boundary

**Files:**
- Create: `docs/superpowers/specs/2026-07-31-nmr-vendor-real-case-registry-design.md`
- Create: `docs/superpowers/plans/2026-07-31-nmr-vendor-real-case-registry.md`
- Create: `docs/agent/tasks/2026-07-31-nmr-vendor-real-case-registry.md`
- Create: `docs/acceptance/2026-07-31-nmr-vendor-real-case-registry.md`
- Test: `tests/eval/test_nmr_vendor_real_case_registry.py`

- [x] **Step 1: Write the RED registry test**

Load the four expected files from `tests/eval/cases/real`, require
`source == "vendor_unreviewed"`, empty `ground_truth`, valid real-engine
dispatch, and run each source through `get_engine("nmr", submodule_id=...)`
with output under pytest's `tmp_path`.

- [x] **Step 2: Run RED**

Run `python -m pytest -q tests/eval/test_nmr_vendor_real_case_registry.py -vv`.
Before the implementation, collection or case loading must fail because the
registry files and provenance enum do not exist.

### Task 2: Implement the minimal registry

**Files:**
- Modify: `tests/eval/runner.py`
- Create: `tests/eval/cases/real/nmr_real_liquid_h_vendor.json`
- Create: `tests/eval/cases/real/nmr_real_liquid_c_vendor.json`
- Create: `tests/eval/cases/real/nmr_real_solid_h_vendor.json`
- Create: `tests/eval/cases/real/nmr_real_solid_c_vendor.json`

- [x] **Step 1: Add the provenance enum**

Allow `vendor_unreviewed` beside the existing provenance values in
`EvalRunner.EVAL_CASE_SCHEMA`; do not alter scoring or infer ground truth.

- [x] **Step 2: Add four descriptors**

Use relative paths under `NMR/` so `EvalRunner` resolves them from the project
test-data root. Keep `ground_truth` `{}` and include an explicit note that
scientific review is pending.

- [x] **Step 3: Run GREEN**

Run the focused registry test and confirm all four real inputs are parsed and
their output is written only below the supplied temporary directory.

### Task 3: Verify and checkpoint

**Files:**
- The source, test, four JSON descriptors, and four task documents above only.

- [x] **Step 1: Run focused tests**

Run `python -m pytest -q tests/eval/test_nmr_vendor_real_case_registry.py tests/eval/test_runner_real_nmr.py -vv`.

- [x] **Step 2: Run structured checks**

Run `python scripts/verify.py --task docs/agent/tasks/2026-07-31-nmr-vendor-real-case-registry.md --changed --types` and `git diff --check`.

- [x] **Step 3: Inspect storage without mutation**

Run `python scripts/test_storage.py report --json` and
`python scripts/test_storage.py clean --older-than-hours 24 --json` only.

- [x] **Step 4: Create one explicit checkpoint**

Use `scripts/auto_commit.py` with the exact changed-file allowlist. Do not
include memory edits, parallel SAXS files, real datasets, or scratch outputs.
