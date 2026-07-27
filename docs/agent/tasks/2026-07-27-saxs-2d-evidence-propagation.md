# SAXS 2D Evidence Mode Propagation

## Goal

Close the existing 2D detector-quality and orientation evidence transport
boundary across static, temperature, and strain SAXS modes, including
Workbench diagnostics, History parameters, and `quality_evidence.json`.

## Non-goals

- No new raw-detector reader, pyFAI geometry, mask inference, or beam-center inference.
- No new anisotropy/orientation calculation or scientific threshold calibration.
- No AI model call, candidate apply, publication authorization, push, merge, or deploy.
- No interpretation of orientation as a generic 1D metric trend or material mechanism.

## Affected boundaries

- Core contract and DTOs: `polynexus/core/saxs_engine/saxs_quality_contracts.py`, `core.py`, `saxs_temperature.py`, `saxs_strain.py`.
- Shared mode transport and parameters: `polynexus/core/saxs_batch_helpers.py`, `polynexus/core/saxs.py`.
- Reproducible export: `polynexus/core/saxs_export_bundle.py`.
- Workbench/history/export regression tests and durable memory.

## Acceptance criteria

- [x] Existing detector/orientation payloads are deep-copied through static, temperature, and strain frame/point payloads.
- [x] Partial mode summaries preserve missing counts, source reason codes, and conservative levels.
- [x] Temperature evidence remains aligned to `source_index` after temperature sorting.
- [x] No summary is emitted when no 2D evidence was supplied.
- [x] Workbench diagnostics display nested 2D evidence without adding orientation to generic 1D review text.
- [x] History and export preserve mode/frame evidence with strict JSON (`allow_nan=False`).
- [x] Existing SAXS tests and the structured verifier pass.
- [x] One atomic checkpoint is created with an explicit changed-file allowlist.

## Implementation plan

1. Extend the shared SAXS quality-copy helper and add conservative detector/orientation summary builders; preserve missing frames and source reason codes.
2. Add optional 2D evidence fields to static, temperature, and strain DTOs; copy only from successful existing analysis results and aggregate only supplied evidence.
3. Align temperature frame evidence by `source_index`, attach static batch summaries, and expose all mode/frame fields through parameters without mutating source objects.
4. Preserve the fields through Workbench diagnostics, History parameters, and `quality_evidence.json`; keep orientation separate from generic 1D metric review text.
5. Run focused tests, the full SAXS matrix, and the task-scoped verifier; update durable memory and create one explicit-allowlist checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_2d_propagation'
python -m pytest tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_mode_evidence_propagation.py -q
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-2d-evidence-propagation.md --changed --types
```

## Verification evidence (2026-07-27)

- TDD RED was observed during initial collection because the new shared 2D
  summary function did not exist; after implementation the focused propagation
  file passed `11 tests`.
- Focused compatibility matrix passed `53 tests`.
- Full SAXS file matrix passed `301 tests, 4 warnings`; warnings are the
  existing Arial CJK glyph warnings from SAXS figure layout.
- Structured verifier passed task/memory validation, changed Ruff, compile,
  type baseline, quality gate `282`, preprocessing gate `106`, and whitespace.

## Checkpoint

The final atomic checkpoint is created by `scripts/auto_commit.py` with the
changed-file allowlist below; the resulting commit hash is reported at handoff.

## Known limitations

This task transports only evidence already produced upstream. Real raw-detector
coverage, geometry/mask provenance, orientation sequences, and scientific
publication sign-off remain separate review items.

## Changed-file allowlist

- `polynexus/core/saxs_batch_helpers.py`
- `polynexus/core/saxs_export_bundle.py`
- `polynexus/core/saxs.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_2d_evidence_propagation.py`
- `tests/test_saxs_batch_parameters.py`
- `tests/test_saxs_export_bundle.py`
- `tests/test_saxs_workbench_series_evidence.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-2d-evidence-propagation-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-2d-evidence-propagation.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`
