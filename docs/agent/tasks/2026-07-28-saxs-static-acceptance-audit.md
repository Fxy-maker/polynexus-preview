---
kind: task
status: completed
date: 2026-07-28
title: Expose the existing scientific acceptance audit for SAXS static results
---

# SAXS static scientific acceptance audit

## Goal

Expose the same read-only `scientific_acceptance_audit` on Static SAXS
parameters that already exists for temperature and strain, without changing
the Static publication gate.

## Evidence baseline

Static SAXS already transports data-quality and metric evidence and has an
explicit figure publication gate. Its parameter payload currently lacks the
unified audit, so consumers cannot use one evidence-boundary contract across
static, temperature, and strain modes.

## Non-goals

- Do not change Static figure eligibility, `paper_*` policy, or publication
  roles; missing Static publication flags remain `None` in this audit.
- Do not alter Porod, Kratky, invariant, lamellar, Guinier, detector, or
  orientation calculations or thresholds.
- Do not add interpolation, rescue, AI, frame deletion, or scientific approval.
- Do not edit real data, generated outputs, `current-state.md`, or scratch.

## Affected boundaries

- `polynexus/core/saxs.py`: Static parameter return paths only;
- `tests/test_saxs_static_acceptance_audit.py`: Static single, batch, and
  optional real-data transport regressions;
- task/spec/plan/acceptance and `docs/agent/memory/active-work.md`.

## Implementation plan

1. Add RED tests proving Static single and aligned batch parameters lack the
   audit before the change; include strict JSON and an optional real directory.
2. Add one private payload attachment helper and call it only from Static
   parameter return paths; reuse the existing audit builder.
3. Run focused/real tests, exact SAXS matrix, structured verifier, diff check,
   and one explicit allowlist checkpoint.

## Acceptance criteria

- [x] Static single parameters expose a strict-JSON audit with existing metric
  evidence and `publication_decision_changed=False`.
- [x] Static aligned batch parameters expose the same audit without changing
  `_batch_data` alignment or existing metric evidence.
- [x] Static publication flags remain `None` when not already present; no
  publication role is promoted.
- [x] Temperature/strain behavior remains unchanged and the real Static path
  exposes the audit when the fixture exists.
- [x] TDD RED/GREEN, SAXS matrix, verifier, diff, and checkpoint evidence are
  recorded.

## Verification

```powershell
python -m pytest -q tests/test_saxs_static_acceptance_audit.py -vv --basetemp C:\Temp\PolyNexus_saxs_static_audit_redgreen
python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName) --basetemp C:\Temp\PolyNexus_saxs_static_audit_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-static-acceptance-audit.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/core/saxs.py`
- `tests/test_saxs_static_acceptance_audit.py`
- this task card
- `docs/superpowers/specs/2026-07-28-saxs-static-acceptance-audit-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-static-acceptance-audit.md`
- `docs/acceptance/2026-07-28-saxs-static-acceptance-audit.md`
- `docs/agent/memory/active-work.md`

## Checkpoint

Create the checkpoint only after current verification is recorded. No push,
merge, publication approval, or real-data write is part of this task.

## Evidence

- TDD RED: `python -m pytest -q tests/test_saxs_static_acceptance_audit.py -vv --basetemp C:\\Temp\\PolyNexus_saxs_static_audit_red` failed as expected with `3 failed in 24.53s`; all failures were the missing audit key.
- GREEN: `python -m pytest -q tests/test_saxs_static_acceptance_audit.py -vv --basetemp C:\\Temp\\PolyNexus_saxs_static_audit_green` passed with `3 passed in 24.03s`.
- SAXS matrix: `python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName) --basetemp C:\\Temp\\PolyNexus_saxs_static_audit_matrix` passed with `444 passed, 6 warnings in 144.61s`.
- The task-scoped verifier and `git diff --check` are recorded in the acceptance note before checkpoint creation.
