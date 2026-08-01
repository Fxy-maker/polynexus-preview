# PolyNexus HTML Presentation Depth Expansion Design

## Purpose

Expand the existing 20-slide PolyNexus overview into a 46-slide, speaker-led
scientific design lecture for polymer researchers preparing papers. The deck
will explain not only what PolyNexus contains, but why each analysis stage
exists, what assumptions it makes, what it returns, and when the result must be
reviewed rather than trusted automatically.

The expanded deck remains a single self-contained HTML file and can serve as a
master video source for Bilibili/Douyin chapter cuts.

## Audience and promise

The primary audience is polymer research students and researchers who already
encounter SAXS, DSC, WAXS, IR, or NMR data but do not want to maintain many
separate analysis tools. The promise is a shorter, more transparent path from
instrument data to paper-ready evidence, without presenting automation or AI as
a replacement for scientific judgment.

## Scope and non-goals

In scope:

- Expand the narrative from 20 to 46 slides.
- Deepen the SAXS section with equations, assumptions, processing stages,
  complementary methods, limitations, and quality states.
- Explain static, temperature, strain, and 2D extensions as one result contract.
- Explain the five-technique architecture without pretending the algorithms are
  identical.
- Explain the AI parameter-advisor loop as bounded, multi-objective,
  human-confirmed optimization.
- Add speaker-note content and specify the visual asset type for every slide.

Out of scope:

- Changes to PolyNexus analysis engines, GUI behavior, data contracts, or
  scientific thresholds.
- Inventing numerical results or claiming publication validity for explanatory
  diagrams.
- Replacing all explanatory diagrams with fabricated GUI screenshots.
- Installation and hands-on tutorials; those remain follow-up videos.

## Narrative architecture

The master deck has five chapters:

| Chapter | Slides | Role |
| --- | ---: | --- |
| Why PolyNexus | 01-07 | Establish the research problem and shared analysis contract. |
| SAXS deep dive | 08-27 | Show how a curve becomes structure evidence, including failure boundaries. |
| Sequence and 2D | 28-33 | Generalize the contract to changing conditions and detector geometry. |
| Five techniques | 34-39 | Map shared responsibilities across DSC, WAXS, SAXS, IR, and NMR. |
| AI advisor | 40-46 | Explain candidate generation, multi-objective review, and human gates. |

Each chapter is independently exportable as a short video. Each 6-8 slide
subchapter should answer one complete question instead of ending on a feature
list.

## Slide-level content contract

### Chapter 01: Why PolyNexus (01-07)

1. Title: from curves to evidence.
2. One sample crossing many tools, formats, and plotting habits.
3. The expensive part is the analysis chain, not an isolated formula.
4. Origin story: a SAXS structure-parameter problem grew into a platform.
5. Four design goals: automation, lower entry barrier, reviewability, and
   multi-technique context.
6. Shared contract: input -> preprocessing -> model -> parameters -> quality ->
   figures/export.
7. Full narrative map and the role of SAXS as the teaching case.

### Chapter 02: SAXS deep dive (08-27)

8. SAXS chapter divider: what a scattering curve can and cannot tell us.
9. Scattering intuition: beam, sample structure, and measured signal.
10. q derivation and the relation between angle, wavelength, and spatial scale.
11. I(q), units, metadata, and the normalized data object.
12. What the raw instrument file becomes inside the analysis pipeline.
13. Intensity correction, normalization, and instrument background.
14. Background subtraction as a scientific choice, not cosmetic cleanup.
15. q-range selection and model-specific working windows.
16. Smoothing, masks, outliers, and the risk of manufacturing structure.
17. Low-q, mid-q, and high-q model-selection map.
18. Guinier assumptions, linearization, and the radius-of-gyration question.
19. I(0), Rg, fit-window stability, and diagnostic agreement.
20. Porod assumptions, high-q tails, interfaces, and exponent limits.
21. Why a Porod exponent is not a complete structural conclusion.
22. Bragg peak position and d = 2pi/q* for periodic structure.
23. Lorentz correction: changing the observable before fitting.
24. Correlation function / IDF: q-space to distance-space interpretation.
25. Invariant Q: integrated structural information and its limitations.
26. Complementary-method matrix: agreement, conflict, and incomparable cases.
27. Quality states: usable, review-required, and unusable with fail-closed
    behavior.

### Chapter 03: Sequence and 2D (28-33)

28. Static, temperature, strain, and 2D as modes of one analysis contract.
29. Temperature sequence: structural evolution rather than isolated curves.
30. Strain sequence: orientation, deformation stages, and anisotropy.
31. 2D data: geometry, azimuthal integration, and directional information.
32. Binding conditions, parameters, provenance, and versions to every result.
33. Extension rule: new modes must retain evidence and explicit failure states.

### Chapter 04: Five techniques (34-39)

34. Material-information hierarchy: thermal, crystal, mesoscopic, chemical, and
    local environments.
35. DSC: baseline, peaks, enthalpy, and thermal events.
36. WAXS: peak position, peak shape, crystallinity, and crystal-size estimates.
37. SAXS: lamellae, long periods, interfaces, and mesoscale organization.
38. IR and NMR: bands, baseline/phase handling, local chemical assignments.
39. Joint context: one sample workspace with technique-specific semantics and
    visible conflicts.

### Chapter 05: AI advisor (40-46)

40. AI as parameter advisor, not scientific authority.
41. Context first: raw input, current model, residuals, quality state, and risk.
42. Candidate generation for windows, baseline, smoothing, model, and bounds.
43. Multi-objective optimum: fit quality, parameter stability, physical
    plausibility, and data quality.
44. Human confirmation and bounded rerun; AI cannot bypass the review gate.
45. Evidence diff: compare before/after parameters, diagnostics, and risks with
    an audit record.
46. Closing principle and follow-up video map.

## Narration and visual asset rules

Every slide receives:

- one concise on-screen claim;
- one speaker-note paragraph explaining the reasoning;
- one declared visual role: formula, process diagram, explanatory curve,
  comparison matrix, quality state, or real GUI screenshot slot;
- one limitation sentence whenever a model assumption could be overread.

The diagrams are explanatory unless labeled as real PolyNexus output. No
synthetic number is presented as a measured material result. Formula slides use
the variables and units needed for the argument, while speaker notes carry the
longer derivation and caveat so the screen stays readable.

## Interaction and video behavior

The fixed 1920x1080 stage, keyboard/touch navigation, progress indicator,
speaker notes, captions, replay, and reduced-motion behavior remain unchanged.
The expanded deck adds chapter markers and a chapter-level navigation label so
the master video can be cut without losing the conceptual transition.

## Visual directness and motion extension

The lecture pages use a persistent `raw input -> decision -> model -> quality /
output` ribbon so the audience can locate every formula and method inside the
same PolyNexus workflow. The active step follows the slide's visual role and
does not replace the scientific explanation. Lecture content enters in layers:
the claim first, the supporting visual second, and the caveat or quality state
third. Curves draw from left to right, process strips carry a restrained sweep,
and quality states resolve one row at a time. All motion is opacity/transform or
stroke-dashoffset based, restarts on slide navigation, and is disabled by
`prefers-reduced-motion`; diagrams remain explanatory and do not represent
measured time-dependent behavior.

## Acceptance criteria

- The deck contains 44-48 slides, with the approved 46-slide outline present.
- Every approved slide has a distinct claim and narration note; no chapter is
  only a feature list.
- SAXS includes q/I(q), data preparation, Guinier, Porod, Bragg, Lorentz,
  correlation/IDF, invariant, complementary methods, and quality states.
- Every SAXS method states at least one assumption or limitation.
- Sequence/2D, five-technique, joint-context, and AI sections explain both
  shared contracts and technique-specific boundaries.
- The AI section includes human confirmation and the four-part objective.
- Browser checks pass at 1280x720 and a phone viewport with no visible slide
  overflow, overlap, or console errors.
- The focused presentation test and repository verifier pass.

## Verification commands

```powershell
pytest tests/test_html_presentation.py -q
python scripts/verify.py --changed --types
```

Use real-browser screenshots and DOM geometry checks for the expanded deck.
The Swiss-only validator remains non-authoritative because the selected deck
uses the editorial A style rather than registered Sxx Swiss layouts.
