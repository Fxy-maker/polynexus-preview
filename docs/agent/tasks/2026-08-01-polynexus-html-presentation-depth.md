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

- 44-48 slides, targeting 46, following the approved five-chapter outline.
- SAXS principles include formulas, assumptions, processing, methods,
  limitations, sequence/2D extensions, and quality states.
- Multi-technique and AI sections explain shared contracts without erasing
  technique-specific semantics.
- Each slide has a speaker-note paragraph and a declared visual role.
- Desktop and phone browser checks show no overflow, overlap, or console errors.
- Focused presentation tests and repository verification pass.

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
