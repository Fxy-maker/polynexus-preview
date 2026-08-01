# PolyNexus HTML Presentation Design

## Purpose

Produce a speaking-led HTML presentation for a narrated Bilibili/Douyin video
series. The first video explains the software's analysis design and scientific
reasoning. Installation and hands-on tutorials are intentionally separate
follow-up videos.

## Audience and promise

The primary audience is polymer-research students who need to publish papers.
The deck's promise is ordered as: automate complex workflows; lower the entry
barrier; make results reviewable and reusable; unify multiple techniques.

## Narrative

1. Start with the real pain: one study crosses many platforms and produces many
   manual plots and transformations.
2. Introduce the SAXS origin story: structure-parameter calculation was the
   first concrete problem, and existing scripts grew into PolyNexus.
3. State the common design contract: input -> preprocessing -> model -> fit and
   parameters -> quality/evidence -> reviewable figures and export.
4. Deep-dive SAXS from physical intuition to q/I(q), complementary methods,
   sequence extensions, and fail-closed review states.
5. Move through the material-information hierarchy: DSC thermal behavior,
   WAXS crystal structure, SAXS mesoscale structure, IR chemical structure,
   NMR local structure, then joint interpretation.
6. Demonstrate the AI advisor in SAXS: inspect current evidence, explain a
   parameter suggestion, require user confirmation, rerun, and compare.
7. Close with the rule that an optimum is multi-objective and that the user
   remains the scientific decision maker.

## Visual system

Use the selected editorial paper-and-ink direction: warm paper, forest ink,
terracotta annotations, restrained sage, serif display typography, sans body,
and mono metadata. Keep the deck speaker-led with one claim per slide. Use
inline SVG charts and diagrams so the HTML stays self-contained. Use real
PolyNexus terminology and result shapes, but label diagrams as explanatory
when they are not captured application screenshots.

## Motion and interaction

Use a fixed 1920x1080 stage that scales uniformly. Apply section-specific
entrances: editorial staggered text, plotted-line drawing, pipeline node reveals,
method-card sequencing, and an AI loop that traces a path. Provide keyboard,
touch, mouse-wheel, progress, dots, and counter controls. A notes/captions mode
is available for narration and subtitles. Reduced-motion mode reveals content
without movement; motion never carries scientific meaning.

## Scientific boundaries

The deck describes implemented analysis concepts without presenting every result
as publication-ready. It explicitly shows quality states, method complementarity,
parameter stability, physical plausibility, and human review. The AI advisor is
an explainable parameter consultant, not an autonomous scientific authority.

## Deliverables

- `docs/presentations/polynexus-overview.html`
- `tests/test_html_presentation.py`
- task, spec, and plan documents for durable project memory
