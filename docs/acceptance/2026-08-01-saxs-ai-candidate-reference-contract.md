# SAXS AI Candidate Reference Contract Acceptance

## Result

Accepted as a diagnostic-only contract. The Advisor can retain only exact
candidate IDs that are already present in the current SAXS temperature summary.
References are deduplicated, unknown and non-string values are dropped, and
static, strain, unsupported, missing-context, and non-SAXS cases fail closed.
Reference-only advice keeps `changes` empty, does not create a preprocess
intent or candidate plan, and is retained by the existing `llm_advice` audit
path.

## Scientific and Safety Boundary

This task adds no rescue calculation, interpolation, frame fabrication,
threshold, quality level, physical gate, sequence gate, rerun, configuration
mutation, or automatic acceptance. Existing deterministic evidence and the
existing SAXS physical/quality validation and application gates remain
authoritative. Raw q/I, detector pixels, source paths, and candidate payloads
do not cross through the new output field.

## Evidence

- TDD RED: three initial tests failed because the reference field and prompt
  contract were absent; the non-SAXS fail-closed test then failed before the
  final normalization condition was added.
- Focused Advisor/prompt/summary/live/orchestrator matrix: `42 passed in
  1.39s`.
- Final explicit candidate-boundary tests: `4 passed in 0.18s`.
- Complete SAXS matrix: `725 passed, 6 warnings in 481.33s`, exit code `0`.
- Structured verifier: exit code `0`; quality `297 passed`, preprocessing `106
  passed`, task/memory, Ruff, compile, type baseline, and whitespace checks
  passed.
- Storage report: `155` artifacts, `34,468,506,754` bytes,
  `eligible_bytes=0`, failures `0`.
- Storage clean dry-run: `eligible_count=19`, `removed_count=0`, failures `0`.
  No `test_storage.py --apply` was executed.
- `git diff --check` passed before checkpointing.

## Changed Files

- `rag/advisor.py`
- `rag/prompt_builder.py`
- `tests/test_advisor.py`
- `tests/test_saxs_prompt_builder.py`
- the linked spec, plan, and task card

## Limitations

The field only identifies existing candidates. It does not provide a user
selection UI or a deterministic candidate validation transaction; those remain
separate follow-up work and must reuse the existing gates.
