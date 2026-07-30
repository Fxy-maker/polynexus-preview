---
task_id: 2026-07-30-scientific-review-canonical-source-match
kind: scientific-semantics
status: verified
date: 2026-07-30
title: Keep multi-reference scientific reviews source-matched
---

# Scientific Review Canonical Source Match

## Goal

Ensure a saved non-SAXS scientific review snapshot binds to the first
canonical source reference when the dialog contains both an evidence source
identifier and the current input-file path.

## Non-goals

- Do not change scientific scopes, required decisions, or promotion policies.
- Do not infer or rewrite vendor coordinates, ROI meaning, assignments, or
  Joint conflict precedence.
- Do not modify SAXS code, tests, evidence, or scratch data.
- Do not change Figure roles or numeric analysis results.

## Affected boundaries

- Results Workbench review-dialog save path.
- Source-linked promotion snapshot generation.
- Focused non-SAXS GUI regression coverage.

## Implementation plan

1. Add a fake-dialog regression with two source refs and assert the snapshot
   preserves the canonical first source ref.
2. Change the save path to pass the first validated source ref whenever one is
   present, including the multi-reference case.
3. Run focused review tests, the native IR mapping route, and task verifier.

## Acceptance criteria

- [x] An accepted review with multiple source refs has a non-empty
      source-matched snapshot.
- [x] A review with one source ref keeps the existing behavior.
- [x] Empty source refs remain fail-closed through core validation.
- [x] No Figure, manifest, numeric, or SAXS behavior changes.

## Verification

```powershell
python -m pytest tests/test_scientific_review_workbench.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-30-scientific-review-canonical-source-match.md --changed --types
git diff --check
```

## Verification result

- TDD RED reproduced `1 failed`; the failure was an empty `source_ref` for a
  valid multi-source accepted record.
- GREEN and the core/Workbench matrix passed: `30 passed`.
- Native IR mapping route passed: `1 passed, 16 deselected`.
- Task-scoped verification passed with quality `290`, preprocessing `106`,
  Ruff, compile, type baseline, memory/task, and whitespace checks.

## Explicit changed-file allowlist

- `polynexus/gui/main_window_results_mixin.py`
- `tests/test_scientific_review_workbench.py`
- `docs/agent/tasks/2026-07-30-scientific-review-canonical-source-match.md`
- `docs/agent/memory/active-work.md`
