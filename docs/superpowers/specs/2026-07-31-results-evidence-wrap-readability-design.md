# Results Evidence Wrap Readability Design

## Decision

Retain `WrappedEvidenceLabel` as the shared presentation widget. It already
stores the source text separately and inserts zero-width break opportunities
only into the rendered QLabel text. When Results configures the widget with a
horizontal `Ignored` policy, Qt disables the label's height-for-width
capability. The fix is to set the policy through a copied `QSizePolicy` and
explicitly restore `heightForWidth=True`.

This keeps the existing horizontal shrink contract while allowing Qt layouts to
ask for the correct wrapped height. No content truncation, ellipsis, manual
line insertion, or technique-specific branch is introduced.

## Data flow

```text
source evidence string
  -> WrappedEvidenceLabel.setText()
  -> exact source retained in text()
  -> rendered text receives zero-width break points
  -> layout uses constrained width + heightForWidth
```

## Error and compatibility behavior

- `None` remains represented as an empty source string.
- `text()` remains lossless for callers and exports.
- Only the layout policy metadata changes; evidence values and labels do not.
- Existing consumers that set a custom horizontal policy retain that policy.

## Testing

The regression creates the real Qt widget, sets a long vendor-style evidence
line, applies the same constrained policy used by Results, and asserts that
height-for-width remains enabled and produces a multi-line height at a narrow
width. It also asserts the source text is unchanged.
