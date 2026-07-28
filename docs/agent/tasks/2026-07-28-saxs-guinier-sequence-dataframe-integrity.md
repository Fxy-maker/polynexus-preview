---
kind: task
status: completed
date: 2026-07-28
title: Project existing Guinier sequence integrity into temperature DataFrame
---

# SAXS temperature Guinier sequence integrity projection

## Goal

Expose the existing `GuinierSequenceEvidence` frame/source integrity facts in
the temperature result DataFrame and CSV projection so a reviewer can see why
a sequence is diagnostic without opening nested JSON.

## Decision

Add a read-only flat projection beside the existing sequence level and reason
columns. Tuple/list index fields use the existing deterministic `|`-joined
format; the explicit `source_index_order_reordered` boolean is preserved as a
boolean. A missing sequence payload produces empty fields. The projection
does not derive new status, validate a new threshold, or reconstruct any frame.

## Non-goals

- Do not change Guinier fitting, qRg gates, sequence level calculation, or
  temperature sorting.
- Do not infer source-index gaps, reorder rows, interpolate, copy, or rescue
  frames.
- Do not change Workbench, Figure, Manifest, Export, History, AI, or
  publication eligibility semantics beyond consuming the existing DataFrame
  columns.
- Do not edit real datasets, generated outputs, or parallel GUI/editor files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`: flat sequence evidence
  projection used by `TempSeriesResult.to_dataframe()`;
- `tests/test_saxs_temperature_guinier_evidence.py`: populated and missing
  payload regressions;
- this task card, its design/spec, implementation plan, and durable memory.

## Implementation plan

1. Add focused RED tests for a populated sequence payload and an absent
   payload, including caller-owned input preservation.
2. Add a fixed-key, read-only DataFrame projection for the existing sequence
   index and reorder fields.
3. Run the focused matrix, exact SAXS matrix, task-scoped verifier, and diff
   check with external basetemps.
4. Record exact evidence and create one checkpoint using the explicit
   allowlist, leaving parallel files untouched.

## Acceptance criteria

- [x] The DataFrame exposes existing frame/source, missing, diagnostic,
  invalid-temperature, duplicate-temperature, nonmonotonic-temperature,
  continuity, duplicate-source, invalid-source, and reorder fields.
- [x] Values are copied deterministically without mutating the nested payload;
  no field is computed from row position or from a new scientific rule.
- [x] An absent sequence payload preserves row count and emits empty fields.
- [x] Existing sequence level/reason columns, per-frame source order, and all
  existing DataFrame columns remain unchanged.
- [x] TDD RED/GREEN, SAXS matrix, task verifier, diff check, and explicit
  allowlist checkpoint are recorded with actual results.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_guinier_dataframe_redgreen'
python -m pytest -q tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_data_quality_dataframe.py
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_guinier_dataframe_matrix
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_saxs_guinier_dataframe_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-guinier-sequence-dataframe-integrity.md --changed --types
git diff --check
```

Full/boundary verification is reported only if a fresh run returns a pytest
summary and exit code 0; a timeout or no-summary run is an explicit limitation.

## Verification evidence

- TDD RED: `2 failed, 7 deselected`; both failures were the expected missing
  sequence-integrity DataFrame fields.
- Focused GREEN/compatibility matrix: `14 passed in 0.34s`.
- Exact SAXS matrix: `481 passed, 6 warnings in 260.61s`. The warnings are the
  existing Arial CJK glyph and missing EDF geometry-header warnings.
- Structured verifier exited `0`: task/memory checks, changed-file Ruff,
  compile, type baseline, quality gate `287 passed`, preprocessing gate `106
  passed`, and whitespace checks all passed.
- `git diff --check` exited `0`; Git reported the existing CRLF-to-LF warning
  for the touched legacy module.
- No fresh full/boundary result is claimed for this slice. The pre-existing
  full/boundary process was left untouched and has no result attributable to
  this change.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_temperature_guinier_evidence.py`
- `docs/agent/tasks/2026-07-28-saxs-guinier-sequence-dataframe-integrity.md`
- `docs/superpowers/specs/2026-07-28-saxs-guinier-sequence-dataframe-integrity-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-guinier-sequence-dataframe-integrity.md`
- `docs/agent/memory/active-work.md`

Pre-existing `current-state.md`, scratch directories, `.superpowers/`, GUI
drafts, and running-test outputs are intentionally outside this allowlist.

## Checkpoint

After fresh verification, create one local checkpoint with
`scripts/auto_commit.py` and exactly the allowlist above. Do not push, merge,
deploy, or claim scientific/publication approval.
