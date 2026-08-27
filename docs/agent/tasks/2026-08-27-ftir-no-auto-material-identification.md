---
task_id: 2026-08-27-ftir-no-auto-material-identification
kind: scientific
status: implementation_complete_review_required
date: 2026-08-27
title: Remove implicit FTIR material identification
---

# Remove implicit FTIR material identification

## Goal

Ensure FTIR without an explicit material hint produces material-neutral peaks
and metrics instead of silently selecting a polymer from the built-in library.

## Non-goals

- Do not remove the optional IR peak library.
- Do not change peak detection, preprocessing, fitting, or explicit-material
  band index calculations.
- Do not block generic FTIR analysis when material metadata is absent.

## Affected boundaries

- IR provider result semantics and its evidence projection.
- CLI/Batch/Agent/GUI continue to share the provider result through ComputeRun;
  no new material field is introduced.

## Acceptance criteria

- [ ] Empty `polymer_name` leaves `IRResult.polymer_name` empty and does not
  assign database polymers to peaks.
- [ ] Generic peak positions, areas, widths, and quality metrics remain
  available without material metadata.
- [ ] Explicit `polymer_name` still enables scoped peak assignment and band
  indices.
- [ ] Existing explicit-material tests and real FTIR route remain green.

## Implementation plan

1. Add failing no-material regression tests.
2. Remove the automatic `identify_polymer_from_peaks` fallback from the provider.
3. Verify explicit-material behavior and shared consumers.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_ftir_no_pa6_default.py tests/test_ir_bridge.py tests/test_nmr_shared_entry.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-ftir-no-auto-material-identification.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "fix(ir): remove implicit material identification" `
  --files polynexus/core/ir_engine/core.py tests/test_ftir_no_auto_material_identification.py docs/agent/tasks/2026-08-27-ftir-no-auto-material-identification.md docs/superpowers/specs/2026-08-27-ftir-no-auto-material-identification-design.md docs/superpowers/plans/2026-08-27-ftir-no-auto-material-identification.md docs/acceptance/2026-08-27-ftir-no-auto-material-identification.md
```

## Completion evidence

- `python -m pytest -p no:cacheprovider -q tests/test_ftir_no_auto_material_identification.py tests/test_ir_engine.py tests/test_ftir_no_pa6_default.py` -> `7 passed`.
- `python scripts/verify.py --task docs/agent/tasks/2026-08-27-ftir-no-auto-material-identification.md --changed --types` -> pending final checkpoint.
- The historical `test_ir_orchestrator_runs_noop_round` fixture still fails at
  canonical mapping (`conversion_mapping_ambiguous`) before provider execution;
  it is unrelated to this material-default change and remains recorded.
- Known limitations: material-specific interpretation still requires explicit
  context supplied by Codex/ARS or the user.
- Pre-existing changes left untouched: `active_run.json`, `runs/`, and
  `tests/_tmp_phase3/`.
