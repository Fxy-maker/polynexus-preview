---
task_id: 2026-09-06-format-ingestion-plugin-foundation
kind: architecture
status: implementation_complete_review_required
date: 2026-09-06
title: Add layered format inspection and reader plugin contracts
---

# Add Layered Format Inspection and Reader Plugin Contracts

## Goal

Give every file-backed entry point one deterministic, JSON-safe format
inspection that separates container detection, reader availability, canonical
conversion readiness, and scientific mapping. Known opaque vendor/project
formats must produce an actionable `needs_input` result before a provider can
publish an empty or fabricated calculation.

## Non-goals

- Do not reverse-engineer vendor binaries, Origin projects, or proprietary
  formats in this foundation task.
- Do not dynamically import or execute untrusted third-party plugins.
- Do not infer polymer chemistry, units, columns, or experimental meaning
  solely from a filename or AI suggestion.
- Do not replace the existing CanonicalDataset/ComputeRun or create a second
  result/provenance store.

## Shared objects and entry points

- Objects: immutable `FormatPluginDescriptor`, `FormatInspection`, and the
  existing `ComputeRun` input-inspection projection.
- Core/CLI/Codex: the format registry is the single deterministic inspection
  producer; `ComputeRunService` attaches its result and fails closed for a
  known format with no available decoder. The new `inspect-format` CLI exposes
  the same DTO.
- GUI: unchanged in this task; it can consume the additive ComputeRun DTO in a
  later view-model task.
- Cross-entry rule: no route may maintain a private format classification or
  silently reinterpret a known opaque input.

## Affected boundaries

- New `polynexus.core.input_formats` registry, descriptors, bounded probes,
  and JSON-safe inspection contract.
- `ComputeRun`/`ComputeRunService` additive inspection field and preflight
  handling.
- CLI parser and JSON inspection command.
- Focused contract, registry, ComputeRun, and CLI tests; durable memory.

## Implementation plan

1. Add failing tests for deterministic detection of portable tables, detector
   images, Bruker directories, known vendor opaque containers, unknown binary
   files, and plugin descriptor round-trips.
2. Implement immutable plugin descriptors and a closed built-in registry with
   bounded magic/header probes and explicit reader availability states.
3. Add the `FormatInspection` DTO, stable content identity, actionable reason
   codes, and a public inspection service.
4. Attach inspection to `ComputeRun`; make known opaque formats return
   `needs_input` before provider execution while preserving compatibility for
   unknown or already-supported legacy inputs.
5. Add the `inspect-format` CLI route, run the focused/shared verification, and
   record limitations and follow-up vendor-reader work.

## Acceptance criteria

- [x] The same source and declared technique produce the same inspection ID
  and JSON projection from Core and CLI.
- [x] Portable tables, detector images, Bruker directories/FIDs, and Rigaku
  raw inputs identify their reader route without claiming scientific mapping.
- [x] Netzsch-like DSC/TGA, vendor DMA `.001`, Origin `.opju`, and unsupported
  spreadsheet/project inputs report an explicit missing-reader/export action.
- [x] Known opaque formats cannot reach provider execution through direct
  ComputeRun; unknown inputs retain compatibility behavior with inspection.
- [x] No plugin dynamically executes code or reads beyond bounded inspection
  probes; actual vendor decoder implementation remains a follow-up.
- [x] Existing shared run contracts and legacy tests remain compatible, and
  no raw validation data enters Git.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_input_formats.py tests/test_compute_service.py tests/test_cli_parser.py tests/test_cli_run_single_service.py
python scripts/verify.py --task docs/agent/tasks/2026-09-06-format-ingestion-plugin-foundation.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(input): add layered format inspection contracts" `
  --files docs/agent/tasks/2026-09-06-format-ingestion-plugin-foundation.md `
          polynexus/core/input_formats/__init__.py `
          polynexus/core/input_formats/models.py `
          polynexus/core/input_formats/registry.py `
          polynexus/core/compute/models.py polynexus/core/compute/service.py `
          polynexus/cli/parser.py polynexus/cli/run_format_inspection.py `
          polynexus/__main__.py tests/test_input_formats.py `
          docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

## Completion evidence

- Exact commands and outcomes:
  - `python scripts/validation_pack.py --data-root D:/PolyNexus-validation-data validate --require-local` — `valid: 12 manifest entries`.
  - `python -m pytest -p no:cacheprovider -q tests/test_input_formats.py tests/test_compute_run_projection.py tests/test_compute_models.py tests/test_compute_service.py tests/test_cli_parser.py tests/test_cli_run_single_service.py` — `139 passed, 4 skipped`.
  - `python scripts/verify.py --task docs/agent/tasks/2026-09-06-format-ingestion-plugin-foundation.md --changed --types` — passed: Ruff, compile, task/memory checks, quality `313`, preprocessing `157`, and diff whitespace check.
- Known limitations or follow-up:
  - This is a declarative, bounded inspection foundation, not a decoder for vendor binaries, Origin projects, or arbitrary third-party formats.
  - Reader implementations need isolated execution, licensing review, real-instrument replay, and mapping/uncertainty/capability review before their values can support formal capability promotion or evidence use.
  - GUI import presentation and trusted plug-in installation are later consumer tasks; no dynamic plug-in loading was introduced.
- Pre-existing changes left untouched:
  - `polynexus/core/agent_workflow/service.py`, manuscript plans/specs, `li2020.txt`, `lotz2021.txt`, and `tests/_tmp_phase3/` remain outside this task's checkpoint.
