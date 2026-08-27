# Evidence review decision ledger — 2026-08-28

Every newly created evidence package now contains `review-decision.json`.
Entries are generated from the package's ARS `human_review` list, retain the
evidence id/action/reason, and start with `decision: "pending"`. The package
manifest and `ars-writing-input.json` point to the ledger and expose its
pending status.

This is a decision record, not a recalculation layer: editing it cannot alter
raw hashes, metric values, or provider evidence. Historical packages without
the file remain readable through the existing compatibility path.

Verification:

- `python -m pytest -p no:cacheprovider -q tests/test_review_decision_ledger.py tests/test_project_workflow_package.py tests/test_project_ars_writing_handoff.py tests/test_evidence_package_view.py` — **48 passed**
- `python scripts/verify.py --task docs/agent/tasks/2026-08-28-review-decision-ledger.md --changed --types` — selected checks passed; quality **311 passed**, preprocessing **157 passed**
- `git diff --check` — passed

Human review is still required before ARS can treat any candidate as an
approved manuscript result.
