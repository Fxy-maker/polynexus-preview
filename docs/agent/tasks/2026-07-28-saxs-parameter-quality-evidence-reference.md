# SAXS parameter quality-evidence reference

## Status

Implementation complete; checkpointed locally with the explicit allowlist.

## Goal

Allow a consumer of `data/parameters.csv` or `parameters.json` to locate the
authoritative SAXS `quality_evidence.json` audit without copying AI or quality
payloads into the parameter table.

## Affected boundaries

- `polynexus/core/saxs_export_bundle.py`
- `tests/test_saxs_export_bundle.py`
- this task card, its design spec, and implementation plan

## Acceptance criteria

- [x] Successful bundle `parameters.json` contains
      `quality_evidence_file: "quality_evidence.json"`.
- [x] Every serialized `data/parameters.csv` row contains
      `quality_evidence_ref: "../quality_evidence.json"`.
- [x] Existing parameter values, row order, and `quality_evidence.json` audit
      content remain unchanged.
- [x] CSV does not contain candidate configuration, raw q/I, detector arrays,
      or a duplicated AI audit.
- [x] Mixed/non-mapping parameter rows remain safe and caller-owned rows are
      not mutated.
- [x] Focused tests, exact SAXS matrix, task verifier, whitespace check, and
      checkpoint evidence are recorded with actual results.

## Non-goals

No AI call, candidate application, rerun, interpolation, frame repair, new
threshold, publication decision, History schema change, or scientific validity
claim is introduced. `quality_evidence.json` remains authoritative; the new
fields are location references only.

## Implementation plan

1. Add the RED bundle regression for JSON and CSV quality-evidence references.
2. Add the detached JSON metadata and CSV-relative reference at the export
   boundary without mutating parameter rows.
3. Run focused, SAXS, task-scoped, whitespace, and release-boundary checks;
   create one explicit allowlist checkpoint only after fresh verification.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_quality_ref_focus'
python -m pytest -q tests/test_saxs_export_bundle.py tests/test_analysis_run_service.py
python -m pytest (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-parameter-quality-evidence-reference.md --changed --types
git diff --check
```

Full/boundary is not claimed unless the fresh command completes with a real
summary.

## Verification evidence (2026-07-28)

- TDD RED: `1 failed, 10 deselected`; the expected failure was the missing
  `parameters.json["quality_evidence_file"]` field.
- GREEN bundle suite: `11 passed`.
- Focused History/Export matrix: `14 passed in 0.33s`.
- Exact SAXS matrix: `402 passed, 6 warnings in 26.94s`. Warnings are the
  existing Arial glyph and missing EDF geometry-header warnings.
- Task-scoped verifier: exit `0`; task card, memory, Ruff, compile/type,
  quality `283 passed`, preprocessing `106 passed`, and whitespace all passed.
- Fresh `python scripts/verify.py --changed --types --full --boundary`:
  full repository `2832 passed, 16 skipped, 12 warnings` in `1564.34s`,
  followed by a passing boundary audit. The 12 warnings are the existing
  chart-layout, DSC polyfit, SAXS Arial glyph, and missing EDF geometry-header
  warnings.
- `git diff --check` passed. Explicit allowlist checkpoint created locally;
  no push, merge, deployment, or scientific/publication approval is implied.

## Checkpoint

The task was committed locally with `scripts/auto_commit.py` using only the
allowlist below. The final amended commit hash is reported by the agent; no
push was performed.

## Explicit changed-file allowlist

- `polynexus/core/saxs_export_bundle.py`
- `tests/test_saxs_export_bundle.py`
- `docs/agent/tasks/2026-07-28-saxs-parameter-quality-evidence-reference.md`
- `docs/superpowers/specs/2026-07-28-saxs-parameter-quality-evidence-reference-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-parameter-quality-evidence-reference.md`

Parallel GUI/release/memory/scratch files are intentionally outside this
allowlist.
