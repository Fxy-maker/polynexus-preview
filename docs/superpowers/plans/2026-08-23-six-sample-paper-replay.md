# Six-Sample Paper Evidence Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a fresh, source-hashed PolyNexus evidence package and writing plan for six PA samples, then perform a retrospective evidence-boundary comparison with the existing direct-AI manuscript.

**Architecture:** A new external project owns a frozen copy of the selected raw inputs and all derived content beneath `.polynexus`; no source-tree analysis outputs are mounted or copied. The project workflow is the sole producer of deterministic runs and the evidence package; ManuscriptPlan consumes that immutable package. The existing direct-AI document is read only after package finalization and is never supplied to the workflow.

**Tech Stack:** Existing PolyNexus CLI/project-workflow services, deterministic DSC/IR/SAXS/WAXS adapters, JSON manifests, evidence package/ARS contracts, and read-only DOCX extraction for retrospective comparison.

---

### Task 1: Freeze the approved raw-input scope

**Files:**
- Create: `D:\PA6-paper-replay-20260823\raw\...`
- Create: `D:\PA6-paper-replay-20260823\source-manifest.json`

- [x] **Step 1: Create the external project root and selected raw-data mirror**

Copy only the 12 DSC TXT, 246 FTIR CSV, 6 SAXS EDF, and 6 WAXS RAW inputs for
`PA6`, `PA6-50`, `PA11`, `PA11-50`, `PA12`, and `PA12-50`; retain source
relative paths and never copy `analysis_output`, `analysis_pipeline`,
`manuscript`, `.polynexus`, pytest, or legacy SPC files.

- [x] **Step 2: Record source hashes and exclusions**

Write a JSON manifest with original and mirrored paths, SHA-256, byte size,
technique, and the explicit excluded file classes. Abort if a copied file hash
does not match its source hash.

### Task 2: Inspect and select all six samples through public contracts

**Files:**
- Create: `D:\PA6-paper-replay-20260823\.polynexus\inventory\index.json`
- Create: `D:\PA6-paper-replay-20260823\analysis-request.json`

- [x] **Step 1: Run read-only project inspection on the frozen `raw` scope**

Persist the canonical inventory and retain all filename-derived group labels as
`inferred_from_filename`.

- [x] **Step 2: Persist one explicit six-sample AnalysisRequest**

Use the selected scope, request deterministic figures/tables/writing input,
and preserve the question as a comparative observation rather than a causal
claim.

### Task 3: Execute and validate deterministic technique routes

**Files:**
- Create: `D:\PA6-paper-replay-20260823\.polynexus\runs\...`
- Create: `D:\PA6-paper-replay-20260823\run-manifests\...`

- [x] **Step 1: Run DSC isothermal and thermal-cycle inputs for all samples**

Use the project workflow/provider routes, retaining any validation or
comparability limits in each run manifest.

- [x] **Step 2: Run all selected FTIR CSV temperature and time series**

Use only supported CSV sources; do not substitute or parse SPC mirrors.

- [x] **Step 3: Run SAXS and WAXS for all six samples**

Retain SAXS geometry/background and WAXS fit/quality review boundaries; do not
claim sample replication from one file per sample.

### Task 4: Package evidence and derive writing artifacts

**Files:**
- Create: `D:\PA6-paper-replay-20260823\.polynexus\evidence\...`
- Create: `D:\PA6-paper-replay-20260823\paper-brief.json`
- Create: `D:\PA6-paper-replay-20260823\manuscript-plan.json`

- [x] **Step 1: Build a new immutable evidence package**

Package only successful/review-bound runs and validate its manifest,
`figure-index.json`, `citation-metrics.json`, and `ars-writing-input.json`.

- [x] **Step 2: Create a conservative PaperBrief and build ManuscriptPlan**

Select only package-provided figures/evidence/metrics, preserve inherited
limitations, and write the plan outside the package directory.

### Task 5: Perform retrospective direct-AI comparison and report

**Files:**
- Create: `D:\PA6-paper-replay-20260823\direct-ai-comparison.json`
- Create: `D:\PA6-paper-replay-20260823\evidence-review.md`

- [x] **Step 1: Freeze the comparator identity**

Record the hash and document metadata for the newest direct-AI manuscript:
`manuscript\\TPAE_纯PA与PTMG引入_偶奇硬段差异化结晶响应_v47_ARS审稿修订_图片恢复_Zotero动态引文.docx`.

- [x] **Step 2: Compare only auditable claims and figure roles**

Map claims to new-package evidence IDs when possible; report missing provenance,
unsupported quantitative claims, omitted review limits, and evidence that is
newly available. Do not copy manuscript text or use it to alter analysis.

- [x] **Step 3: Verify and checkpoint task documentation**

Run the focused project/evidence/ManuscriptPlan tests, structured verifier,
and `git diff --check`; then create the allowlisted documentation checkpoint.
