# SAXS AI Rescue Figure/Manifest Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve a compact, read-only projection of existing SAXS AI rescue audits in FigureDefinition recipes and Manifest-backed figure documents.

**Architecture:** `figure_provider` copies the four existing engine audit fields and passes them to the existing `figure_evidence` boundary. `figure_evidence` projects only audit metadata into `recipe.evidence.quality_provenance.ai_rescue`, leaving figure roles, frame selection, and the authoritative Export quality bundle unchanged.

**Tech Stack:** Python, strict JSON-safe figure contracts, FigurePipeline, pytest, Ruff, `scripts/verify.py`, and `scripts/auto_commit.py`.

---

### Task 1: Add the audit contract and RED tests

**Files:**
- Create: `docs/superpowers/specs/2026-07-28-saxs-ai-rescue-figure-manifest-provenance-design.md`
- Create: `docs/superpowers/plans/2026-07-28-saxs-ai-rescue-figure-manifest-provenance.md`
- Create: `docs/agent/tasks/2026-07-28-saxs-ai-rescue-figure-manifest-provenance.md`
- Test: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Add a provider binding regression.**

  Give `_static_engine()` a plan, decision, replay, and confirmed-rerun audit.
  Build static definitions and assert the first definition contains
  `recipe["evidence"]["quality_provenance"]["ai_rescue"]` with the candidate
  ID, `request_confirmation`, replay status, and rollback phase while the
  publication role remains `main`.

- [x] **Step 2: Add strict/detached and malformed regressions.**

  Call `build_saxs_figure_evidence((frame,), mode="static", ai_rescue=source)`;
  run `json.dumps(..., allow_nan=False)`, mutate the source after projection,
  and assert the projected compact record is unchanged. Pass lists/strings or
  mappings without identifiers and assert no `ai_rescue` record is created.

- [x] **Step 3: Add Manifest retention regression.**

  Run `FigurePipeline().run(...)` for a definition with AI provenance, read the
  generated `figure.pnfig.json`, and assert the same compact record is present
  under the recipe evidence without raw candidate configuration fields.

- [x] **Step 4: Run RED.**

  ```powershell
  $env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_ai_figure_red'
  python -m pytest -q tests/test_saxs_figure_evidence_binding.py
  ```

  Expected: the new tests fail because `build_saxs_figure_evidence` does not
  accept `ai_rescue` and providers do not pass the engine audit.

### Task 2: Implement compact figure provenance

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_evidence.py`
- Modify: `polynexus/core/saxs_engine/figure_provider.py`
- Modify: `polynexus/core/saxs_engine/figure_static.py`
- Modify: `polynexus/core/saxs_engine/figure_temperature.py`
- Modify: `polynexus/core/saxs_engine/figure_strain.py`

- [x] **Step 1: Add a pure projection helper.**

  Implement `_project_ai_rescue_evidence(payload)` with explicit field
  allowlists. Keep candidate IDs and statuses only; omit full `intent`,
  `candidates`, configs, arrays, and non-mapping rows. Convert values through
  the existing `_json_safe` helper and return `{}` when no valid section exists.

- [x] **Step 2: Extend the evidence boundary additively.**

  Add `ai_rescue: Mapping[str, Any] | None = None` to
  `build_saxs_figure_evidence` and `attach_saxs_figure_evidence`. Add the
  projected record only when non-empty. Keep the existing failure fallback and
  `quality_evidence_file` unchanged.

- [x] **Step 3: Pass existing engine state from all providers.**

  In each existing provider call, pass
  `copy_saxs_ai_rescue_evidence(engine_state, getattr(engine_state, "result", None))`.
  Do not read or branch on audit fields in eligibility or role calculation.

- [x] **Step 4: Run GREEN.**

  ```powershell
  $env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_ai_figure_green'
  python -m pytest -q tests/test_saxs_figure_evidence_binding.py
  ```

  Expected: all figure evidence and Manifest regressions pass.

### Task 3: Verify and checkpoint

**Files:**
- All files in the explicit allowlist in the task card.

- [x] **Step 1: Run the focused consumer matrix.**

  Run the figure evidence, provider, figure document, and Export tests with a
  dedicated basetemp; record the exact result.

- [x] **Step 2: Run the exact SAXS matrix and task verifier.**

  Run the PowerShell-expanded `tests/test_saxs_*.py` matrix and
  `python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-ai-rescue-figure-manifest-provenance.md --changed --types`, then run `git diff --check`. Do not claim full/boundary unless it completes in this task.

- [x] **Step 3: Create one explicit allowlist checkpoint.**

  Use `scripts/auto_commit.py` with only the task card, spec, plan, figure
  projector/provider, and focused test. Leave release-audit, GUI, memory,
  scratch, and generated files untouched.
