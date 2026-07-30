# NMR embedded axis declaration implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the unit-bearing JEOL/Delta x-axis declaration visible as provenance without applying unverified origin semantics.

**Architecture:** Parse the vendor `acquisition` text in `nmr_engine.io`, carry the JSON-safe declaration through the existing NMR run evidence projection, and render it in the existing Results review summary. Keep the numerical axis and scientific gates unchanged.

**Tech Stack:** Python, regular expressions scoped to the vendor acquisition block, existing NMR evidence contracts, pytest, PySide6 i18n.

---

### Task 1: Establish real-file and consumer regressions

**Files:**
- Modify: `tests/test_nmr_engine.py`
- Modify: `tests/test_analysis_evidence.py`
- Modify: `tests/test_results_review_service.py`

- [x] Add real solid 13C and 1H assertions for vendor dimension, domain, origin field/value, sweep field/value, units, and points.
- [x] Add a malformed/non-ppm rejection case.
- [x] Add evidence and Results assertions for the explicit declaration.
- [x] Run the new tests once and record the expected missing-metadata/consumer RED result.

### Task 2: Parse and project the declaration

**Files:**
- Modify: `polynexus/core/nmr_engine/io.py`
- Modify: `polynexus/core/nmr.py`
- Modify: `polynexus/core/analysis_evidence_nmr.py`

- [x] Parse only the `acquisition ... end acquisition` block and retain complete ppm declarations.
- [x] Attach `vendor_axis_declaration` to the loaded spectrum and copy it into NMR output parameters.
- [x] Publish it under `axis_evidence.vendor_declaration` without changing `ppm_axis_*` or Xc behavior.

### Task 3: Render and verify

**Files:**
- Modify: `polynexus/gui/results_review_service.py`
- Modify: `polynexus/gui/i18n.py`
- Create: `docs/acceptance/2026-07-30-nmr-embedded-axis-declaration.md`

- [x] Render dimension, domain, origin field/value, sweep field/value, points, and not-applied status in Results review.
- [x] Run the full focused NMR matrix, native solid-C route, structured verifier, diff check, and storage report.
- [x] Create one explicit allowlist checkpoint containing only this task's files (final `HEAD`).
