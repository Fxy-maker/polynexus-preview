# Task: SAXS detector provenance in DataFrame and CSV exports

**Status:** checkpointed at `4d09085`

## Goal

Expose existing per-frame raw-detector provenance in temperature/strain
DataFrames and static/series parameter CSV exports so dirty-data review remains
traceable outside the GUI and nested JSON bundle.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_output_helpers.py`: shared flat export fields.
- `polynexus/core/saxs_engine/saxs_temperature.py`: temperature DataFrame rows.
- `polynexus/core/saxs_engine/saxs_strain.py`: strain DataFrame rows.
- `tests/test_saxs_detector_provenance_dataframe.py`: focused regressions.

## Non-goals

- No detector re-analysis, geometry calibration, mask inference, or validity
  judgment.
- No changes to quality levels, physical thresholds, physical gates, rescue,
  AI, Figure roles, or publication eligibility.
- No replacement of `quality_evidence.json`; the flat columns are a CSV/table
  projection and the nested report remains authoritative.
- No edits to real datasets, generated outputs, or parallel GUI/scratch files.

## Acceptance criteria

- [x] Temperature and strain DataFrames expose stable detector source/level/
  reasons plus geometry and mask provenance columns for every row.
- [x] Static parameter CSV conversion exposes the same flat provenance fields.
- [x] Missing reports remain explicit as empty/None fields; no row or frame is
  invented, copied, interpolated, or dropped.
- [x] Nested field-source ordering and mask shape formatting are deterministic;
  `not_assessed` remains visible without becoming an approval status.
- [x] Existing DataFrame/CSV columns and quality semantics remain unchanged.
- [x] Focused, SAXS, structured verifier, and explicit checkpoint evidence are
  recorded.

## Implementation plan

1. Add RED tests for temperature, strain, static CSV, and missing report rows.
2. Add one shared flat projection helper in `saxs_output_helpers.py`.
3. Reuse it from temperature/strain DataFrames and static parameter CSV
   conversion.
4. Run focused/consumer/SAXS verification, update durable memory, and checkpoint
   only the explicit allowlist.

## Verification

```powershell
python -m pytest -q tests/test_saxs_detector_provenance_dataframe.py tests/test_saxs_output_helpers.py tests/test_saxs_mode_evidence_propagation.py --basetemp C:\Temp\PolyNexus_saxs_detector_dataframe_redgreen
& python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName) --basetemp C:\Temp\PolyNexus_saxs_detector_dataframe_saxs_matrix
$taskPytestOptions = '--basetemp=C:\Temp\PolyNexus_saxs_detector_dataframe_verify'; $env:PYTEST_ADDOPTS = $taskPytestOptions; python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-detector-provenance-dataframe-export.md --changed --types; Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
git diff --check
```

### Recorded evidence

- TDD RED was completed before implementation; the new contract tests failed
  for the missing flat fields while existing helper/propagation tests passed.
- Focused GREEN and consumer matrix: `21 passed in 0.38s`.
- Exact SAXS file matrix, split across four isolated basetemps: `383 passed,
  6 warnings` (`106 + 92 + 100 + 85`); warnings are existing Arial glyph and
  EDF geometry-header warnings.
- Structured verifier exited `0` with task/memory checks, Ruff, compile/type
  baseline, quality `283 passed`, preprocessing `106 passed`, and whitespace.
- The first unsplit matrix invocation produced only partial output and was
  discarded as evidence; no process remained. The four fresh shards above are
  authoritative. The verifier reported only existing CRLF-to-LF warnings for
  the touched legacy modules.
- Explicit allowlist checkpoint: `4d09085` (created by
  `scripts/auto_commit.py`; no push).

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-28-saxs-detector-provenance-dataframe-export.md`
- `docs/superpowers/specs/2026-07-28-saxs-detector-provenance-dataframe-export-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-detector-provenance-dataframe-export.md`
- `polynexus/core/saxs_engine/saxs_output_helpers.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_detector_provenance_dataframe.py`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`

## Scientific limitation

Flat export fields describe provenance only. Detector geometry calibration,
beam-center interpretation, mask validity, saturation meaning, and publication
approval remain human scientific gates.
