# SAXS AI orchestrator handoff

## Goal

Connect the existing SAXS AI rescue bridge to the shared preprocessing
orchestrator so that a valid SAXS intent produces auditable candidate-only
plan/decision provenance in the report and engine used for export.

## Non-goals

- Do not call an AI model or invent an intent.
- Do not change SAXS q-I algorithms, quality thresholds, physical evidence, or
  publication roles.
- Do not execute a candidate outside the existing shared transaction and hard
  guards.
- Do not enable tiered-auto without the existing calibrated policy.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `polynexus/orchestrator_preprocess.py`
- `tests/test_saxs_ai_orchestrator_handoff.py`
- SAXS export provenance consumes the resulting engine attributes through its
  existing read-only audit path.

## Implementation plan

1. Expose SAXS-only intent validation from the existing bridge.
2. Validate SAXS intents before generic preprocessing candidate generation.
3. Attach a JSON-safe candidate-only SAXS plan and shared decision wrapper to
   the preprocess report and source engine.
4. Preserve existing generic transaction behavior and verify invalid, shadow,
   confirm, and calibrated-auto safety semantics.

## Acceptance criteria

- [x] SAXS orchestrator rejects an intent missing any protected physical
  feature before running candidates.
- [x] Valid SAXS reports include `saxs_ai_rescue_plan` with
  `candidate_only=true` and `original_preserved=true`.
- [x] Reports include `saxs_ai_rescue_decision`; default shadow remains
  `keep_original` and `apply_allowed=false`.
- [x] The source engine receives JSON-safe plan/decision attributes so the
  existing SAXS export bundle can audit them without executing anything.
- [x] Existing generic preprocessing, SAXS, export, and verifier regressions
  pass.

## Verification

```powershell
python -m pytest tests/test_saxs_ai_orchestrator_handoff.py -q
python -m pytest tests/test_saxs_ai_rescue_bridge.py tests/test_orchestrator_preprocess.py tests/test_orchestrator_preprocess_automation.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-ai-orchestrator-handoff.md --changed --types
```

## Verification evidence (2026-07-27)

- Focused bridge and orchestrator handoff tests: **8 passed**.
- SAXS/orchestrator/preprocess matrix: **383 passed, 4 warnings**. The
  warnings are the existing SAXS Arial CJK glyph warnings.
- Structured task verifier: passed task-card validation, memory validation,
  Ruff, compilation, quality gate (`282 passed`), preprocessing gate (`103
  passed`), and whitespace checks.
- A first export-focused retry hit the pre-existing repository `.pytest_tmp`
  Windows permission cleanup issue; the same export suite was rerun with an
  external basetemp and passed **6 tests**.

## Known limitations

This task wires the existing bridge into the shared report/export path. Model
provider integration, real candidate recalculation on user-confirmed runs, and
human scientific release approval remain separate gates.

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `polynexus/orchestrator_preprocess.py`
- `tests/test_saxs_ai_orchestrator_handoff.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-ai-orchestrator-handoff-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-ai-orchestrator-handoff.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
