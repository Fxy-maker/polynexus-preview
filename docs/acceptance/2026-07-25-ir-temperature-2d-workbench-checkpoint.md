# IR temperature-2D Workbench checkpoint

## Delivered

The IR temperature-2D mode now consumes its existing analysis result through
the shared FigureDefinition pipeline. The mode publishes a Manifest-backed
main spectral-evolution heatmap, band-tracking and band-index support figures,
and synchronous/asynchronous 2D-correlation diagnostic figures. The Results
Workbench profile points at the logical IDs
`ir.temperature_2d.heatmap` and `ir.temperature_2d.band-tracking`.

The provider keeps sequence values, band series, correlation matrices, and the
existing analysis recipe in the figure document. It does not recalculate IR
science in the GUI or reuse the legacy `Fig-IRT*` output as a normal Gallery
entry.

## Verification evidence

- IR temperature-2D provider, Manifest publication, IREngine handoff, and
  Workbench profile regressions: 7 passed.
- Existing IR/NMR/Joint focused matrix after the preceding profile checkpoint:
  55 passed.
- `python scripts/verify.py --changed --types`: passed, including Ruff,
  compile, quality gate (282), and preprocessing gate (103).

## Remaining acceptance boundary

- IR standard still needs a mode-level acceptance note and full real/Golden
  Figure Pack, Gallery/Editor, export, fallback, and visual walkthrough.
- IR mapping/ROI has analysis entry points but no shared FigureDefinition
  provider in this checkpoint.
- Restarted-GUI visual review, real-data scientific sign-off, and the final
  AI-off/failure/fallback matrix remain release gates.
- This checkpoint does not complete the IR vertical slice.
