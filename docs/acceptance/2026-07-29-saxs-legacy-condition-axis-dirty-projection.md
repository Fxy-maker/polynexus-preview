# SAXS Legacy Condition-Axis Dirty Projection Acceptance

Status: accepted for this automated compatibility Figure boundary; scientific
and release gates remain separate.

Legacy static/strain Figure condition labels now use the existing detached
elementwise numeric projection. Numeric condition tokens retain their original
order and formatting. Malformed or non-finite values become `NaN` and use the
existing `Frame <index>` label fallback. No condition is inferred, sorted,
replaced, or removed, and the caller-owned source remains unchanged.

Evidence:

- RED: `1 failed, 11 deselected`, failing at the old whole-array conversion.
- GREEN: `1 passed, 11 deselected`; complete provider `12 passed`.
- Structured verifier: exit `0`, quality `287`, preprocessing `106`, with
  Ruff/compile/memory/task/whitespace checks passing.
- Exact SAXS matrix: `575 passed, 6 warnings in 508.86s`, exit `0`.
- `git diff --check`: exit `0`.
- Storage report/clean: dry-run `30` artifacts, `0` eligible bytes,
  `0` removed; `test_storage.py --apply` was not run.
- The explicit allowlist checkpoint is created after this evidence; its commit
  hash is reported in the handoff.

Limitations: this is a legacy Figure-label boundary only. Analysis condition
semantics, modern Figures, detector/orientation projections, quality levels,
physical gates, AI/rescue, publication roles, and human scientific/release
approval are unchanged.
