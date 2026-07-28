# SAXS Static Publication Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended).

**Goal:** Bind Static SAXS Main publication role to existing explicit evidence authorization and fail closed when it is absent.

**Architecture:** Tighten the existing frame eligibility boundary and add only provider-side downgrade metadata. Figure data, evidence payloads, renderer, Manifest schema, and non-Static algorithms remain unchanged.

**Tech Stack:** Python, NumPy, immutable `FigureDefinition`, pytest, repository verifier.

---

### Task 1: Establish the Static role regression

**Files:**
- Create: `tests/test_saxs_static_publication_gate.py`
- Modify: `tests/test_saxs_mode_evidence_contract.py` only for explicit Static fixture authorization

- [x] Write tests for an explicit candidate-approved Static frame, an
  unqualified `quality_flag="OK"` frame, and an explicit candidate-rejected
  frame.
- [x] Run the focused tests with a new external basetemp and confirm RED: the
  unqualified `OK` frame currently becomes Main.
- [x] Add assertions that the provider keeps diagnostic definitions and that a
  no-Main pack exposes `no_publication_ready_figure` in recipe metadata.

### Task 2: Tighten existing eligibility without new thresholds

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_eligibility.py`

- [x] Keep the existing `ERROR` and explicit candidate-false branches first.
- [x] Keep explicit candidate-true plus existing reliability veto behavior.
- [x] Replace the implicit `quality_flag="OK"` Main fallback with an SI
  decision carrying a deterministic missing-authorization reason.
- [x] Run Task 1 tests and the existing mode evidence contract; confirm GREEN.

### Task 3: Record Static no-Main downgrade provenance

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_static.py`
- Test: `tests/test_saxs_static_publication_gate.py`

- [x] After building the unchanged definitions, detect the absence of a Main
  definition without removing any existing definition.
- [x] Add `no_publication_ready_figure=True` and
  `no_publication_ready_reason="static_frame_publication_authorization_missing"`
  to the affected recipe metadata only when no Main remains.
- [x] Preserve deterministic ordering, source values, and quality provenance.
- [x] Run Static provider/pipeline tests and strict JSON assertions.

### Task 4: Regression matrix and checkpoint

**Files:**
- Update: task/spec/plan and `docs/agent/memory/active-work.md`,
  `docs/agent/memory/current-state.md`

- [x] Run the focused Static/provider/figure matrix with an external basetemp.
- [x] Run all `tests/test_saxs*.py` with a fresh external basetemp.
- [x] Run `python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-static-publication-gate.md --changed --types` and `git diff --check`.
- [x] Run fresh `--full --boundary` verification in a writable isolated
  runtime environment: `2856 passed, 17 skipped, 14 warnings` in `1365.15s`;
  quality `283`, preprocessing `106`, and boundary audit passed.
- [x] Review the cumulative diff and keep the implementation checkpoint
  `63059d5` limited to the explicit allowlist.
- [x] Record the exact results and keep GUI/scientific human approval open.
