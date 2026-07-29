# SAXS Legacy Temperature Figure Partial-Frame Acceptance

Status: accepted for this automated presentation boundary; scientific and
release gates remain separate.

The legacy temperature Figure provider now keeps a full source-indexed slot
list while projecting q/I. A fully unplottable frame is omitted from Figure
sources rather than aborting the whole series. Valid frames keep their original
Figure ids, and recipe evidence records the omitted zero-based index with
`figure_profile_unavailable`. No data is fabricated and no analysis or quality
decision is recalculated.

Evidence:

- RED: `1 failed, 10 deselected`, failing at the old no-plottable-data
  `ValueError`.
- GREEN: `1 passed, 10 deselected`; complete legacy provider `11 passed`.
- Related Figure consumers: `30 passed, 25 deselected`.
- Structured verifier: exit `0`, quality `287`, preprocessing `106`, with
  Ruff/compile/memory/task/whitespace checks passing.
- Exact SAXS matrix: `574 passed, 6 warnings in 459.23s`, exit `0`.
- `git diff --check`: exit `0`.
- Storage report/clean: dry-run `30` artifacts, `0` eligible bytes,
  `0` removed; `test_storage.py --apply` was not run.
- The explicit allowlist checkpoint is created after this evidence; the commit
  hash is reported in the handoff.

Limitations: structural sequence-count mismatches still fail closed. This
task does not change modern temperature Figures, static/strain Figures,
detector/orientation projections, analysis metrics, quality levels, physical
gates, AI/rescue, publication roles, or human scientific/release approval.
