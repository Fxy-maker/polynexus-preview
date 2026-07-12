# Agent Task

## Goal

Evaluate the legacy gallery fallback and record the default manifest-only policy
without changing production behavior.

## Non-goals

- Do not re-enable automatic legacy fallback in the normal gallery.
- Do not migrate or delete historical output directories.
- Do not change the manifest schema or recovery classification rules.
- Do not claim that legacy rendered assets are object-editable or publication-ready.

## Acceptance criteria

- [x] Normal gallery behavior is documented as active-manifest-only.
- [x] Legacy recursive discovery is documented as an explicit recovery-only path.
- [x] Recovery isolation, capability honesty, and active-run safety are documented.
- [x] Automatic fallback, explicit recovery, and temporary dual-mode options are compared.
- [x] Concrete triggers for revisiting the decision are recorded.
- [x] Existing focused gallery/recovery/quality-gate tests pass.

## Affected boundaries

- [x] GUI gallery and recovery entry points
- [x] Manifest-backed persistence
- [x] Historical figure recovery policy
- [x] Agent architecture documentation

## Implementation plan

1. Inspect the active gallery, manifest repository, legacy recovery service, and existing tests.
2. Compare automatic fallback, explicit recovery, and temporary dual-mode strategies.
3. Record the selected manifest-only policy, safety boundaries, risks, and revisit triggers.
4. Run focused tests and validate the task card and changed documentation.

## Verification

```powershell
python -m pytest tests/test_plot_gallery_service.py tests/test_legacy_figure_recovery.py tests/test_legacy_figure_recovery_service.py tests/test_main_window_figure_mixin.py tests/test_quality_gate.py -q
python scripts/task_check.py --task docs/agent/tasks/2026-07-12-legacy-gallery-fallback-strategy.md
python scripts/verify.py --changed --types
git diff --check
```

## Review checkpoint

- Decision: retain manifest-only normal gallery and explicit legacy recovery.
- Production Python files changed: none.
- Strategy document: `docs/superpowers/specs/2026-07-12-legacy-gallery-fallback-strategy.md`
- Decision memory: `docs/agent/memory/decisions/0003-manifest-only-gallery-discovery.md`
- Focused tests: 50 passed.
- Task-card validation: passed with the existing `D:\PolyNexus\scripts\task_check.py` against this worktree's task card.
- `git diff --check`: passed.
- The `main` baseline used for this branch does not track `scripts/verify.py`; no production Python files changed, so changed-file Ruff/compile checks are not applicable to this documentation-only task.
- The optional memory helper could not validate this branch because the same baseline does not track `docs/agent/memory/README.md`, `current-state.md`, or `known-issues.md`; existing user-worktree copies were left untouched.
- Human review: user direction explicitly selected the manifest-only default; future changes require architecture review.
- Status: strategy complete; implementation remains intentionally deferred.
