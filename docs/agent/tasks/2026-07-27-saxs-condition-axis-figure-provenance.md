# SAXS Condition-Axis Figure Provenance

## Goal

Preserve the existing per-metric `condition_axis` evidence when SAXS figure
provenance is projected into FigureDefinitions and Manifest-backed documents.

## Non-goals

- Do not add a new evidence field or change the `MetricEvidenceSummary`
  contract.
- Do not recalculate, sort, repair, interpolate, or interpret condition axes.
- Do not change figure roles, publication profiles, Workbench text, History,
  or the authoritative bundle-level `quality_evidence.json` contract.
- Do not apply temperature ordering semantics to strain data.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_evidence.py`
- `tests/test_saxs_figure_evidence_binding.py`
- this task card, spec/plan, and durable memory

## Acceptance criteria

- [x] Frame-level metric evidence preserves an existing `condition_axis` in the
  Figure evidence projection.
- [x] Series-level temperature metric evidence preserves the same axis and
  existing source-index/sequence provenance.
- [x] The projection remains detached and strict JSON-safe, including non-finite
  condition values represented as `null`.
- [x] Existing orientation separation, figure roles, missing-evidence fallback,
  and FigurePipeline serialization remain unchanged.
- [x] TDD RED/GREEN, Figure focused matrix, complete SAXS matrix, task
  verifier, and explicit allowlist checkpoint have exact evidence.

## Implementation plan

1. Add frame and series Figure evidence tests containing defective and finite
   condition axes, including strict JSON and detached-value assertions.
2. Extend the existing common metric projection allowlist with the already
   public `condition_axis` key; do not broaden projection to arbitrary fields.
3. Verify temperature/strain FigureDefinitions and Manifest serialization,
   then update memory and create one explicit allowlist checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_condition_axis_figure'
python -m pytest tests/test_saxs_figure_evidence_binding.py tests/test_saxs_figure_document.py -q
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-condition-axis-figure-provenance.md --changed --types
git diff --check
```

## Verification evidence (2026-07-27)

- TDD RED focused Figure/Document matrix: `2 failed, 23 passed, 4 warnings`;
  both failures were the expected missing `condition_axis` projection key.
- GREEN focused Figure/Document matrix: `25 passed, 4 warnings`.
- Figure/provider consumer matrix: `45 passed, 4 warnings`.
- Complete isolated SAXS matrix: `361 passed, 4 warnings`; warnings are the
  existing Arial CJK glyph warnings from SAXS figure layout.
- Task-scoped verifier with isolated `PYTEST_ADDOPTS`: task/memory checks,
  changed Ruff/compile/type, quality `282 passed`, preprocessing `106 passed`,
  and whitespace all passed.
- `git diff --check` passed. The only production change is adding the existing
  `condition_axis` key to the explicit common metric projection allowlist.

## Known limitations

This task proves provenance transport only. It does not prove a physical
transition, validate raw detector geometry, authorize rescue, or authorize
publication.

## Changed-file allowlist

- `polynexus/core/saxs_engine/figure_evidence.py`
- `tests/test_saxs_figure_evidence_binding.py`
- `docs/agent/tasks/2026-07-27-saxs-condition-axis-figure-provenance.md`
- `docs/superpowers/specs/2026-07-27-saxs-condition-axis-figure-provenance-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-condition-axis-figure-provenance.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
