---
task_id: 2026-07-29-preprocess-golden-audit
kind: release-verification-audit
status: completed
---

# Preprocessing Golden data audit

## Goal

Run the repository's Golden preprocessing evaluation and record fresh evidence
for deterministic expected outputs.

## Non-goals

- Do not change preprocessing behavior, fixtures, or scientific thresholds.
- Do not treat Golden agreement as human scientific approval.
- Do not delete or migrate test data.

## Affected boundaries

- `tests/eval/preprocess/test_preprocess_golden.py`
- `tests/eval/preprocess/golden_manifest.json`
- Preprocessing adapters and decision contracts.

## Implementation plan

1. Run the complete Golden preprocessing evaluation with D: basetemp.
2. Capture the complete pytest summary and exit code.
3. Record the scope limitation and preserve the existing fixtures.

## Acceptance criteria

- [x] The Golden evaluation has a complete summary and exit code.
- [x] No fixture or production file is modified.
- [x] Golden evidence remains separate from scientific/release approval.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_preprocess_golden_20260729'
python -m pytest -q tests/eval/preprocess/test_preprocess_golden.py
# 3 passed in 0.13s
# GOLDEN_EXIT_CODE=0

python scripts/verify.py --task docs/agent/tasks/2026-07-29-preprocess-golden-audit.md --changed --types
git diff --check
```

## Limitations

This is deterministic preprocessing Golden evidence only. It does not prove
scientific interpretation, vendor mapping/ROI semantics, NMR assignment,
Joint conflict resolution, restarted-GUI visual approval, or final release
authorization. No test data was deleted or migrated.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-29-preprocess-golden-audit.md`
- `docs/acceptance/2026-07-29-preprocess-golden-audit.md`
- `docs/agent/memory/active-work.md`
