# Evidence-Grounded Paper Generation Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a usable, evidence-grounded paper draft in one controlled run while preserving reproducible figures, formulas, citations, and document layout.

**Architecture:** Keep PolyNexus Core as the deterministic producer of runs, metrics, tables, and evidence. Add a Suite paper pipeline that consumes those contracts and emits versioned manuscript-source and FigurePlan objects; ARS handles research prose, Zotero/CSL handles citations, and preflight validates the final export. GUI and CLI remain thin consumers of shared DTOs.

**Tech Stack:** Python dataclasses/JSON, existing evidence package contracts, Matplotlib/SVG rendering, optional Zotero/CSL adapters, python-docx or existing document exporters, pytest.

---

### Task 1: Define manuscript-source and review contracts

**Files:**
- Create: `polynexus/suite/paper_contracts.py`
- Create: `tests/test_paper_contracts.py`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Write failing tests** for round-tripping `PaperBrief`, `ClaimRecord`, `FigurePlan`, `CitationRequest`, `ManuscriptSource`, and `PreflightReport`, including schema version and stable IDs.
- [ ] **Step 2: Run** `python -m pytest -p no:cacheprovider -q tests/test_paper_contracts.py`; confirm RED because contracts do not exist.
- [ ] **Step 3: Implement** frozen dataclasses with strict required fields, JSON-safe `to_dict/from_dict`, and no scientific calculations.
- [ ] **Step 4: Re-run** the focused test; expected GREEN.
- [ ] **Step 5: Checkpoint** with `scripts/auto_commit.py` using only the listed files.

### Task 2: Build evidence-to-manuscript-source bridge

**Files:**
- Create: `polynexus/suite/paper_source.py`
- Create: `tests/test_paper_source.py`
- Modify: `polynexus/cli/run_suite_service.py`
- Modify: `polynexus/gui/suite_manager_adapter.py`

- [ ] **Step 1: Write failing tests** proving a valid evidence package produces claims linked to metric IDs, table IDs, figure IDs, and review boundaries, while missing or diagnostic metrics cannot be promoted.
- [ ] **Step 2: Run** the focused source tests and verify RED.
- [ ] **Step 3: Implement** a read-only bridge that calls `load_evidence_package_view()` and projects `ManuscriptSource`; never recompute or copy raw files.
- [ ] **Step 4: Re-run** source and existing handoff tests; expected GREEN.
- [ ] **Step 5: Checkpoint** the bridge and tests.

### Task 3: Add FigurePlan-driven candidate rendering

**Files:**
- Create: `polynexus/suite/figure_plans.py`
- Create: `polynexus/suite/figure_quality.py`
- Create: `tests/test_figure_plans.py`
- Create: `tests/test_figure_quality.py`

- [ ] **Step 1: Write failing tests** for FigurePlan validation, SVG-first output, optional PNG/PDF generation, source-data binding, and checks for labels, units, clipping, overlap, dimensions, and duplicate logical figures.
- [ ] **Step 2: Run** focused tests and verify RED.
- [ ] **Step 3: Implement** layout-family recipes and a renderer that emits one logical figure bundle; default output is SVG plus JSON, with PNG/PDF/CSV generated only by explicit profile or request.
- [ ] **Step 4: Re-run** focused tests and existing figure-index tests; expected GREEN.
- [ ] **Step 5: Checkpoint** figure contracts, renderer, quality checks, and tests.

### Task 4: Add AI ranking and human figure decisions

**Files:**
- Create: `polynexus/suite/figure_review.py`
- Create: `tests/test_figure_review.py`
- Modify: `polynexus/suite/handoff.py`

- [ ] **Step 1: Write failing tests** for deterministic machine reports, AI candidate ranking as advisory-only, human selection persistence, and rejection of unbound or diagnostic-only promotion.
- [ ] **Step 2: Run** focused tests and verify RED.
- [ ] **Step 3: Implement** review DTOs and append-only decisions linked to FigurePlan IDs; do not mutate immutable evidence.
- [ ] **Step 4: Re-run** focused review/package tests; expected GREEN.
- [ ] **Step 5: Checkpoint** review service and tests.

### Task 5: Add Zotero dynamic and CSL static citation adapters

**Files:**
- Create: `polynexus/suite/citations.py`
- Create: `tests/test_suite_citations.py`
- Modify: `polynexus/suite/paper_source.py`

- [ ] **Step 1: Write failing tests** for Zotero detection, unresolved-key handling, dynamic-field requests, CSL static rendering with a fixture bibliography, and `.bib`/`.json` export.
- [ ] **Step 2: Run** focused citation tests and verify RED.
- [ ] **Step 3: Implement** Zotero as the authoritative dynamic source; when unavailable, render static citations through a pinned CSL style and preserve the same keys. Never fabricate missing metadata.
- [ ] **Step 4: Re-run** citation and ARS handoff tests; expected GREEN.
- [ ] **Step 5: Checkpoint** citation adapters and tests.

### Task 6: Add formula objects and whole-paper writing orchestration

**Files:**
- Create: `polynexus/suite/formulas.py`
- Create: `polynexus/suite/paper_pipeline.py`
- Create: `tests/test_formula_contracts.py`
- Create: `tests/test_paper_pipeline.py`

- [ ] **Step 1: Write failing tests** for formula variable/unit validation, chapter contracts, paragraph roles, and evidence-first draft assembly.
- [ ] **Step 2: Run** focused tests and verify RED.
- [ ] **Step 3: Implement** formula and section DTOs plus a Suite orchestrator that routes ARS phases internally: argument planning, evidence-grounded drafting, claim audit, scientific humanization, and preflight.
- [ ] **Step 4: Re-run** focused tests; expected GREEN.
- [ ] **Step 5: Checkpoint** orchestration and tests.

### Task 7: Add manuscript preflight and document export

**Files:**
- Create: `polynexus/suite/preflight.py`
- Create: `tests/test_manuscript_preflight.py`
- Modify: `polynexus/cli/run_suite_service.py`
- Modify: `polynexus/gui/suite_manager_adapter.py`

- [ ] **Step 1: Write failing tests** for claim/metric links, formula/citation/figure consistency, document asset presence, and PDF render checks.
- [ ] **Step 2: Run** focused tests and verify RED.
- [ ] **Step 3: Implement** deterministic preflight reports and non-destructive export from manuscript-source. Insert SVG or high-resolution PNG into DOCX; export whole-document PDF for visual QA; do not default-insert per-figure PDFs or rewrite existing DOCX in place.
- [ ] **Step 4: Re-run** preflight, existing evidence, CLI, and GUI adapter tests; expected GREEN.
- [ ] **Step 5: Checkpoint** preflight/export changes.

### Task 8: PA6 six-sample end-to-end pilot

**Files:**
- Create: `docs/acceptance/2026-08-29-pa6-paper-pipeline-pilot.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1:** Read the existing v011 package without modifying raw data.
- [ ] **Step 2:** Generate PaperBrief, FigurePlans, manuscript-source, citations, and draft through the shared Suite route.
- [ ] **Step 3:** Run all preflight checks and render the draft to PDF.
- [ ] **Step 4:** Compare defects and revision categories with the historical direct-AI manuscript workflow.
- [ ] **Step 5:** Record human decisions, limitations, exact commands, and whether the draft is suitable for further scientific review.
