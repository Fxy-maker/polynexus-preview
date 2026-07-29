# SAXS modern temperature Figure axis dirty-input acceptance

Task: `docs/agent/tasks/2026-07-29-saxs-modern-temperature-figure-axis-dirty-input.md`

Status: verified and checkpointed locally.

The implementation uses elementwise temperature-axis coercion to explicit
missing values, with stable frame positions and no scientific or publication
semantic changes.

Evidence:

- RED: `1 failed, 12 deselected` at the old whole-array conversion boundary.
- GREEN: focused dirty-axis test `1 passed, 12 deselected`.
- Related Figure/provider/evidence matrix: `50 passed`.
- Task verifier: exit `0`, quality `290`, preprocessing `106`, Ruff,
  compile, type baseline, memory, and whitespace all passed.
- Exact SAXS matrix: `589 passed, 6 warnings`, exit `0`.
- Storage dry-run: `54` artifacts, `6` eligible, `0` removed; no apply.
- `git diff --check`: exit `0`.

Scientific/release limitation: missing condition values remain explicit
diagnostic data. No quality level, physical gate, AI/rescue decision, or
publication authorization was changed.
