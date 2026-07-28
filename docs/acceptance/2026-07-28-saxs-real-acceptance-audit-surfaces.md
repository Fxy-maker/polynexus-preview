# SAXS real acceptance audit surfaces

**Date:** 2026-07-28
**Task:** `docs/agent/tasks/2026-07-28-saxs-real-acceptance-audit-surfaces.md`

## Scope

The real Static, Temperature, and Strain SAXS fixtures were replayed through
the existing engine pipeline. The acceptance check compares the existing
`scientific_acceptance_audit` mapping across final parameters, generated Figure
documents, and the exported `quality_evidence.json` contract. No physical
threshold, publication role, rescue behavior, AI behavior, or scientific
status was changed.

## Evidence

- RED reproduction: Static and Strain passed; Temperature failed because
  figures were emitted before post-analysis validation and retained
  `automated_validation_passed=True` while final parameters were `False`.
- GREEN focused regression:
  `python -m pytest -q tests/test_saxs_real_acceptance_audit_surfaces.py -vv
  --basetemp C:\\Temp\\PolyNexus_saxs_real_acceptance_audit_surfaces_green_apply`
  returned `3 passed` in `53.2s`.
- The fix refreshes only the generated Figure document's existing
  `recipe.evidence.quality_provenance.scientific_acceptance_audit` field after
  final validation. Missing manifests/documents or malformed provenance are
  skipped with warnings.

- Current focused recheck:
  `python -m pytest -q tests/test_saxs_real_acceptance_audit_surfaces.py -vv
  --basetemp D:\\PolyNexus-test-runs\\saxs-real-audit-surfaces-red-current`
  returned `3 passed in 44.47s` (Static, Temperature, Strain). The Temperature
  result remains `validation_passed=False`.
- Structured verifier returned exit code `0` with quality `287` and
  preprocessing `106`; Ruff, compile, type baseline, memory/task, and
  whitespace checks passed. `git diff --check` passed.
- `python scripts/test_storage.py report --json` remained dry-run only:
  `460` artifacts, `49` eligible, `411` protected, `24,006,209,757` eligible
  bytes, and `0` removed. No test output or real data was deleted.

## Checkpoint

The explicit changed-file allowlist is recorded in the task card. The local
checkpoint is created with `scripts/auto_commit.py`; it does not push, merge,
deploy, or apply storage cleanup. Scientific interpretation, GUI review, and
publication approval remain separate gates.
