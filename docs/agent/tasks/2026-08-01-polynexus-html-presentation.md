# PolyNexus HTML Presentation Task

## Goal

Create a self-contained HTML slide deck that explains why PolyNexus exists, how
its analysis design works, how SAXS turns curves into structure parameters, how
the other techniques fit a material-information hierarchy, and how the AI
parameter advisor supports a human-reviewed optimization loop.

## Non-goals

- Do not change PolyNexus analysis engines, GUI behavior, data contracts, or
  scientific thresholds.
- Do not claim that an AI-selected fit is scientifically authoritative.
- Do not create download/install tutorials in this deck; those belong to later
  videos.
- Do not edit real regression datasets or generated application outputs.

## Affected boundaries

- `docs/presentations/`: new user-facing HTML presentation artifact.
- `docs/superpowers/specs/`: durable presentation design decision.
- `docs/superpowers/plans/`: implementation plan and verification map.
- `tests/`: static smoke coverage for the presentation contract.

## Acceptance criteria

- The deck is a complete single HTML document with a fixed 1920x1080 stage.
- The deck contains 18-20 slides covering the approved narrative.
- Arrow keys, Space, Home/End, touch swipe, progress, dots, and counter work.
- A speaker-notes/subtitle mode is available without changing the slide content.
- Slides contain animated but non-essential visual effects and support reduced
  motion.
- SAXS methods are presented with their intended role and limitation, including
  Bragg, Lorentz, correlation/IDF, Guinier, Porod, Kratky, invariant, and
  temperature/strain extensions.
- The AI section states that the objective combines fit quality, stability,
  physical plausibility, and data quality, with user confirmation required.
- Browser inspection finds no console errors, visible overflow, or overlapping
  content at desktop and phone viewport sizes.

## Verification

```powershell
pytest tests/test_html_presentation.py -q
python scripts/verify.py --changed --types
node "$env:USERPROFILE/.codex/skills/guizang-ppt/scripts/validate-swiss-deck.mjs" docs/presentations/polynexus-overview.html
```

## Verification evidence (2026-08-01)

- Focused presentation test: `2 passed`.
- Repository verifier: selected checks passed; quality gate `297 passed` and
  preprocessing gate `106 passed`.
- Browser inspection: Chromium rendered the title, SAXS, AI, and closing
  slides at 1280x720 and the fixed-stage deck at 390x844. Arrow navigation,
  captions, speaker notes, console cleanliness, and all-slide geometry checks
  passed. A q/I(q) legend selector bug was fixed after the first geometry scan.
- The Swiss-only validator is not applicable to this selected editorial A
  style: it reports missing `data-layout` registration for all slides. Static
  and browser checks are the authoritative validation for this deck.
- Known limitation: diagrams are inline explanatory SVGs; real PolyNexus GUI
  screenshots can replace them in a later visual-material pass.
