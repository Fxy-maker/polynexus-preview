# PolyNexus HTML Presentation Depth Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the existing 20-slide PolyNexus overview into the approved 46-slide SAXS-led research-principles master video.

**Architecture:** Keep the zero-dependency single HTML architecture. The existing fixed-stage presentation engine remains responsible for slide visibility, scale, navigation, captions, notes, and motion; the expansion adds structured slide metadata (`data-chapter`, `data-visual`) and content-specific CSS/inline SVG components inside the same file. The focused pytest contract verifies slide count and required scientific/narrative terms, while Playwright verifies rendered geometry and interactions.

**Tech Stack:** HTML, inline CSS, inline SVG, vanilla JavaScript, pytest, repository verifier, Playwright CLI.

---

## File Map

- Modify `docs/presentations/polynexus-overview.html`: replace the 20-slide body with the 46-slide outline, add formula/process/evidence components, and preserve the existing navigation engine.
- Modify `tests/test_html_presentation.py`: assert the expanded slide contract, chapter metadata, speaker notes, visual-role metadata, and scientific method coverage.
- Modify `docs/agent/tasks/2026-08-01-polynexus-html-presentation-depth.md`: record implementation evidence and the final commit.
- Modify `docs/agent/memory/active-work.md` only if its existing pre-existing worktree changes are reconciled safely; never stage unrelated memory changes.
- Do not modify analysis engines, GUI modules, real datasets, generated application outputs, or the previous 20-slide presentation commit history.

## Task 1: Lock the expanded artifact contract with a failing test

**Files:**
- Modify `tests/test_html_presentation.py`
- Test `docs/presentations/polynexus-overview.html`

- [ ] **Step 1: Change the slide-count expectation to the approved range.**

Replace the current `18 <= slide_count <= 20` assertion with `44 <= slide_count <= 48`, and add these exact checks:

```python
assert slide_count == 46
assert html.count('data-chapter=') == 46
assert html.count('data-visual=') == 46
assert html.count('data-notes=') == 46
```

- [ ] **Step 2: Add required scientific coverage assertions.**

Assert that the HTML contains `q = 4π sinθ / λ`, `Guinier`, `Porod`,
`Bragg`, `Lorentz`, `IDF`, `invariant`, `background subtraction`,
`temperature`, `strain`, `azimuthal`, `DSC`, `WAXS`, `IR`, `NMR`,
`fit quality`, `parameter stability`, `physical plausibility`, and
`data quality`.

- [ ] **Step 3: Run the focused test to confirm RED.**

Run:

```powershell
pytest tests/test_html_presentation.py -q
```

Expected result: failure because the current artifact still has 20 slides and
does not yet expose the expanded metadata/content contract.

## Task 2: Replace the slide body with the 46-slide narrative

**Files:**
- Modify `docs/presentations/polynexus-overview.html`

- [ ] **Step 1: Add a structured slide metadata convention.**

Every slide must start with the following shape, using the chapter number and
visual role from the approved spec:

```html
<section class="slide paper ..."
  data-chapter="02 / SAXS DEEP DIVE"
  data-visual="formula"
  data-caption="一句可直接作为字幕的主张。"
  data-notes="一段完整的配音讲稿，说明原理、输入、输出和限制。">
```

Use `data-visual` values from `formula`, `process`, `curve`, `comparison`,
`quality`, `hierarchy`, `screenshot-slot`, and `closing`.

- [ ] **Step 2: Implement slides 01-07 for the motivation and contract chapter.**

Use the approved titles and claims: fragmented research workflow, the cost of
manual analysis, the SAXS origin story, four design goals, the shared input to
export contract, and the full narrative map. Keep one claim per slide and use
short on-screen text with the longer explanation in `data-notes`.

- [ ] **Step 3: Implement slides 08-17 for SAXS intuition and data preparation.**

Add inline SVG diagrams for the scattering geometry and q/I(q) curve. Explain
the q equation, units, metadata, raw-data conversion, intensity correction,
normalization, background subtraction, q-window selection, smoothing, masks,
outliers, and the low/mid/high-q model map. Label all diagrams as explanatory
unless they are real GUI screenshot slots.

- [ ] **Step 4: Implement slides 18-27 for SAXS models and evidence.**

Create dedicated formula or diagnostic layouts for Guinier/Rg, I(0), Porod,
Porod exponent, Bragg/d-spacing, Lorentz correction, correlation/IDF,
invariant Q, complementary-method agreement, and quality states. Each method
slide must state its assumption or limitation in visible text or speaker notes.

- [ ] **Step 5: Implement slides 28-33 for sequence and 2D analysis.**

Add temperature and strain timeline diagrams, a 2D detector/azimuthal
integration sketch, a provenance/result-binding view, and a shared extension
contract. Preserve the boundaries: sequence changes conditions and tracks
evolution; 2D adds geometry and directional information; neither is presented
as a universal automatic interpretation.

- [ ] **Step 6: Implement slides 34-39 for the five-technique hierarchy.**

Use one hierarchy slide, one slide each for DSC, WAXS, and SAXS, one combined
IR/NMR slide, and one joint-context slide. Each technique gets its own input,
model/processing idea, output, and failure/review signal. The joint slide must
show that results share sample context while retaining technique-specific
semantics.

- [ ] **Step 7: Implement slides 40-46 for the AI advisor.**

Add a context-input diagram, candidate-generation flow, four-objective score
view, user-confirmation gate, bounded rerun, evidence-diff/audit view, and
closing/video-series slide. Explicitly show that AI suggestions are candidates,
not conclusions, and that user confirmation precedes rerun.

## Task 3: Add content-specific visual components and chapter chrome

**Files:**
- Modify `docs/presentations/polynexus-overview.html`

- [ ] **Step 1: Add reusable CSS primitives for the expanded content.**

Add fixed-stage-safe styles for `.formula-card`, `.equation`, `.process-strip`,
`.evidence-table`, `.assumption-note`, `.quality-state`, `.chapter-marker`,
`.screenshot-slot`, and `.chapter-label`. Keep the existing paper/ink palette,
avoid card nesting, and keep all slide content inside the 1920x1080 stage.

- [ ] **Step 2: Add chapter-aware presentation chrome.**

Update `updateChrome()` to set the current slide's `data-chapter` into a small
chapter label and keep the existing counter/caption/notes behavior. Add a
chapter-aware progress segment without changing arrow, space, Home/End, touch,
wheel, replay, reduced-motion, or edit-mode behavior.

- [ ] **Step 3: Add explanatory speaker notes and visual roles for all slides.**

Verify one `data-notes` and one `data-visual` value per slide. Notes must
mention the model limitation where the slide could otherwise be read as a
scientific guarantee. Screenshot slots must be explicit placeholders rather
than fabricated screenshots.

## Task 4: Make the expanded contract pass

**Files:**
- Modify `tests/test_html_presentation.py`
- Modify `docs/presentations/polynexus-overview.html` only for contract fixes

- [ ] **Step 1: Run the focused presentation test.**

Run `pytest tests/test_html_presentation.py -q`; expected result is `1 passed`
or more with zero failures.

- [ ] **Step 2: Run the HTML JavaScript syntax check.**

Extract the inline script and run `node --check` against the extracted file.
Expected result: exit code `0`.

- [ ] **Step 3: Run repository verification.**

Run `python scripts/verify.py --changed --types`. Expected result: selected
checks passed, with any unrelated pre-existing worktree changes reported
separately.

## Task 5: Verify real rendering and interaction before checkpoint

**Files:**
- Inspect `docs/presentations/polynexus-overview.html`
- Update `docs/agent/tasks/2026-08-01-polynexus-html-presentation-depth.md`

- [ ] **Step 1: Start or reuse a local static server.**

Serve `D:\PolyNexus` on an unused port and open
`/docs/presentations/polynexus-overview.html` in Chromium.

- [ ] **Step 2: Capture representative desktop screens.**

Inspect the title, SAXS formula, Guinier/Porod, quality, sequence/2D,
multi-technique, AI objective, and closing slides at 1280x720. Confirm text
does not overlap, formulas remain readable, and chapter markers do not enter
the bottom navigation safe area.

- [ ] **Step 3: Run an all-slide geometry scan.**

For each slide, call the existing `showSlide(index)` function and measure
descendant bounds relative to the 1920x1080 slide. Fail the check if any
descendant is outside the stage or if body scroll dimensions exceed the
viewport.

- [ ] **Step 4: Verify interaction and console state.**

Exercise ArrowRight/ArrowLeft, Home/End, `N`, `C`, `R`, touch swipe, and chapter
navigation. Confirm captions and notes update to the active slide and the
browser console has zero errors.

- [ ] **Step 5: Repeat the key checks at a phone viewport.**

Use a 390x844 viewport. The stage may letterbox because the deck remains fixed
16:9, but it must not reflow, horizontally scroll, overlap controls, or expose
content outside the stage.

## Task 6: Record evidence and create the checkpoint

**Files:**
- Modify `docs/agent/tasks/2026-08-01-polynexus-html-presentation-depth.md`

- [ ] **Step 1: Record exact test counts, browser checks, and limitations.**

Record the focused test result, repository verifier result, browser viewport
checks, and the limitation that explanatory diagrams can later be replaced by
real GUI screenshots.

- [ ] **Step 2: Run final diff checks.**

Run `git diff --check` and confirm only this task's files are staged.

- [ ] **Step 3: Create the explicit local checkpoint.**

```powershell
python scripts/auto_commit.py `
  --message "feat(presentation): expand PolyNexus deep-dive deck" `
  --files docs/agent/tasks/2026-08-01-polynexus-html-presentation-depth.md `
           docs/superpowers/specs/2026-08-01-polynexus-html-presentation-depth-design.md `
           docs/superpowers/plans/2026-08-01-polynexus-html-presentation-depth.md `
           docs/presentations/polynexus-overview.html `
           tests/test_html_presentation.py
```

Expected result: one local commit containing only the expanded deck, focused
test, plan, task evidence, and design documents; no push or merge.

## Task 7: Make the data flow visible and animate the lecture system

**Files:**
- Modify `docs/presentations/polynexus-overview.html`
- Modify `tests/test_html_presentation.py`

- [x] **Step 1: Add a persistent data-flow ribbon to lecture slides.**

The presentation engine should add one small fixed-stage ribbon to each
`lecture-slide`, with the stages `raw input`, `decision`, `model`, and
`quality / output`. `updateFlowRibbon()` should highlight the stage implied by
the slide visual role (`process`/`hierarchy` = decision, `formula`/`curve` =
model, `comparison`/`quality` = quality, `closing` = output). This makes each
abstract method page visibly part of the same software workflow.

- [x] **Step 2: Add layered entrance motion for lecture components.**

Use CSS transforms and opacity only: headings rise, visual panels scale in,
tables and quality rows wipe in, and metrics stagger. The classes must be
retriggered by the existing `showSlide()` visibility toggle and must be
disabled by the existing `prefers-reduced-motion` rule.

- [x] **Step 3: Animate scientific visual primitives.**

Animate SVG curve paths with a line-draw effect, add a slow sweep to process
strips, and pulse the active flow-ribbon stage once after the slide enters.
These effects must remain explanatory and must not imply measured dynamics.

- [x] **Step 4: Extend focused HTML contract tests.**

Assert that the HTML contains `flow-ribbon`, `updateFlowRibbon`,
`lecture-enter`, `process-sweep`, and a `prefers-reduced-motion` reset for the
new motion classes. Run `pytest tests/test_html_presentation.py -q` before
browser review.

- [x] **Step 5: Verify motion at desktop and phone viewports.**

At `1280x720` and `390x844`, inspect slides 01, 17, 20, 25, 27, 40, and 46.
Confirm that the ribbon stays inside the stage, text remains readable, the
animation does not cause layout shift or overflow, and the browser console is
clean.
