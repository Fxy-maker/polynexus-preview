# SAXS 2D input shape fail-closed implementation plan

1. Add a mismatched-axis RED test to the existing 2D detector/orientation
   evidence suite.
2. Add a small input-normalization/compatibility guard at the public
   `analyze_anisotropy()` boundary.
3. Extend the evidence attachment helper only enough to mark structurally
   invalid input as `Unusable` with a reason code.
4. Run focused 2D tests, all `test_saxs_*.py`, the structured verifier, and
   `git diff --check` using an external basetemp.
5. Record exact evidence, update `active-work.md`, and create an explicit
   allowlist checkpoint without touching `current-state.md` or scratch.
