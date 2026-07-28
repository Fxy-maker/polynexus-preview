# SAXS Results evidence layout design

## Context

The native Windows SAXS route can produce long `Risk note` and `Next step`
strings containing multiple evidence sources and machine reason codes. The
labels already have `wordWrap` enabled, but their default horizontal size
policy lets the unwrapped size hint determine the parent group's minimum
width. The surrounding Results scroll area does not provide a horizontal
scrollbar, so the right side of the evidence can be clipped.

## Design

Configure the existing Results text labels with `minimumWidth = 0` and
`QSizePolicy.Ignored` horizontally while retaining `QSizePolicy.Preferred`
vertically and `wordWrap = True`. Apply this to the summary and review text
labels created by `MainWindowResultsMixin._build_results_tab()` so both
presentation surfaces remain bounded by the available Results viewport.

The existing `risk_text` and `next_text` values remain unchanged. No comma
insertion, truncation, normalization, or HTML/display transformation is
introduced; preserving exact label text keeps History and persistence
consumers compatible and leaves scientific evidence semantics untouched.

## Error and boundary behavior

Empty labels remain hidden under the existing visibility logic. Long strings
wrap within the available label width. The fix does not make an unusable or
diagnostic result more publishable and does not affect any SAXS calculation,
quality threshold, rescue candidate, or export payload.

## Testing

The regression instantiates the real `MainWindow`, supplies long risk and
next-step strings through `_set_results_summary()`, and asserts that the
evidence labels are horizontally shrinkable, remain word-wrapped, preserve
the exact strings, and do not force an unbounded summary-group minimum width.
Existing GUI/Workbench/SAXS matrices and the structured verifier provide
consumer and repository-level regression coverage.

The fresh SAXS matrix returned `456 passed, 6 warnings`; the task verifier
passed with quality `287` and preprocessing `106`; and the native SAXS route
harness returned `3 passed, 14 deselected`. These checks do not constitute the
remaining human scientific or publication release gates.
