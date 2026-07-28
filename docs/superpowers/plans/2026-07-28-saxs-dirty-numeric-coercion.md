# SAXS dirty numeric coercion implementation plan

1. Add focused tests asserting that malformed q/I tokens are dropped at their
   original pair positions while neighboring valid pairs survive and report
   `invalid_pairs_dropped`.
2. Run the focused tests to capture the expected RED against whole-array
   conversion.
3. Change only `_as_1d_float_array()` to coerce elements independently,
   representing conversion failures as `NaN`.
4. Run focused tests, the exact SAXS matrix, task-scoped verification, and
   `git diff --check` with an isolated test root if required by Windows.
5. Update the task card and durable memory, then invoke `scripts/auto_commit.py`
   with the explicit allowlist. Leave all pre-existing parallel files out.
