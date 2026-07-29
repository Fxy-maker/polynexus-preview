# SAXS modern temperature Figure axis dirty-input implementation plan

1. Add a focused RED regression to
   `tests/test_saxs_temperature_figure_provider.py` using a malformed
   temperature token surrounded by valid values. Assert no exception, stable
   frame identity/order, and explicit missing condition values in the modern
   Figure definitions.
2. Run the focused regression before changing production code and record the
   expected whole-array conversion failure.
3. Replace only the modern provider's temperature-axis whole-array coercions
   with one projected numeric array produced by the existing helper. Reuse it
   for frame, waterfall, parameters, and heatmap construction.
4. Run focused GREEN, the related SAXS Figure provider matrix, the exact SAXS
   matrix, the structured verifier, `git diff --check`, and test-storage
   report/clean dry-runs.
5. Update the task card, acceptance evidence, and `active-work.md`, audit the
   explicit diff allowlist, and create one `scripts/auto_commit.py` checkpoint.

No full/boundary pass is claimed unless a fresh command emits a complete
pytest summary and exit code `0`.
