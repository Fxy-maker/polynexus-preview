# Project-level release decision acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-30-project-release-decision.md`
Scope: non-SAXS release/workbench provenance only

## Result

The project-level release workflow is structurally implemented. A validated
`ScientificReviewRecord(scope="release")` is appended to a SampleDB batch,
the newest snapshot is hydrated for analysis-run/history consumers, and the
Results Workbench/Export surfaces expose detached provenance. Saving the record
does not alter numeric results, Figure roles, or scientific promotion gates.

## Focused verification

All commands used the external test root `C:\PolyNexus-test-runs`,
`POLYNEXUS_TEST_RETENTION=review`, and `-p no:cacheprovider` to avoid writing
test artifacts to the full D: volume.

| Command | Result |
| --- | --- |
| `python -m pytest -p no:cacheprovider -q tests/test_scientific_review.py tests/test_scientific_review_workbench.py` | `40 passed in 0.64s`, exit 0 |
| `python -m pytest -p no:cacheprovider -q tests/test_sample_db.py` | `2 passed in 0.13s`, exit 0 |
| `python -m pytest -p no:cacheprovider -q tests/test_export_context_service.py` | `16 passed in 0.29s`, exit 0 |
| `python -m pytest -p no:cacheprovider -q tests/test_main_window_history_mixin.py` | `1 passed in 0.50s`, exit 0 |

## Remaining human boundary

The software records a reviewer decision but cannot supply the missing IR
vendor-native mapping payload, NMR solid-C assignment truth set, Joint conflict
precedence, or the human `approve/conditional/reject` choice. Until those are
entered by the responsible reviewer, release promotion remains denied or
conditional according to the stored record; no scientific conclusion is
invented by this task.

## Storage note

The updated emergency retention rule was honored. The previous `--apply`
removed eligible managed failed runs, and non-SAXS current test artifacts were
moved intact to `C:\PolyNexus-test-archive-20260730` after verifying they were
untracked and not referenced by a process. SAXS and real datasets were left
untouched.

## Structured verification

To be filled with the fresh outputs from:

```powershell
python scripts/boundary_audit.py --root D:\PolyNexus --json
python scripts/verify.py --task docs/agent/tasks/2026-07-30-project-release-decision.md --changed --types
git diff --check
```

Fresh results on 2026-07-30:

| Command | Result |
| --- | --- |
| `python scripts/boundary_audit.py --root D:\PolyNexus --json` | JSON inventory emitted, exit 0; no boundary-audit failure reported |
| `python scripts/verify.py --task docs/agent/tasks/2026-07-30-project-release-decision.md --changed --types` | exit 0; quality `291 passed`, preprocessing `106 passed`; task/memory, Ruff, compile, type-baseline, and whitespace checks passed |
| `git diff --check` (explicit release source/test allowlist) | exit 0 |

The focused matrix was rerun after the final release-missing tests were added:
`61 passed in 1.53s`, exit 0. The checkpoint allowlist excludes the existing
`docs/agent/memory/current-state.md` modification, SAXS paths, real datasets,
and all temporary test artifacts.
