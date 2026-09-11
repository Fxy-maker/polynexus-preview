---
task_id: 2026-09-11-netzsch-ngb-reader-route
kind: architecture
status: implementation_complete_review_required
date: 2026-09-11
title: Add bounded native reader routes for observed Netzsch NGB inputs
---

# Add Bounded Native Reader Routes for Observed Netzsch NGB Inputs

## Goal

Decode the observed public Netzsch DSC `.ngb-sd7` and TGA `.ngb-ds1` input
families into the existing `CanonicalExperiment` and `ComputeRun` pipeline,
with raw source, decoded signal, unit, layout, and reader-version provenance.

## Non-goals

- Do not claim support for every `.ngb` file, Proteus version, instrument, or
  vendor binary layout.
- Do not infer calibration, heat-flow sign, sample mass, thermal programme,
  event assignment, or material identity when the source does not provide it.
- Do not mutate original archives or external validation data, nor add it to Git.
- Do not create a second analysis, run, or provenance representation.

## Shared objects and entry points

- Objects: `FormatInspection`, `CanonicalExperiment`, `Measurement`, and
  `ComputeRun`.
- AI/Codex/CLI: the existing conversion and direct-run services remain the sole
  producer; public replay exercises the same route.
- GUI: unchanged implementation; its worker already uses the same converter
  registry and will receive ordinary `ComputeRun` output.
- Cross-entry rule: decoder registration, canonical conversion, direct CLI
  computation, and public replay must produce one shared representation.

## Affected boundaries

- Input-format inspection and bounded native reader detection.
- Canonical DSC/TGA conversion and shared `ComputeRun` execution.
- Public validation replay manifest and external validation report.
- AI/Codex/CLI and GUI consume the existing shared objects; no private result
  path is added.

## Context and output budget

- Read first: `AGENTS.md`, `README.md`, agent memory, input-format contracts,
  canonical converter registry, and public validation adapter.
- Search scope: the Netzsch reader/converter, input-format registry, DSC engine,
  focused tests, and the external five-case replay manifest.
- Expand only for: architecture/scientific semantics needed to verify the
  observed binary layout and TGA signal meaning.
- Report: changed files, exact verification, replay evidence, limitations, and
  untouched pre-existing changes.

## Implementation plan

1. Add bounded readers for the observed DSC ZIP/stream and TGA `CDbTable`
   layouts, with fail-closed signatures and source-block provenance.
2. Convert decoded segments through the existing `CanonicalExperiment` and
   `ComputeRun` contracts without inventing calibration or sample mass.
3. Add synthetic reader and shared-run regression tests, then replay the real
   public DSC/TGA cases twice through `polynexus public-validate`.
4. Update the external replay manifest and durable project memory, preserving
   scientific-review and capability-promotion boundaries.
5. Run focused tests and the structured verifier, then create an allowlisted
   local checkpoint without push or merge.

## Acceptance criteria

- [x] The verified DSC ZIP/`CDbTable` and TGA database signatures are detected
  separately; malformed or unrecognised layouts fail closed before provider
  execution.
- [x] Decoded source columns retain their exact labels, units, stream/layout
  provenance, and reader version before existing technique-specific mapping.
- [x] Each supported source reaches the existing DSC or TGA canonical template
  and `ComputeRun`; public replay is updated from expected `needs_input` to its
  observed deterministic status only after a real replay succeeds twice.
- [x] Synthetic fixtures prove the bounded reader contract without committing
  public raw data.
- [x] This remains parser/replay evidence only; capability promotion,
  calibration, uncertainty, and scientific interpretation stay excluded.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_netzsch_ngb_reader.py tests/test_input_formats.py tests/test_compute_service.py tests/test_public_validation.py tests/test_cli_public_validation.py
python scripts/verify.py --task docs/agent/tasks/2026-09-11-netzsch-ngb-reader-route.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(input): read observed Netzsch NGB layouts" `
  --files docs/agent/tasks/2026-09-11-netzsch-ngb-reader-route.md `
          polynexus/readers/netzsch_ngb_reader.py `
          polynexus/core/canonical_experiments/netzsch.py `
          polynexus/core/canonical_experiments/registry.py `
          polynexus/core/input_formats/registry.py `
          polynexus/core/dsc.py `
          tests/test_netzsch_ngb_reader.py tests/test_input_formats.py `
          docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes: Pending final structured verification. The
  external `public-validate` replay passed all five cases; DSC/TGA each ran
  twice with matching output hashes and preserved raw hashes.
- Known limitations or follow-up: Observed layouts only; non-observed NGB
  layouts, calibration, absolute TGA mass semantics, uncertainty, independent
  replay, standards/negative controls, and capability promotion remain open.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`
  and unrelated untracked plans, specs, literature text, and test diagnostics.
