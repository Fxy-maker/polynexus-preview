---
task_id: 2026-08-27-nmr-shared-entry-no-material-default
kind: architecture
status: implementation_complete_review_required
date: 2026-08-27
title: Route NMR through shared canonical entry without material defaults
---

# Route NMR through shared canonical entry without material defaults

## Goal

Make NMR use the same canonical conversion and `ComputeRun` provenance path as
the other retained techniques, while keeping generic NMR calculations usable
without a material name or an implicit material database match.

## Non-goals

- Do not change peak detection, deconvolution, relaxation fitting, or ppm-axis
  algorithms.
- Do not delete the optional polymer shift library.
- Do not add a GUI material database or make material metadata mandatory.
- Do not promote NMR assignments or Xc to publication conclusions.

## Shared objects and entry points

- Objects: `CanonicalExperiment`, `AnalysisPlan`, `ComputeRun`, `AnalysisResult`.
- AI/Codex/CLI: `ComputeRunService` and single/batch analysis consume the same
  NMR canonical template and preserve source/plan linkage.
- GUI: existing NMR result DTOs remain unchanged; GUI receives the shared run
  projection and does not branch on provider internals.
- Cross-entry rule: table NMR inputs use the generic one-dimensional converter;
  FID/vendor directories use a source-bound NMR envelope, then the provider
  runs through the same `ComputeRun` producer.

## Affected boundaries

- Conversion: `canonical_experiments.one_dimensional` and converter registry.
- Shared execution: `compute.service` conversion dispatch.
- Provider semantics: NMR material scope remains optional and explicit.
- Consumers: CLI, Batch, Agent/Codex, and GUI continue to consume `ComputeRun`.

## Implementation plan

1. Add failing NMR conversion and no-material regression tests.
2. Register NMR ppm tables and opaque NMR source envelopes.
3. Attach NMR templates in `ComputeRunService`.
4. Run focused provider/consumer verification and record limitations.

## Acceptance criteria

- [ ] CSV/TXT/Excel NMR tables convert to `nmr.spectrum.v1` with source locators.
- [ ] FID/vendor directory NMR inputs receive a source-bound NMR canonical
  template instead of `canonical_converter_unregistered`.
- [ ] `ComputeRun` persists the NMR template and result linkage for CLI/Batch,
  Agent/Codex, and GUI persistence routes.
- [ ] No `polymer_name` means generic peak metrics remain available, no
  material-library assignment is fabricated, and solid-state NMR Xc remains
  unavailable unless explicit phase assignments are present.
- [ ] An explicit project-context material name is passed as a provider hint,
  but is recorded as context rather than proof from the instrument file.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_canonical_converter_registry.py tests/test_compute_service.py tests/test_nmr_engine.py tests/test_nmr_shared_entry.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-nmr-shared-entry-no-material-default.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(nmr): route shared compute entry without material defaults" `
  --files polynexus/core/canonical_experiments/one_dimensional.py polynexus/core/canonical_experiments/registry.py polynexus/core/compute/service.py polynexus/core/nmr_engine/core.py tests/test_nmr_shared_entry.py docs/agent/tasks/2026-08-27-nmr-shared-entry-no-material-default.md docs/superpowers/specs/2026-08-27-nmr-shared-entry-no-material-default-design.md docs/superpowers/plans/2026-08-27-nmr-shared-entry-no-material-default.md
```

## Completion evidence

- `python -m pytest -p no:cacheprovider -q tests/test_nmr_shared_entry.py tests/test_canonical_converter_registry.py tests/test_compute_service.py tests/test_nmr_engine.py` -> `77 passed, 3 skipped`.
- `python scripts/verify.py --task docs/agent/tasks/2026-08-27-nmr-shared-entry-no-material-default.md --changed --types` -> selected checks passed, including quality gates (`310` focused and `157` preprocessing tests).
- `git diff --check` -> passed.
- Known limitations or follow-up: real six-sample replay, GUI gallery cutover,
  cross-technology package handoff, and historical release failures remain
  separate goal stages. NMR vendor bytes are preserved as an opaque envelope;
  they are not decoded by the canonical converter.
- Pre-existing changes left untouched: `active_run.json`, `runs/`, and
  `tests/_tmp_phase3/`.
- Pre-existing changes left untouched: `active_run.json`, `runs/`, and
  `tests/_tmp_phase3/`.
