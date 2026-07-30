# SAXS modern temperature Figure derived-array dirty-input acceptance

Task: `docs/agent/tasks/2026-07-30-saxs-modern-temperature-figure-derived-arrays-dirty-input.md`

Status: verified and checkpointed at `bb0048c`.

The intended boundary is elementwise projection of malformed derived metric
tokens to explicit missing values, while preserving frame positions and all
existing quality, physical, publication, AI, and rescue contracts.

Evidence:

- RED: `1 failed, 13 deselected` at `_series_values()` whole-array conversion.
- GREEN: `1 passed, 13 deselected`.
- Related Figure/provider/evidence matrix: `51 passed`.
- Task verifier: exit `0`, quality `290`, preprocessing `106`, Ruff,
  compile, type baseline, memory, and whitespace passed.
- Exact SAXS matrix: `590 passed, 6 warnings`, exit `0`.
- Storage report/clean dry-run: `54` artifacts, `6` eligible, `0` removed;
  no apply was run.
- `git diff --check`: exit `0`.

No scientific metric, quality level, physical gate, publication role, AI
decision, or rescue behavior was changed.

No push or merge was performed.
