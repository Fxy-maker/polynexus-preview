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
- Full task-scoped verification and the explicit allowlist checkpoint are
  recorded after the final changed-file check.

## Result

For a conflict error, the panel now exposes text equivalent to:

`Joint conclusion | blocked | allowed=false | reason=conflict_error`

This is display/provenance clarification only. It does not change the Joint
classifier, reviewer record, formula, conflict priority, or release approval.
