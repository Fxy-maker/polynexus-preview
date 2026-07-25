# NMR analysis evidence persistence

## Goal

Make the ordinary NMR engine path attach the shared `AnalysisEvidence` DTO to
the `AnalysisResult` consumed by GUI persistence, so NMR peak, signal,
assignment, and crystallinity confidence fields survive into SampleDB and
History.

## Non-goals

- Do not change NMR peak detection, assignment, crystallinity, or validation
  thresholds.
- Do not invent evidence for spectra beyond the representative spectrum already
  used by the single run result; the spectrum count remains explicit metadata.
- Do not claim real-data, restarted-GUI, or scientific review acceptance from a
  synthetic engine-assembly regression.

## Affected boundaries

- `polynexus/core/nmr.py`: ordinary `NMREngine.analyze()` result assembly.
- `tests/test_nmr_engine.py`: unified evidence regression.
- NMR Workbench/History persistence contracts, which already serialize the
  `AnalysisResult` evidence payload.

## Acceptance criteria

- [x] A normal NMR analysis attaches JSON-safe evidence with `technique=NMR`.
- [x] Peak count and assignment-gated Xc status are present in the shared
  evidence sections.
- [x] Existing SampleDB persistence tests continue to preserve evidence.
- [ ] Real four-partition GUI/export/restart acceptance remains a separate
  human-review boundary.

## Implementation plan

1. Add a failing NMR engine regression that assembles a typed result and
   requires the shared evidence payload on `AnalysisResult`.
2. Build evidence from the existing typed NMR parameter contract without
   changing peak detection, assignment, or validation behavior.
3. Run the NMR persistence and real-reader/core matrices, then run Ruff and
   the repository's structured verifier with an external pytest basetemp.
4. Record the code-level evidence handoff and the remaining real GUI/restart
   limitation in the acceptance and memory documents.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_nmr_evidence_verify'
python -m pytest tests/test_nmr_engine.py::test_nmr_engine_analysis_attaches_unified_evidence_for_history_persistence tests/test_analysis_run_service.py -q
python -m ruff check polynexus/core/nmr.py tests/test_nmr_engine.py
python scripts/verify.py --task docs/agent/tasks/2026-07-25-nmr-evidence-persistence.md --changed --types
```

## Known limitation

The repository's real `.jdf` fixtures validate reader and core-analysis
behavior, but there is no registered vendor-format NMR evaluation manifest or
restarted desktop visual record. Those remain explicit release-review items.
