 # SAXS Static Method Evidence Diagnostic Figure Implementation Plan

 > **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

 **Goal:** Project existing static per-frame Porod, Kratky, invariant, and lamellar evidence into a diagnostic Figure without recalculation or promotion.

 **Architecture:** Add a private static-provider helper beside the existing static Figure builders. It reads `SAXSFrameView.index`, `source_path`, and `analysis.metric_evidence`, builds detached nullable audit sources and finite plot sources, then appends the definition before the existing role/order polishing and evidence attachment.

 **Tech Stack:** Python, NumPy, immutable Figure contracts, pytest, repository verifier.

 ---

 ### Task 1: Write the static method-evidence regression tests

 **Files:**
 - Modify: `tests/test_saxs_static_figure_panels.py`

 - [ ] **Step 1: Add an evidence-bearing engine fixture helper and tests**

 Add a `metric_evidence` mapping to a copied static fixture and assert the new
 Figure ID, four audit sources, nullable values, finite plot projection,
 diagnostic role, recipe boundary, strict JSON, v2 validation, and input
 detachment. Keep the existing no-evidence fixture assertions unchanged.

 - [ ] **Step 2: Run the focused tests and confirm RED**

 Run:

 ```powershell
 python -m pytest -q tests/test_saxs_static_figure_panels.py -o addopts= -k method_evidence
 ```

 Expected result: the new tests fail because
 `saxs.static.method_evidence` is not yet emitted; no production code is changed
 before this failure is observed.

 ### Task 2: Implement the minimal static provider projection

 **Files:**
 - Modify: `polynexus/core/saxs_engine/figure_static.py`

 - [ ] **Step 1: Define the supported method metadata**

 Add a private tuple matching the existing temperature method contract:
 `porod/a.u.`, `kratky/nm^-1`, `invariant/a.u.`, and `lamellar/nm`.

 - [ ] **Step 2: Add the projection helper**

 Read only `frame.analysis.metric_evidence`. For each method and frame, append
 a nullable audit row and append a plot pair only when both `frame.index` and
 the existing `value` are finite. Convert reason-code sequences to the same
 pipe-delimited representation used by the temperature provider. Emit a plot
 source only when it has at least one finite pair, so an audit-only method does
 not create an empty V2 renderer source. Return `None` when no supported
 mapping exists anywhere.

 - [ ] **Step 3: Append the diagnostic definition**

 Add the helper result to `definitions` before existing diagnostics, preserving
 the current sorting and `attach_saxs_figure_evidence` call. Use four panels and
 the recipe flags from the spec. Do not alter existing definitions.

 - [ ] **Step 4: Run focused GREEN tests**

 Run:

 ```powershell
 python -m pytest -q tests/test_saxs_static_figure_panels.py -o addopts= -k method_evidence
 ```

 Expected result: all new static method-evidence tests pass.

 ### Task 3: Verify the atomic task and checkpoint it

 **Files:**
 - Modify: `polynexus/core/saxs_engine/figure_static.py`
 - Modify: `tests/test_saxs_static_figure_panels.py`
 - Add: `docs/agent/tasks/2026-07-31-saxs-static-method-evidence.md`
 - Add: `docs/superpowers/specs/2026-07-31-saxs-static-method-evidence-design.md`
 - Add: `docs/superpowers/plans/2026-07-31-saxs-static-method-evidence.md`
 - Add: `docs/acceptance/2026-07-31-saxs-static-method-evidence.md`

 - [ ] **Step 1: Run the task-scoped checks**

 Run the focused static matrix, structured changed/type verifier, exact SAXS
 matrix, storage report and non-destructive clean dry-run, and `git diff
 --check`. Record exact outcomes, including any timeout without a pytest final
 summary.

 - [ ] **Step 2: Review the diff and explicit allowlist**

 Ensure the allowlist contains only the six task files above. Leave the
 pre-existing `active-work.md`, `current-state.md`, `.superpowers/`, test
 directories, and parallel SAXS EDF files untouched.

 - [ ] **Step 3: Create the checkpoint**

 ```powershell
 python scripts/auto_commit.py --message "feat(saxs): add static method evidence figure" --files polynexus/core/saxs_engine/figure_static.py tests/test_saxs_static_figure_panels.py docs/agent/tasks/2026-07-31-saxs-static-method-evidence.md docs/superpowers/specs/2026-07-31-saxs-static-method-evidence-design.md docs/superpowers/plans/2026-07-31-saxs-static-method-evidence.md docs/acceptance/2026-07-31-saxs-static-method-evidence.md
 ```

 Expected result: one local atomic commit; no push, merge, or cleanup apply.
