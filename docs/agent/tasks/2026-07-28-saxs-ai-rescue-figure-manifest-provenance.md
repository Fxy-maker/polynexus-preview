# SAXS AI rescue Figure/Manifest provenance

## Goal

Bind existing SAXS AI rescue plan/decision/replay/confirmed-rerun evidence to
FigureDefinitions and Manifest-backed figure documents as compact, detached,
read-only provenance.

## Non-goals

- No model call, candidate application, rerun, interpolation, or frame repair.
- No new physical/quality threshold or publication-role change.
- No raw q/I, detector arrays, full result objects, or full candidate configs in
  figure recipes.
- No change to Workbench, History, or authoritative Export semantics.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_evidence.py`
- `polynexus/core/saxs_engine/figure_provider.py`
- `polynexus/core/saxs_engine/figure_static.py`
- `polynexus/core/saxs_engine/figure_temperature.py`
- `polynexus/core/saxs_engine/figure_strain.py`
- `tests/test_saxs_figure_evidence_binding.py`
- This task card, spec, and plan

## Acceptance criteria

- [x] Existing AI plan/decision/replay/confirmed-rerun metadata appears under
      `recipe.evidence.quality_provenance.ai_rescue` when valid.
- [x] Projection is strict JSON-safe, detached, compact, and excludes raw
      arrays/full configs; malformed or absent values produce no AI record.
- [x] Static, temperature, and strain providers pass the existing engine audit
      without changing frame eligibility or publication roles.
- [x] FigurePipeline Manifest documents retain the same provenance mapping.
- [x] Focused tests, exact SAXS matrix, task verifier, and diff check have exact
      recorded results; full/boundary is reported separately if not run.
- [x] One explicit `auto_commit.py` checkpoint contains only the allowlist.

## Implementation plan

1. Add RED projection/provider/Manifest regressions.
2. Implement the compact projector and pass existing engine state at providers.
3. Run focused/SAXS/task verification and create one allowlist checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_ai_figure_focus'
python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_figure_document.py tests/test_saxs_export_bundle.py
$exit = $LASTEXITCODE
Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
exit $exit

$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_ai_figure_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-ai-rescue-figure-manifest-provenance.md --changed --types
$exit = $LASTEXITCODE
Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
exit $exit

python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
git diff --check
```

## Known limitations

This task binds provenance but does not decide whether an AI candidate is
scientifically valid or publishable. Existing deterministic rerun/physical/
quality gates, human scientific review, restarted-GUI review, and release
approval remain open. Full/boundary verification is not required for this
consumer slice unless actually run and completed.

## Verification evidence (2026-07-28)

- TDD RED: `2 failed, 7 passed`; failures were the missing Figure/Manifest
  `ai_rescue` projection and the missing `ai_rescue` argument.
- GREEN figure evidence: `10 passed`.
- Focused Figure/Manifest/Export/Workbench consumer matrix: **66 passed, 4
  warnings**. Warnings are the existing Arial CJK glyph warnings.
- Exact SAXS matrix after repairing the legacy temperature-provider接线:
  **401 passed, 6 warnings**. The earlier intermediate run had 12 NameError
  failures from that接线 error and is not counted as final evidence.
- Task verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-ai-rescue-figure-manifest-provenance.md --changed --types`
  -> exit 0; task/memory, Ruff, compile/type, quality **283 passed**,
  preprocessing **106 passed**, and whitespace all passed. The verifier also
  discovered pre-existing `tests/_tmp_phase3/test_visual_audit_capture.py`; it
  was untouched and is outside the checkpoint.
- Full/boundary verification was not run for this consumer slice; no
  full/boundary pass is claimed.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_evidence.py`
- `polynexus/core/saxs_engine/figure_provider.py`
- `tests/test_saxs_figure_evidence_binding.py`
- `docs/agent/tasks/2026-07-28-saxs-ai-rescue-figure-manifest-provenance.md`
- `docs/superpowers/specs/2026-07-28-saxs-ai-rescue-figure-manifest-provenance-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-ai-rescue-figure-manifest-provenance.md`
