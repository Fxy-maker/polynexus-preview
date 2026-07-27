# SAXS condition-axis Export/History boundary audit plan

## Task 1: Define and write RED regressions

- [x] Add a temperature-series export assertion for the complete nested
  `condition_axis`, including `None` and diagnostic positions.
- [x] Extend the History persistence fixture with the same axis and assert both
  storage locations plus input immutability.
- [x] Add a direct public quality DTO case because the generic History
  normalizer did not preserve its `to_dict()` representation.

Expected result: the new assertions fail only where the current boundary does
not preserve the contract.

## Task 2: Minimal implementation

- [x] RED identified a real DTO serialization gap; add the smallest
  `to_dict()`-aware normalization branch in `analysis_run_service.py`.
- [x] Do not touch the SAXS engine, condition-axis builder, or quality gate.

## Task 3: Verification and checkpoint

- [x] Run focused GREEN tests with an external Windows basetemp.
- [x] Run the complete SAXS matrix and structured task verifier.
- [x] Review `git diff --check` and the explicit allowlist.
- [x] Update durable memory with exact evidence and known human-review limits.
- [x] Create one `scripts/auto_commit.py` checkpoint; never include parallel GUI
  or scratch files.

Checkpoint: `fac9c8d` (`fix(saxs): preserve condition-axis history DTOs`).
