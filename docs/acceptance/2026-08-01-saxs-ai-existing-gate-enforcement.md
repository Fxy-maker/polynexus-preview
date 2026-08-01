---
kind: acceptance
status: recorded
date: 2026-08-01
title: Existing SAXS gates enforced for AI preprocessing candidates
task: docs/agent/tasks/2026-08-01-saxs-ai-existing-gate-enforcement.md
---

# Acceptance Record

## Behavior

The SAXS AI candidate path now composes generic preprocessing scoring with the
existing `assess_saxs_confirmed_rerun()` result. A candidate is only eligible
when both existing physical and quality statuses are `passed`. Failed or
unavailable evidence is retained as audit evidence and forces
`keep_original`; no new threshold or rescue action was introduced.

The decision exposes `saxs_existing_quality_gate` and
`saxs_existing_physical_gate` hard guards. Detached
`technique_specific.saxs_existing_gate` evidence contains only status,
accepted, and reason-code fields. Static, temperature, and strain candidates
were each covered.

## Automated Evidence

- TDD RED reproduced the gap: the Diagnostic-quality candidate returned
  `auto_accept` before the production guard existed.
- Focused AI/SAXS orchestration matrix: `46 passed in 0.42s`, exit code `0`.
- Complete SAXS matrix: `720 passed, 6 warnings in 443.79s`, exit code `0`.
- Structured verifier exited `0`: quality `297 passed`, preprocessing `106
  passed`, task/memory, Ruff, compile, type baseline, and whitespace checks
  passed.
- Storage report dry-run: `147` artifacts and `34,459,622,776` bytes. The clean
  dry-run saw `148` artifacts; both reported `eligible_bytes=0`, `failures=0`,
  and `removed=0`. No `test_storage.py --apply` ran.
- `git diff --check` exited `0`.

## Boundary

The confirmed transaction service still performs its existing post-rerun
validation. Non-SAXS preprocessing is unchanged. This software gate does not
approve detector geometry, mask validity, orientation, temperature/strain
meaning, or publication/release decisions; those remain human scientific
gates.

## Explicit changed-file allowlist

- `polynexus/orchestrator_preprocess.py`
- `tests/test_saxs_ai_orchestrator_handoff.py`
- `docs/superpowers/specs/2026-08-01-saxs-ai-existing-gate-enforcement-design.md`
- `docs/superpowers/plans/2026-08-01-saxs-ai-existing-gate-enforcement.md`
- `docs/agent/tasks/2026-08-01-saxs-ai-existing-gate-enforcement.md`
- `docs/acceptance/2026-08-01-saxs-ai-existing-gate-enforcement.md`

Parallel memory, real-boundary, scratch, generated-output, and test-storage
changes remain outside this checkpoint.
