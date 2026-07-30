# Scientific Review Workbench Entry Acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-30-scientific-review-workbench-entry.md`

## Scope

The Results Workbench now provides a generic entry point for reviewer-owned
IR mapping, NMR solid-C, and Joint records. The action validates through the
existing core contract and persists a source-linked record against one exact
analysis run. It does not fabricate scientific values or republish figures.

## Verification

TDD RED/GREEN evidence:

- Missing core schema helpers: import failure, then `8 passed, 14 deselected`.
- Missing DB update API: `2 failed`, then `2 passed`.
- Missing Qt dialog module: `2 failed`, then dialog tests passed.

Focused non-SAXS matrix:

```text
python -m pytest tests/test_scientific_review.py tests/test_scientific_review_workbench.py tests/test_ir_mapping.py tests/test_ir_lifecycle_closure.py tests/test_nmr_figure_provider.py tests/test_nmr_joint_provenance_matrix.py tests/test_joint_figure_provider.py tests/test_joint_lifecycle_closure.py -q
62 passed in 33.01s
```

`git diff --check` passed. The structured verifier passed with task/memory
checks, Ruff, compile, quality `290 passed`, preprocessing `106 passed`, and
whitespace; no changed file matched the phased type-check baseline. The
verifier's standard quality gate includes the repository's shared preprocessing
adapter checks, but no SAXS source, task card, acceptance record, or scratch
path was edited or staged. The explicit allowlist checkpoint follows this
acceptance note.

## Safety boundary

- The DB update is run-scoped and transactional.
- Invalid/cancelled records do not write.
- History presentation reads the same persisted snapshot.
- Saving a record does not alter existing Figure/Manifest assets or
  publication roles; an explicit rerun/republication remains required.
- Existing `current-state.md`, SAXS code, tests, evidence, and scratch paths
  were intentionally left untouched.
