# SAXS export dirty-profile guard acceptance

Date: 2026-07-29

Task: `docs/agent/tasks/2026-07-29-saxs-export-dirty-profile-guard.md`

Status: automated acceptance complete; explicit checkpoint created

The export boundary now prefers canonical q and uses elementwise coercion for
fallback profile layers. Dirty positions remain empty CSV cells while
`provenance.json` retains `WARN` and invalid-value diagnostics.

Evidence: RED `1 failed, 11 deselected`; GREEN `1 passed, 11 deselected`;
consumer matrix `17 passed`; fresh real SAXS lifecycle replay returned `3
passed, 12 deselected` with exit code `0`; structured verifier exit `0` with quality `287`
and preprocessing `106`; storage dry-run `572` artifacts, `42` eligible,
`530` protected, `0` removed. The exact SAXS matrix timed out after `304s`
without a pytest summary and is not claimed as passed. No scientific analysis,
rescue, AI, or publication behavior changed. The final checkpoint hash is
reported in the handoff; no push or merge was performed.
