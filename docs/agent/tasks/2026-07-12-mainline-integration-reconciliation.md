# Mainline Integration Reconciliation Task

Task slug: `mainline-integration-reconciliation-2026-07-12`
Date: 2026-07-12

## Goal

Reconcile `codex/runtime-unified-tables` against the latest `origin/main` by splitting only reviewable, testable, rollback-safe integration slices while preserving current mainline behavior and user-local changes.

## Non-goals

- Do not resolve PR #9 as one opaque 161-commit merge or use blanket ours/theirs strategies.
- Do not modify the user worktree `D:\PolyNexus`, user-local scripts, or unrelated GUI files.
- Do not merge, push, create PRs, close PR #9, or sync local main without explicit authorization.
- Do not change SAXS/DSC/WAXS scientific semantics without focused tests and human review.

## Context and canonical decisions

- Canonical base: `origin/main` at the time each slice is created.
- Canonical GUI/editor/gallery/shared figure lifecycle: current mainline.
- Integration-only features: Unified Tables/results and only provider behavior absent from main.
- SAXS path A: preserve the current provider API and figure IDs; add evidence filtering incrementally.
- Publication roles: `main`, `si`, `diagnostic`; missing evidence defaults to SI.
- User-local files and untracked agent assets are excluded from source integration.

## Affected boundaries

- [x] Analysis engine
- [x] Result/schema contract
- [x] Persistence/export lifecycle
- [x] Documentation/tooling
- [x] GUI/history review boundary
- [ ] CLI behavior

## Acceptance criteria

- [x] Baseline inventory records main/integration refs, patch-equivalent history, conflict surface, and canonical-source matrix.
- [x] Shared figure panel/audit/TIFF/status/persistence slices have focused regression evidence.
- [x] SAXS mode precedence, mixed-series rejection, and evidence-role contract are implemented and tested.
- [x] SAXS evidence-filtering design and execution plan are approved and committed.
- [x] Temperature evidence filtering is implemented with focused tests and separate commits `985f9c2` and `a4231f8`.
- [x] Strain evidence filtering is implemented with focused tests and separate commit `c75888b`.
- [ ] DSC/WAXS providers, Unified Tables, and GUI wiring are separately reviewed and integrated.
- [ ] Replacement PR chain is reviewed, merged, and local main is synchronized.

## Verification commands

Completed for the current checkpoint:

```powershell
python -m pytest tests/test_figure_contracts.py tests/test_figure_pipeline.py tests/test_figure_production.py tests/test_run_figure_manifest.py tests/test_figure_render_plan_core.py tests/test_figure_assets.py tests/test_figure_publication_audit.py tests/test_figure_recovery_pipeline.py tests/test_manifest_editor_shared_plan.py tests/test_saxs_mode_evidence_contract.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_publication_cutover.py -q
python -m compileall -q polynexus/core/figures polynexus/core/saxs_engine
git diff --check
```

Latest checkpoint before final handoff: 89 passed across the cumulative shared/SAXS group; Ruff, py_compile, compileall, and diff-check passed. Full pytest previously exceeded the runtime limit without a reported failure. `scripts/verify.py` is user-local and absent from clean `origin/main`, so the unified verifier has not been run in this isolated worktree.

## Memory and handoff

- [x] Updated `docs/agent/memory/active-work.md`.
- [x] Added decision `docs/agent/memory/decisions/0005-mainline-saxs-evidence-filtering.md`.
- [x] Added acceptance evidence in `docs/acceptance/2026-07-12-mainline-integration-reconciliation-inventory.md`.
- [x] Added final temperature/strain slice hashes and local verification evidence.
- [x] Formal human scientific review of the temperature/strain slices completed with no blocking concerns.
- [ ] External PR review and merge review remain pending.

## Commit and review checkpoint

- Human review required: yes — architecture, data contract, scientific publication semantics, and history/rollback.
- Current commits: `5c3636c` SAXS mode/evidence contract; `961c2c0` SAXS design; `91dd638` SAXS rollout plan; `985f9c2`/`a4231f8` temperature evidence filtering; `c75888b` strain evidence filtering.
- Review-fix commit: `a81af58` persists publication roles, propagates evidence reasons, fixes mode precedence, applies conservative mixed-role aggregation, and validates role values.
- PR #9 remains diagnostic reference only; no push, PR creation, merge, or main synchronization has occurred.

## Review checkpoint — 2026-07-12

- [x] Cumulative read-only code review completed against `origin/main..HEAD`.
- [x] No Critical findings.
- [x] Four Important findings fixed and covered by regression tests.
- [x] Two Minor contract/validation findings fixed or explicitly tracked.
- [x] Formal human scientific review of the temperature/strain filtering behavior completed; no blocking concerns reported.

## Handoff

Current next action: perform human scientific review of the completed temperature/strain filtering slices, then decide whether to proceed to DSC/WAXS or create replacement PRs. No external Git operation has been performed.
