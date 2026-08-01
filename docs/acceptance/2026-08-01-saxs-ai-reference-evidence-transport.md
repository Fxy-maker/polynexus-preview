# SAXS AI Candidate-Reference Evidence Transport

## Result

The existing diagnostic candidate-reference resolution now reaches the SAXS
Workbench, Figure/Manifest provenance, and Export quality evidence without
changing candidate execution, physical gates, quality levels, publication
roles, or validation semantics.

## Evidence

| Check | Result |
|---|---|
| TDD RED | `4 failed in 1.44s`; expected missing shared, Workbench, Figure, and Export evidence |
| Focused GREEN and Advisor/prompt regression | `104 passed in 20.94s` |
| Complete SAXS matrix | `744 passed, 6 warnings in 704.21s`, exit code `0` |
| Structured verifier | task-check valid; Ruff, compile, quality `297 passed`, preprocessing `106 passed`, whitespace passed |
| Storage report | dry-run, `162` artifacts, `eligible_bytes=0`, no emergency cleanup |
| Storage clean | dry-run, `removed=0`, `failures=0` |
| Diff hygiene | `git diff --check` passed |

The focused matrix includes the malformed Mapping guard, shared detached copy,
orchestrator engine/result attachment, Workbench advisory rendering, compact
Figure and Manifest projection, Export JSON evidence, resolver behavior, SAXS
prompt contract, and acceptance-context regression. Temperature assertions use
`guinier_sequence_evidence`; strain assertions use `metric_evidence.guinier`.

## Full-matrix verification

The exact PowerShell-expanded `test_saxs_*.py` matrix was rerun with an
isolated external basetemp and completed with `744 passed, 6 warnings in
704.21s`, exit code `0`. The six warnings are existing Arial CJK font warnings
and EDF geometry-default warnings; no failure occurred. Two earlier bounded
attempts timed out without summaries and are not counted as pass evidence.

## Scientific boundary

The resolution is diagnostic identity evidence only. Existing deterministic
physical metrics, frame quality levels, sequence integrity, validation
requirements, and publication gates remain authoritative. No candidate
parameters are shown in Workbench or Figure projections, and no interpolation,
frame repair, automatic rescue, or candidate execution is introduced.

## Follow-up boundary

This task's automated acceptance is closed. Scientific review of real SAXS
calibration, temperature/strain meaning, candidate validation, and publication
approval remains a separate human gate under the broader goal.
