# SAXS AI prompt protection contract

## Goal

Make the SAXS AI preprocessing prompt explicit about the protected physical
features required by the SAXS rescue bridge, so valid intents can be produced
without weakening the fail-closed validator.

## Non-goals

- Do not relax intent validation or hard guards.
- Do not call a model, execute candidates, or change q-I analysis.
- Do not alter non-SAXS scientific semantics.

## Affected boundaries

- `rag/prompt_builder.py`
- `tests/test_saxs_prompt_builder.py`
- prompt-contract task/spec/plan and durable memory.

## Implementation plan

1. Render the policy protected-feature list in the preprocessing intent
   contract.
2. Add SAXS-specific wording that all listed physical features are required.
3. Verify the prompt contains every current SAXS protected feature and keep the
   existing prompt regressions green.

## Acceptance criteria

- [x] SAXS preprocessing prompts list all seven bridge-required protected
  features: weak peaks, integrated area, Guinier region, beamstop boundaries,
  peak position, peak width, and physical parameters.
- [x] The prompt says the full SAXS list must be included, rather than using a
  vague placeholder.
- [x] Existing prompt, SAXS, preprocess, and structured verifier checks pass.

## Verification

```powershell
python -m pytest tests/test_saxs_prompt_builder.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-ai-prompt-protection-contract.md --changed --types
```

## Verification evidence (2026-07-27)

- Prompt builder suite (`tests/test_saxs_prompt_builder.py` and
  `tests/test_prompt_builder.py`): **20 passed**.
- Ruff, py_compile, and `git diff --check`: passed.
- The touched prompt-builder file's seven pre-existing Ruff blockers were
  removed mechanically; no prompt behavior outside the protected-feature
  contract was changed.

## Known limitations

Prompt guidance does not replace the core validator. Malformed or incomplete
model output still fails closed and remains auditable.

## Changed-file allowlist

- `rag/prompt_builder.py`
- `tests/test_saxs_prompt_builder.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-ai-prompt-protection-contract-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-ai-prompt-protection-contract.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
