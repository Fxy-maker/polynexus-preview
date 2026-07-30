# Joint conclusion display acceptance

## Scope

Non-SAXS Results review presentation only. The existing core
`joint_conclusion` projection remains authoritative; this change makes its
fail-closed state visible beside the existing review-record metadata.

## Verification

- TDD RED: the focused regression failed because `joint_conclusion` was not
  included in the Joint panel text.
- Focused GREEN: `3 passed, 26 deselected` for the Results review panel slice.
- Related review/history slice: `22 passed, 125 deselected`.
- Task-scoped verification: quality `292 passed`, preprocessing `106 passed`,
  Ruff/compile/type/whitespace all passed.
- Native Windows Qt route: `1 passed, 16 deselected in 9.22s`, exit 0, with
  capture root `D:\PolyNexus_native_joint_conclusion_display_20260730`.

## Result

For a conflict error, the panel now exposes text equivalent to:

`Joint conclusion | blocked | allowed=false | reason=conflict_error`

This is display/provenance clarification only. It does not change the Joint
classifier, reviewer record, formula, conflict priority, or release approval.

The native Results capture visibly contains the blocked conclusion and the
separate accepted review-record metadata. Gallery, History, Editor, and export
fallback route construction also passed. This remains route evidence, not
human scientific conflict approval.
