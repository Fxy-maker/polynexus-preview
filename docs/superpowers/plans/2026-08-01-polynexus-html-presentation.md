# PolyNexus HTML Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** Build a self-contained, narrated-video-ready HTML deck explaining PolyNexus's scientific analysis design and AI-assisted parameter workflow.

**Architecture:** One fixed-stage HTML file owns slide markup, inline SVG diagrams, CSS theme, navigation, motion, captions, and speaker notes. A focused pytest smoke test checks the artifact contract; browser inspection checks rendered geometry and interaction.

**Tech Stack:** HTML, inline CSS, inline SVG, vanilla JavaScript, pytest smoke test, Chromium/browser inspection.

---

### Task 1: Establish the artifact contract

**Files:**
- Create: `tests/test_html_presentation.py`
- Create: `docs/presentations/polynexus-overview.html`

- [x] **Step 1: Write the failing smoke test**

Assert that the presentation file exists, is a complete HTML document, contains
18-20 fixed-stage slides, has keyboard/touch navigation hooks, includes
`prefers-reduced-motion`, and includes notes/subtitle data.

- [x] **Step 2: Run the smoke test and confirm the expected missing-file failure**

Run: `pytest tests/test_html_presentation.py -q`

Expected: FAIL because `docs/presentations/polynexus-overview.html` does not yet exist.

### Task 2: Implement the editorial fixed-stage deck

**Files:**
- Modify: `docs/presentations/polynexus-overview.html`

- [x] **Step 1: Add the stage, theme, and motion primitives**

Use a 1920x1080 `.deck-stage`, paper/ink variables, Google-font links with local
fallbacks, inline SVG utility classes, reduced-motion rules, and non-scrolling
slide visibility controlled by `.active`/`.visible`.

- [x] **Step 2: Add the approved slide narrative**

Create title, pain, origin, design contract, SAXS divider, physical intuition,
q/I(q), method map, complementary fits, quality states, temperature/strain,
multiscale technique map, shared result contract, AI loop, multi-objective
optimum, workflow surfaces, future tutorial split, and closing slides.

- [x] **Step 3: Add navigation and narration controls**

Implement Arrow/PageUp/PageDown/Space/Home/End, touch swipe, wheel throttling,
progress, dots, counter, `N` notes mode, `C` captions mode, and `R` replay.

- [x] **Step 4: Add section-specific motion**

Use staggered editorial reveals, SVG stroke drawing for curves/connectors,
sequential method cards, and a traced AI loop. Ensure the deck remains legible
when motion is disabled.

### Task 3: Verify layout and browser behavior

**Files:**
- Modify: `tests/test_html_presentation.py` only if a contract gap is found.

- [x] **Step 1: Run the focused smoke test and inspect the output**

Run: `pytest tests/test_html_presentation.py -q`

Expected: PASS with no failures.

- [x] **Step 2: Run the repository verifier**

Run: `python scripts/verify.py --changed --types`

Report the exact exit code and any pre-existing workspace noise separately.

- [x] **Step 3: Open the deck in a real browser**

Verify the first, middle, AI, and closing slides at desktop and phone viewport
sizes. Check stage scaling, text containment, no overlap, no console errors,
keyboard/touch navigation, notes/captions, and reduced-motion behavior.

- [x] **Step 4: Run the available Swiss-layout validator**

Run: `node "$env:USERPROFILE/.codex/skills/guizang-ppt/scripts/validate-swiss-deck.mjs" docs/presentations/polynexus-overview.html`

Treat validator warnings as review items; the selected editorial direction may
not satisfy Swiss-only registration rules, so supplement it with browser evidence.

- [x] **Step 5: Create the local checkpoint**

Run `python scripts/auto_commit.py` with an explicit allowlist containing only
the task card, spec, plan, presentation, and focused test after all checks pass.
