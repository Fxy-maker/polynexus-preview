---
task_id: 2026-07-31-saxs-ai-acceptance-audit-context
kind: scientific-cross-module
status: completed
date: 2026-07-31
title: Project existing SAXS scientific acceptance audit into AI context
---

# SAXS AI scientific acceptance audit context

## Goal

Expose the already-computed `scientific_acceptance_audit` to the existing
summary-only SAXS AI context so Advisor diagnosis can see the same acceptance
evidence already used by SAXS Result, Workbench, Figure, Manifest, and Export.

## Non-goals

- No audit recalculation, new threshold, physical gate, quality level, or publication decision.
- No raw q/I, detector pixels, source path, interpolation, frame repair, candidate execution, rerun, apply, or automatic rescue.
- No changes to Figure, Manifest, Export, Workbench, or non-SAXS behavior.
- No edits to real data, generated outputs, scratch, storage, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`: engine/result unwrapping and strict audit summary projection.
- `polynexus/orchestrator_state.py`: pass the engine wrapper into the summary
  builder so live temperature/strain contexts can read the existing audit on
  the engine-level result.
- `tests/test_saxs_ai_acceptance_audit_context.py` and `tests/test_saxs_ai_live_context.py`: focused regressions.

## Contract

The context may carry only the existing audit's summary fields:
`status`, `automated_validation_passed`, `existing_publication_gate`,
`evidence_levels`, `provenance_validity`, `physical_gate_evidence`,
`method_gate_status`, `reliability`, `reason_codes`, `audit_scope`,
`publication_decision_changed`, and `detector_provenance_audit`. The copy is
detached and strict-JSON-safe. Missing or malformed audit data is omitted.
Prompt-side sanitization applies the same whitelist and excludes raw q/I,
detector pixels, source paths, and unknown fields.

## Acceptance criteria

- [x] Direct result and engine-wrapper audits project into the context.
- [x] Temperature/strain context retains existing frame and series evidence.
- [x] Missing/unsupported audit data fails closed without fabricated values.
- [x] Prompt context remains candidate-only and physical validation remains required.
- [x] Focused regressions, SAXS matrix, structured verifier, storage dry-runs,
  diff check, and explicit checkpoint are recorded. TDD GREEN is recorded;
  inherited RED was not captured and is not claimed.

## Implementation plan

1. Define the fixed audit-summary whitelist and raw-data exclusions in the
   existing summary-context boundary.
2. Project audits from direct results and engine wrappers while preserving the
   established static, temperature, and strain frame/series evidence paths.
3. Add focused regressions for detached strict-JSON projection, malformed-input
   omission, prompt sanitization, and live orchestrator state.
4. Run the focused suite, complete SAXS matrix, structured verifier, storage
   dry-runs, and diff check, then create one explicit allowlist checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_ai_acceptance_audit_context.py tests/test_saxs_ai_live_context.py tests/test_advisor.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_summary_context.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-ai-acceptance-audit-context.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

`test_storage.py --apply` is not part of this task. A timeout or pytest exit
without a final summary is recorded as incomplete, never as a pass.

## TDD evidence

- RED: `4 failed, 5 passed in 1.79s`; all four failures were the expected
  missing audit projection keys.
- GREEN: audit/live focused `9 passed in 1.42s`; combined Advisor/prompt/summary
  regression `24 passed in 0.97s`; final combined focused suite `25 passed in
  1.70s`.

## Verification evidence

- Fresh complete SAXS matrix after the live engine-wrapper handoff: `693 passed,
  6 warnings in 467.02s`, exit `0`.
- Task-scoped verifier: exit `0`; quality `297 passed`, preprocessing `106
  passed`, plus task/memory, Ruff, compile, type baseline, whitespace, and
  diff checks passed.
- Audit consumer regression: `18 passed in 93.87s`; `git diff --check` passed.
- Final storage report and clean were dry-run only: `68` artifacts,
  `13,075,489,954` bytes total, `0` eligible bytes, and `0` removed.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `polynexus/orchestrator_state.py`
- `tests/test_saxs_ai_acceptance_audit_context.py`
- `tests/test_saxs_ai_live_context.py`
- `docs/superpowers/specs/2026-07-31-saxs-ai-audit-context.md`
- `docs/superpowers/plans/2026-07-31-saxs-ai-acceptance-audit-context.md`
- `docs/agent/tasks/2026-07-31-saxs-ai-acceptance-audit-context.md`
- `docs/acceptance/2026-07-31-saxs-ai-acceptance-audit-context.md`

Parallel memory edits, scratch directories, real data, and test-storage artifacts remain outside this task.
