# SAXS Static Scientific Acceptance Audit

Date: 2026-07-28
Task: `docs/agent/tasks/2026-07-28-saxs-static-acceptance-audit.md`

## Result

Static SAXS parameter payloads now expose the existing read-only
`scientific_acceptance_audit` contract on single-profile, aligned batch, and
batch fallback paths. The implementation reuses
`build_saxs_scientific_acceptance_audit()` and does not synthesize publication
eligibility or alter the existing Static publication provider.

The audit keeps `paper_figure_candidate`, `paper_conclusion_candidate`, and
`paper_conclusion_ready` as `None` when Static publication flags are not already
present, and reports `publication_decision_changed=False`. Aligned `_batch_data`
rows and missing-frame evidence remain unchanged.

## TDD and verification evidence

- RED: the focused test command failed as expected with `3 failed in 24.53s`
  because Static payloads lacked the audit key.
- GREEN: the focused test command passed with `3 passed in 24.03s`, including
  the real Static directory test when the fixture was available.
- Exact SAXS matrix passed: `444 passed, 6 warnings in 144.61s`.
- The six warnings are the existing Matplotlib CJK glyph warnings and SAXS EDF
  geometry-default warnings; they are unrelated to this transport change.
- Structured verifier passed:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-static-acceptance-audit.md --changed --types`.
  Task card and memory checks passed; Ruff, compile, and type baseline passed;
  quality gate passed with `287 passed`; preprocessing optimization passed with
  `106 passed`; whitespace check passed.
- Independent `git diff --check` passed.
- Test-data management audit: `python scripts/test_storage.py report --json`
  completed in dry-run mode. Test outputs stayed outside the source/data
  boundary for this task; no cleanup or deletion was performed. The report
  still finds pre-existing legacy artifacts in the repository and external
  roots, including eligible retention candidates, which were intentionally
  left untouched because they are outside this task's allowlist.

## Boundary and limitations

This is an evidence-transport unification only. It does not change Guinier,
Porod, Kratky, invariant, lamellar, detector, orientation, quality thresholds,
rescue, interpolation, AI, frame deletion, or publication approval. Temperature
and strain branches retain their existing behavior. Scientific interpretation
and publication authorization still require the existing physical gates and
human review.

The explicit checkpoint hash is appended after the allowlisted commit.
