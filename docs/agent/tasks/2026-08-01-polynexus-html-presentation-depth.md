# PolyNexus HTML Presentation Depth Expansion

## Goal

Expand the existing PolyNexus HTML overview from 20 slides to an approved
46-slide, SAXS-led research-principles master video.

## Non-goals

- No changes to analysis engines, GUI behavior, data contracts, datasets, or
  scientific thresholds.
- No fabricated experimental results.
- No installation tutorial in this deck.

## Affected boundaries

- `docs/presentations/polynexus-overview.html`
- `tests/test_html_presentation.py`
- `docs/superpowers/specs/2026-08-01-polynexus-html-presentation-depth-design.md`
- `docs/superpowers/plans/2026-08-01-polynexus-html-presentation-depth.md`

## Acceptance criteria

- [x] 46 slides following the approved five-chapter outline.
- [x] SAXS principles include formulas, assumptions, processing, methods,
  limitations, sequence/2D extensions, and quality states.
- [x] Multi-technique and AI sections explain shared contracts without erasing
  technique-specific semantics.
- [x] Each slide has a speaker-note paragraph and a declared visual role.
- [x] Desktop and phone browser checks show no overflow, overlap, or console errors.
- [x] Focused presentation tests and repository verification pass.

## Implementation plan

1. Keep the focused contract test red while expanding the slide metadata and
   scientific coverage requirements.
2. Replace the 20-slide body with the approved 46-slide SAXS-led narrative,
   using explanatory diagrams and explicit limitation notes.
3. Add reusable fixed-stage visual primitives and chapter-aware presentation
   chrome without changing the existing navigation contract.
4. Run focused tests, JavaScript syntax checks, repository verification, and
   desktop/mobile browser geometry checks.
5. Record exact evidence, complete the acceptance checklist, and create one
   explicit presentation-only checkpoint.

## Design approval

- User selected the 40-50 slide scale on 2026-08-01.
- User approved the SAXS-led 46-slide chapter structure on 2026-08-01.
- User approved the written design and requested continuation on 2026-08-01.
- Implementation plan is recorded in
  `docs/superpowers/plans/2026-08-01-polynexus-html-presentation-depth.md`.

## Verification

```powershell
pytest tests/test_html_presentation.py -q
python scripts/verify.py --changed --types
```

## Evidence

- Focused presentation test: `3 passed`.
- SAXS slides 17-27 now have distinct model scopes: q-region map, Guinier,
  Guinier evidence stability, Porod assumption/exponent, Bragg, Lorentz,
  correlation function/IDF, invariant Q, cross-method matrix, and quality
  state/fail closed.
- Inline JavaScript syntax check: `node` `new Function` parse passed.
- Desktop browser check at `1280x720`: 46 slides scanned, no stage overflow,
  body dimensions `1280x720`, and no page or console errors.
- Mobile browser check at `390x844`: 46 slides scanned, fixed stage rendered as
  `390x219`, body dimensions stayed `390x844`, and no stage overflow or errors.
  `Home -> ArrowRight -> End` reached `02 / 46` and `46 / 46`.
- Task-scoped verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-08-01-polynexus-html-presentation-depth.md --changed --types`
  passed with quality gate `297 passed` and preprocessing optimization gate
  `106 passed`.
- `git diff --check` passed. Screenshots were captured under the ignored
  `output/playwright/` diagnostic directory.

The diagrams are explanatory visuals, not measured experimental results. Real
GUI screenshots and scientific examples remain follow-up material for the
separate tutorial and case-study videos.
