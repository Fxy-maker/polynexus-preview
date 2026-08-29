# Suite Runtime and Skill Installation Acceptance

**Date:** 2026-08-29
**Task:** `docs/agent/tasks/2026-08-29-suite-runtime-installation.md`
**Status:** implementation_complete_review_required

## Implemented

- Shared `SuiteManager` discovers Codex skills, validates a pinned component
  manifest, stages local directory/ZIP or HTTP(S) sources, checks SHA-256 and
  required files, and writes an atomic `suite-lock.json`.
- Existing installations are moved to a timestamped backup before activation;
  activation or lock failures restore the previous directory.
- CLI `suite doctor`, `install-ars`, `update`, `rollback`, and `handoff` all
  delegate to the shared service. Installation/update require `--yes`.
- GUI uses a Qt-free `SuiteManagerAdapter` that returns the same JSON-safe DTOs.
- Evidence handoff validates the existing `EvidencePackageView` contract and
  returns package-relative ARS input files without copying or recalculating
  metrics.

## Verification

```text
python -m pytest -p no:cacheprovider -q tests/test_suite_contracts.py tests/test_suite_manager.py tests/test_suite_handoff.py tests/test_suite_cli.py tests/test_suite_gui_adapter.py
```

Result: 11 passed.

The task-scoped structured verifier and `git diff --check` are required before
the final checkpoint and are recorded in the completion report.

## Limitations and review boundaries

- The repository does not invent an official ARS distribution URL or license.
  Production shipping still needs a human-approved manifest entry containing
  the official source, pinned hash, and terms. Local/offline sources are fully
  supported now.
- No model invocation occurs during installation smoke validation.
- Scientific values, eligibility, and human review decisions are unchanged.
- Existing untracked `active_run.json`, `runs/`, and `tests/_tmp_phase3/` remain
  untouched.
