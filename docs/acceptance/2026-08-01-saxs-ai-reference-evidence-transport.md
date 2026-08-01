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
| Structured verifier | task-check valid; Ruff, compile, quality `297 passed`, preprocessing `106 passed`, whitespace passed |
| Storage report | dry-run, `162` artifacts, `eligible_bytes=0`, no emergency cleanup |
| Storage clean | dry-run, `removed=0`, `failures=0` |
| Diff hygiene | `git diff --check` passed |

The focused matrix includes the malformed Mapping guard, shared detached copy,
orchestrator engine/result attachment, Workbench advisory rendering, compact
Figure and Manifest projection, Export JSON evidence, resolver behavior, SAXS
prompt contract, and acceptance-context regression. Temperature assertions use
`guinier_sequence_evidence`; strain assertions use `metric_evidence.guinier`.

## Full-matrix limitation

The exact PowerShell-expanded `test_saxs_*.py` matrix was attempted twice on
the current checkout. The first invocation exited `124` after `124044 ms`; the
second exited `124` after `604102 ms`. Neither produced a final pytest summary,
so neither is counted as a pass. The second run's exact parent/pytest processes
were then stopped after the bounded timeout; unrelated parallel pytest
processes were left untouched.

## Scientific boundary

The resolution is diagnostic identity evidence only. Existing deterministic
physical metrics, frame quality levels, sequence integrity, validation
requirements, and publication gates remain authoritative. No candidate
parameters are shown in Workbench or Figure projections, and no interpolation,
frame repair, automatic rescue, or candidate execution is introduced.

## Open follow-up

Re-run the complete SAXS matrix in an isolated, sufficiently long-lived test
session and record a complete pytest summary with exit code `0` before treating
this task as fully closed. The current code and focused/structured checks are
checkpointable, but the full-matrix acceptance checkbox remains open.
