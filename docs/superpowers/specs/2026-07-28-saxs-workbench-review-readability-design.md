# SAXS Workbench review evidence readability design

## Context

SAXS Workbench review presentation already derives independent advisory
sections for condition-axis defects, metric evidence, Guinier sequence,
sequence rescue, AI rescue, detector evidence, and data quality. The current
presentation model concatenates those sections with spaces, so a populated
temperature result becomes a dense paragraph even though the underlying
evidence remains structured and conservative.

## Design

Change only the final presentation join in
`build_saxs_results_presentation()`:

```python
risk_text = "\n".join(text for text in risk_sections if text)
next_text = "\n".join(text for text in next_sections if text)
```

The section lists retain their current order. The public fields remain strings,
so existing GUI, History, Export, and review-hint consumers continue to work.
No source content is changed, and empty sections do not create blank lines.

## Safety and scientific boundary

This is presentation-only. It cannot promote Diagnostic/Unusable evidence,
alter physical gates, select rescue candidates, call AI, or modify persisted
analysis payloads. New tests assert source ordering, exact per-section text,
newline separation, empty-section omission, and input immutability.

## Verification evidence

- RED: `1 failed`; the expected failure showed the old space-joined output.
- Focused consumer matrix: `104 passed`.
- Exact SAXS matrix: `419 passed, 6 warnings`.
- The task verifier passed with quality `283`, preprocessing `106`, Ruff,
  compile, memory/task, and whitespace checks; `git diff --check` passed. The
  explicit allowlist checkpoint is `8e09f23`. Post-change full/boundary
  verification also passed: `2851 passed, 17 skipped, 12 warnings` in
  1567.25s, with compile, whitespace, and boundary audit passing.
