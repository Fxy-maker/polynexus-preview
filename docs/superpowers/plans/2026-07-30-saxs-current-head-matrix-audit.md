# Current-head SAXS Matrix Audit Plan

## Task 1: Establish the audit boundary

- [x] Inspect current HEAD, parallel changes, and existing SAXS evidence.
- [x] Create the task card and design records.

## Task 2: Run the fresh SAXS matrix

- [x] Enumerate all `tests/test_saxs_*.py` files.
- [x] Run them with offscreen Qt and a writable workspace basetemp.
- [x] Record the complete pytest summary and exit code.

## Task 3: Verify and checkpoint

- [x] Run the structured task verifier and `git diff --check`.
- [x] Record acceptance evidence and any limitations.
- [x] Create the explicit documentation-only checkpoint.
