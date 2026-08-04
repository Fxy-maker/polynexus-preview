# PolyNexus SAXS and AI Presentation Depth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing 46-slide PolyNexus HTML presentation so the SAXS chapter explains its real processing chain and the AI chapter explains the controlled LLM/RAG/orchestrator architecture with a concrete simulated-data rescue case.

**Architecture:** Keep the single-file fixed 1920x1080 presentation and its five-chapter metadata. Reuse the existing electronic-magazine visual system, slide navigation, captions, speaker notes, flow ribbons, and reduced-motion behavior. The content change is limited to slide markup, inline CSS/JS-free visual diagrams, focused regression assertions, and durable activity memory.

**Tech Stack:** Self-contained HTML/CSS, inline SVG/CSS diagrams, existing presentation navigation engine, pytest string/structure regression tests, Playwright CLI visual checks.

---

### Task 1: Lock the new narrative contract in tests

**Files:**
- Modify: `tests/test_html_presentation.py`

- [x] **Step 1: Add assertions for the SAXS processing chain.**

Assert that the presentation contains the implemented chain terms and status language: `CSV`, `DAT`, `TXT`, `XY`, `pyFAI`, `q-window`, `beamstop`, `transmission`, `Savitzky-Golay`, `Guinier`, `Porod`, `Bragg`, `Lorentz`, `IDF`, `invariant Q`, `Quantitative`, `Trend`, `Diagnostic`, and `Unusable`.

- [x] **Step 2: Add assertions for the simulated comparison and AI rescue story.**

Assert that the HTML contains `simulated teaching data`, `ideal curve`, `problem curve`, `beamstop`, `background drift`, `peak overlap`, `candidate`, `shadow`, `confirm-only`, `RAG`, `AI Advisor`, `deterministic orchestrator`, `keep_original`, and `user confirmation`.

- [x] **Step 3: Run the focused test before implementation.**

Run: `pytest tests/test_html_presentation.py -q`

Expected: the new assertions fail because the current deck does not yet contain the complete contract.

### Task 2: Expand SAXS processing and method teaching slides

**Files:**
- Modify: `docs/presentations/polynexus-overview.html`

- [x] **Step 1: Replace the early SAXS setup slides with the actual processing chain.**

Use the existing SAXS chapter slots to show: supported 1D inputs and 2D-to-I(q) integration; pyFAI/manual q conversion and geometry prerequisites; geometry/polarization limitations; background/transmission/thickness normalization; smoothing and mask/beamstop boundaries; q-window selection and method-specific eligibility.

- [x] **Step 2: Keep the model map and six method pages, but make each page answer four questions.**

For Guinier, Porod, Bragg, Lorentz, IDF/correlation function, and invariant Q, show the scientific question, core relation or transform, output parameters, and one explicit applicability/failure boundary. State that `sasmodels` is a partial/advanced route and is not the default for every static 1D entry.

- [x] **Step 3: Add the semi-crystalline/layered polymer simulated comparison.**

Use a clean explanatory curve and a problem curve with a sharp Bragg peak plus a broad correlation peak. The problem state adds low-q beamstop truncation, background drift/non-matched subtraction, peak overlap, noise, and outliers. Label values as illustrative simulation values, then show ideal evidence versus degraded evidence.

- [x] **Step 4: Add the partial-availability quality contract.**

Explain that the current system is not uniformly fail-closed: input-level geometry errors may stop a path, method-level shortages may return empty/NaN, and other methods may continue with `Diagnostic` evidence. Show `Quantitative / Trend / Diagnostic / Unusable`, `quality_flag`, `metric_evidence`, `Q_star_valid`, and formal publication-figure restrictions.

### Task 3: Rewrite the AI chapter around the concrete SAXS rescue flow

**Files:**
- Modify: `docs/presentations/polynexus-overview.html`

- [x] **Step 1: Introduce the AI value proposition.**

Explain that AI reads heterogeneous evidence and maps symptoms to a bounded adjustment direction; it does not replace candidate generation, parameter validation, rerun execution, quality gates, or scientific adoption.

- [x] **Step 2: Show the actual architecture.**

Render the chain `evidence → AI Advisor → structured JSON → whitelist/type/range/dependency validation → deterministic candidate generation → rerun → physical/quality gates → accept/rollback/confirm`. Include configurable LLM API, Chroma/BM25 case retrieval, no raw-curve/document RAG claim, and offline mock behavior when the model is unavailable.

- [x] **Step 3: Show the SAXS preprocessing rescue as a constrained branch.**

Use `PreprocessIntent` examples such as weakening smoothing, protecting the Guinier region, or handling low-q contamination. Make clear that deterministic services generate concrete values and that `shadow`/`confirm-only` is the default safety posture for the SAXS rescue path.

- [x] **Step 4: Show user review and failure handling.**

Include the result-page entry, independent tuning report, before/after candidate table, risks, rollback status, `keep_original`, user confirmation, and per-failure fallbacks: mock/no changes, candidate rejection, or confirmation request. Preserve the statement that core analysis is independent of AI/RAG/API availability.

### Task 4: Verify presentation behavior and repository contract

**Files:**
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/superpowers/plans/2026-08-03-polynexus-presentation-saxs-ai-depth.md`

- [x] **Step 1: Run static checks.**

Run: `pytest tests/test_html_presentation.py -q`; parse inline scripts with Node `vm.Script`; run `git diff --check`.

- [x] **Step 2: Run browser checks.**

Attempted with the local server at `http://127.0.0.1:8765/docs/presentations/polynexus-overview.html`. The static server returned the deck successfully, but the Codex in-app browser blocked localhost navigation by policy, so screenshot and viewport checks remain an environment limitation.

- [x] **Step 3: Run repository verification.**

Run: `python scripts/verify.py --changed --types`

Expected: selected checks pass, including the repository quality and preprocessing gates.

- [x] **Step 4: Update durable activity memory.**

Record the new SAXS processing chain, simulated comparison, AI architecture, visual evidence, verification commands, and known limitation that method-level quality behavior is not fully uniform.

- [ ] **Step 5: Create the atomic checkpoint.**

Run `scripts/auto_commit.py` with an explicit allowlist containing the HTML, focused test, plan, and activity-memory files. Do not stage pre-existing unrelated changes or untracked test artifacts.
