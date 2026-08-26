---
task_id: 2026-08-26-optional-vendor-converters
kind: architecture
status: implementation_complete_review_required
date: 2026-08-26
title: Route generic 1-D templates and isolate vendor converters
---

# Route generic 1-D templates and isolate vendor converters

## Goal

Make generic FTIR/SAXS/WAXS table conversion the canonical default while
retaining vendor/directory compatibility as a separate fallback boundary.

## Non-goals

- No new vendor-specific parser.
- No DSC thermal-program conversion.
- No GUI, Batch, Codex, or provider-engine migration.
- No scientific interpretation or evidence promotion.

## Shared objects and entry points

- Objects: `ConversionOutcome`, `CanonicalExperiment`, capability item results.
- AI/Codex/CLI/GUI: unchanged consumers in this slice; all future consumers
  read the same canonical outcome and item tuple.
- Producer: `CanonicalConverterRegistry`; compatibility fallback remains
  source-bound and does not invent measurements.

## Implementation plan

1. Add registry tests for generic-ready, generic-ambiguous, and vendor/directory
   compatibility outcomes.
2. Route supported table extensions through the generic converter and preserve
   non-ready outcomes without fallback; expose the finite capability handoff.
3. Run canonical, capability, DSC regression, and structured verification tests.
4. Record the optional-adapter boundary and create an allowlisted checkpoint.

## Affected boundaries

- `polynexus.core.canonical_experiments.registry`: generic-first routing and
  explicit compatibility fallback.
- `polynexus.core.canonical_experiments.capabilities`: finite capability
  handoff for ready generic templates.
- Existing provider engines and entry points remain unchanged.

## Acceptance criteria

- [x] CSV/TXT/Excel IR/SAXS/WAXS inputs that map deterministically produce the
  appropriate `spectrum_1d.v1` or `scattering_1d.v1` template.
- [x] Generic mapping ambiguity remains `needs_input` and does not fall back to
  a raw envelope.
- [x] Vendor-like unsupported formats and directories retain the old
  compatibility envelope behavior.
- [x] Generic ready templates can produce the finite capability item tuple.
- [x] Existing DSC, unknown-technique, and replay behavior remains green.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_canonical_converter_registry.py tests/test_canonical_one_dimensional.py tests/test_capability_execution.py tests/test_canonical_experiment_templates.py
python scripts/verify.py --task docs/agent/tasks/2026-08-26-optional-vendor-converters.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(core): route generic canonical converters" `
  --files docs/superpowers/specs/2026-08-26-optional-vendor-converters-design.md docs/agent/tasks/2026-08-26-optional-vendor-converters.md polynexus/core/canonical_experiments/registry.py polynexus/core/canonical_experiments/capabilities.py tests/test_canonical_converter_registry.py tests/test_capability_execution.py
```

## Completion evidence

- Exact commands and outcomes: focused canonical/capability/DSC matrix `85
  passed`; structured verification is recorded below.
- Structured verification: `python scripts/verify.py --task
  docs/agent/tasks/2026-08-26-optional-vendor-converters.md --changed --types`
  passed task-check, Ruff, compile, quality, preprocessing, and whitespace.
- Known limitations: vendor readers remain optional future adapters; DSC and
  consumer migration are separate tasks.
- Pre-existing changes left untouched: none.
