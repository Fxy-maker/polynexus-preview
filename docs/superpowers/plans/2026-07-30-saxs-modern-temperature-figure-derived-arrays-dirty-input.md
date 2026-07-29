# SAXS modern temperature Figure derived-array dirty-input implementation plan

1. Add a focused RED test to
   `tests/test_saxs_temperature_figure_provider.py` with malformed tokens in
   `L_array`, `lc_array`, `lc_effective_array`, `Q_star_array`, and `Xc_array`;
   assert the old whole-array conversion fails.
2. Run the focused test before production edits and record the expected
   `ValueError` from `_series_values()`.
3. Change only `_series_values()` to use the existing elementwise coercion
   helper, normalize non-finite values to `NaN`, and preserve its required,
   optional, and length-mismatch branches.
4. Run focused GREEN, the related temperature Figure/provider/evidence
   matrix, the exact SAXS matrix, the structured task verifier, `git diff
   --check`, and storage report/clean dry-runs.
5. Update the task card, acceptance evidence, and `active-work.md`; audit the
   explicit allowlist and create one `scripts/auto_commit.py` checkpoint.

No full/boundary pass is attributed to this task unless a fresh command emits
a complete pytest summary and exit code `0`.
