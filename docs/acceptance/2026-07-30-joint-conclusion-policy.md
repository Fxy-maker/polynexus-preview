# Joint conclusion policy acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-30-joint-conclusion-policy.md`
Scope: non-SAXS Joint report semantics only

## Result

Joint now exposes a JSON-safe `joint_conclusion` at report level and inside
`ai_context`. It classifies only existing reviewer status and existing
validation/technique issue severity. Reviewer policy text is preserved as
provenance and is never interpreted as a scientific precedence rule.

## Classification evidence

| Existing state | Class | Allowed |
| --- | --- | --- |
| Missing, invalid, pending, stale, or source-mismatched review | `review_required` | No |
| Rejected review | `rejected` | No |
| Accepted review plus an existing `ERROR` | `blocked` | No |
| Accepted review plus an existing `WARN` | `conditional` | No |
| Accepted review and no existing issue | `accepted` | Yes |

The projection carries `record_id`, `scope`, `status`, `policy_version`,
`source_refs`, and the exact `conflict_precedence`, `minimum_evidence`, and
`unresolved_conflict_policy` strings for each valid reviewer record.

## Verification

| Command | Result |
| --- | --- |
| `python -m pytest -p no:cacheprovider -q tests/test_joint_hub_dataset.py -k "conclusion or joint_hub_dataset_collects_latest_runs_and_reports"` | `6 passed, 7 deselected in 0.38s`, exit 0 |
| `python -m pytest -p no:cacheprovider -q tests/test_joint_hub_dataset.py tests/test_joint_real_data_lifecycle.py tests/test_joint_figure_provider.py tests/test_joint_lifecycle_closure.py tests/test_nmr_joint_provenance_matrix.py` | `24 passed in 44.79s`, exit 0 |
| `python scripts/boundary_audit.py --root D:\PolyNexus --json` | JSON inventory emitted, exit 0 |
| `python scripts/verify.py --task docs/agent/tasks/2026-07-30-joint-conclusion-policy.md --changed --types` | exit 0; quality `291 passed`, preprocessing `106 passed`; task/memory, Ruff, compile, type-baseline, and whitespace passed |
| `git diff --check` | exit 0 |

All test commands used `C:\PolyNexus-test-runs` with review retention and
`-p no:cacheprovider`. The change does not alter formulas, thresholds,
evidence weights, existing scientific-review promotion snapshots, figure
roles, SAXS files, or real datasets.

## Remaining boundary

This is a software/provenance classification, not a scientific decision. It
does not supply IR mapping metadata, NMR assignments, or reviewer values for
Joint conflict precedence. Missing reviewer input remains fail-closed, and
human final release approval remains open.
