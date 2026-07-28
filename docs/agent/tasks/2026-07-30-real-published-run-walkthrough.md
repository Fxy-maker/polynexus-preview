---
task_id: 2026-07-30-real-published-run-walkthrough
kind: release-verification-audit
status: completed
---

# Real published-run lifecycle walkthrough

## Goal

Re-run the repository's real published-run lifecycle matrix and record fresh
evidence for engine input through Manifest/Gallery/Editor/export provenance.

## Non-goals

- Do not change production code or real regression data.
- Do not infer scientific validity from lifecycle transport.
- Do not approve IR vendor semantics, NMR solid-C assignments, or publication.

## Affected boundaries

- `tests/test_real_published_run_walkthrough.py`
- Real fixture engines and shared figure/run lifecycle contracts.
- Durable task and acceptance evidence only.

## Implementation plan

1. Run the complete real published-run walkthrough with an isolated D: basetemp.
2. Read the complete pytest summary and exit code.
3. Record covered modes, warnings, output root, and scientific limitations.

## Acceptance criteria

- [x] The complete real-mode matrix has a pytest summary and exit code.
- [x] DSC, SAXS, WAXS, IR, and NMR mode coverage is recorded.
- [x] Lifecycle evidence is kept separate from scientific/release approval.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_real_walkthrough_current_20260730'
python -m pytest -q tests/test_real_published_run_walkthrough.py
# 15 passed, 11 warnings in 361.98s (0:06:01)
# WALKTHROUGH_EXIT_CODE=0

python scripts/verify.py --task docs/agent/tasks/2026-07-30-real-published-run-walkthrough.md --changed --types
git diff --check
```

Coverage is DSC standard/isothermal/non-isothermal (`3`), SAXS static/
temperature/strain (`3`), WAXS static/temperature/strain-2D (`3`), IR
standard/temperature-2D (`2`), and NMR liquid H/C and solid H/C (`4`).

## Limitations

This proves real fixture lifecycle transport through publication and recovery;
it does not establish scientific agreement, IR vendor/ROI meaning, NMR
solid-C assignment correctness, Joint conflict interpretation, restarted-GUI
visual approval, or final release authorization. No test data was deleted or
migrated.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-30-real-published-run-walkthrough.md`
- `docs/acceptance/2026-07-30-real-published-run-walkthrough.md`
- `docs/agent/memory/active-work.md`
