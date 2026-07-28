---
task_id: 2026-07-29-ai-fallback-matrix-audit
kind: release-verification-audit
status: completed
---

# Cross-technique AI-off/failure/fallback matrix audit

## Goal

Re-run the shared deterministic safety matrix for AI-off compatibility, failed
preprocessing, and fallback behavior across supported technique boundaries.

## Non-goals

- Do not enable external AI calls or alter scientific thresholds.
- Do not infer scientific correctness from contract behavior.
- Do not delete or migrate test data.

## Affected boundaries

- `tests/test_preprocess_cross_technique_matrix.py`
- `tests/test_preprocess_ai_off_compat.py`
- `tests/test_preprocess_fault_injection.py`
- Preprocessing decision/fallback contracts only.

## Implementation plan

1. Run the three focused safety-path suites with an external D: basetemp.
2. Capture the full pytest summary and exit code.
3. Record what the matrix proves and what remains a human/scientific gate.

## Acceptance criteria

- [x] AI-off, failure, and fallback matrix has a complete pytest summary.
- [x] The command exits successfully with no external model call.
- [x] Scientific interpretation and publication approval remain separate.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_ai_fallback_matrix_20260729'
python -m pytest -q tests/test_preprocess_cross_technique_matrix.py tests/test_preprocess_ai_off_compat.py tests/test_preprocess_fault_injection.py
# 25 passed in 0.23s
# AI_FALLBACK_EXIT_CODE=0

python scripts/verify.py --task docs/agent/tasks/2026-07-29-ai-fallback-matrix-audit.md --changed --types
git diff --check
```

## Limitations

This proves deterministic safety contracts and does not prove scientific model
quality, calibration, IR mapping semantics, NMR assignment, Joint conflict
interpretation, restarted-GUI visuals, or release approval. No test data was
deleted or migrated.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-29-ai-fallback-matrix-audit.md`
- `docs/acceptance/2026-07-29-ai-fallback-matrix-audit.md`
- `docs/agent/memory/active-work.md`
