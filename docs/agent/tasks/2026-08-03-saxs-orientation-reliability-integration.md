# SAXS Orientation Reliability Integration

## Goal

Integrate the SAXS orientation reliability chain into local `main` without
bringing the current editor branch's unrelated history or parallel worktree
changes.

## Affected boundaries

- q-resolved orientation reliability and support contracts;
- cross-strain feature tracking;
- explicit tensile-axis transport and results presentation;
- inactive-by-default detector correction plugin;
- read-only orientation advisory and hardened callback lifecycle;
- required core, GUI, RAG, persistence, and focused regression tests.

The data flow under review is `SAXS engine -> result parameters -> 2D review
context -> advisory projection -> GUI worker/results table -> persistence`.

## Non-goals

- no direct merge of the 399-commit editor branch;
- no inclusion of parallel memory, AI-tuning GUI, presentation, generated
  output, pytest-run directories, or unrelated technique changes;
- no push, deploy, data deletion, reset, or overwrite of the source workspace;
- no change to AI tuning, confirmed rerun, mask, calibration, quality, or
  publication authority.

## Integration boundary

The source is `codex/origin-editor-usable-controls`. The integration branch is
based on local `main` and uses an explicit source-file allowlist. The source
history from `codex/saxs-feature-orientation-foundation` is treated as a
dependency baseline; only its final SAXS orientation-related file state is
projected into this integration branch.

## Acceptance criteria

- [ ] Core results preserve deterministic source evidence, explicit axes, support
   gates, correction provenance, and advisory immutability.
- [ ] GUI consumes DTOs/results and rejects stale advisory callbacks without an
   apply or rerun route.
- [ ] Existing rescue/tuning/review/publication gates remain unchanged.
- [ ] Focused SAXS tests, task verification, full boundary checks, Ruff/compile,
   and whitespace checks pass.
- [ ] A checkpoint is created only with an explicit changed-file allowlist.

## Implementation plan

1. Establish a clean integration branch from local `main` and preserve the
   source workspace and parallel worktree changes.
2. Apply the final SAXS orientation/evidence dependency closure through an
   explicit file allowlist, including only required shared renderer and review
   DTO boundaries.
3. Resolve test conflicts by retaining both existing raw-orientation coverage
   and the new q-band, tracking, delta, and reliability assertions.
4. Run focused, complete synthetic SAXS, task verifier, type, boundary, and
   diff checks; record the real EDF environment limitation separately.
5. Create one explicit-allowlist checkpoint and stop before local mainline
   integration if scientific semantics or target worktree state needs review.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-orientation-reliability-integration.md --changed --types
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --changed --types --full --boundary
git diff --check
```

## Known review gate

Scientific semantics and any conflict that changes the meaning of an
orientation value require human review before local mainline integration.
