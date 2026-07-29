---
task_id: 2026-07-29-saxs-1d-review-evidence-binding
kind: scientific-cross-module
status: completed
date: 2026-07-29
title: Bind SAXS 1D reviewer evidence to temperature Figure provenance
---

# SAXS 1D reviewer evidence binding

## Goal

Consume an explicit `saxs.1d` review record in temperature SAXS 1D Figure
evidence, with source matching and fail-closed diagnostics.

## Non-goals

- No new physical threshold, fit, quality-level, or rescue behavior.
- No interpolation, frame fabrication, source guessing, or source rewriting.
- No automatic publication-role promotion or result validation change.
- No static/strain review consumption, `saxs.2d`, GUI review hints, or storage
  deletion.

## Affected boundaries

- `SAXSConfig` optional reviewer payload.
- Existing SAXS Figure-evidence projection and temperature provider handoff.
- Focused review-binding regression tests and durable task evidence.

## Design

The input is `SAXSConfig.scientific_review`, restored by the shared immutable
review-record contract. Existing source provenance is the only binding input:
`SAXSFrameView.source_path`, `data_quality_report.raw_data_ref`, and
`data_quality_report.source_id`. A record is aggregate-accepted only when it
is an accepted, valid `saxs.1d` record and matches every existing temperature
frame. Any missing, malformed, pending, wrong-scope, or mismatched source
remains fail-closed. The snapshot is detached evidence and cannot change
Guinier, quality, physical, AI, rescue, or publication behavior.

## Acceptance criteria

- [x] Complete accepted matching review produces strict-JSON `review_accepted`
      evidence for all temperature frames.
- [x] Missing, invalid, pending, wrong-scope, and partial-source records retain
      fail-closed diagnostic reasons.
- [x] Exact existing source paths and frame/source indices remain visible.
- [x] Static and strain provider roles remain unchanged and do not consume this
      temperature-only review snapshot.
- [x] Focused TDD RED/GREEN, exact SAXS matrix, structured verification, diff
      check, and storage dry-run evidence are recorded.
- [x] One explicit allowlist checkpoint is created with no parallel files.

## Implementation plan

1. Add RED tests for accepted, missing, invalid, wrong-scope, and partial-source
   review payloads at the temperature Figure evidence boundary.
2. Add the optional config payload and a pure detached source-matching
   projection that reuses the shared fail-closed review contract.
3. Thread the payload through the existing temperature Figure provider and
   fallback only; leave static and strain providers unchanged.
4. Run focused GREEN, structured verification, exact SAXS, diff, and storage
   dry-run checks, then checkpoint the explicit allowlist.

## Verification

The authoritative structured check is:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-1d-review-evidence-binding.md --changed --types
```

The exact SAXS matrix must be counted only from a final pytest summary and
exit code `0`; historical or timeout-only output is not evidence of a pass.
Storage commands remain dry-run only and no test directory belongs in the
checkpoint.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_1d_review_evidence_binding.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-1d-review-evidence-binding.md --changed --types
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/config.py`
- `polynexus/core/saxs_engine/figure_evidence.py`
- `polynexus/core/saxs_engine/figure_temperature.py`
- `polynexus/core/saxs_engine/figure_provider.py`
- `tests/test_saxs_1d_review_evidence_binding.py`
- `docs/superpowers/specs/2026-07-29-saxs-1d-review-evidence-binding-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-1d-review-evidence-binding.md`
- `docs/agent/tasks/2026-07-29-saxs-1d-review-evidence-binding.md`
- `docs/agent/memory/active-work.md`

## Current limitations

The shared workspace still has an older unrelated `verify.py --full --boundary`
process tree. Its output is not used as evidence for this task; a fresh exact
SAXS matrix and task-scoped verifier were run independently. Human scientific
review and the later static/strain/2D binding slices remain open.

## Verification record

- TDD RED: `5 failed`; failures were the expected missing
  `scientific_review` evidence key.
- Focused GREEN: `5 passed`; evidence/acceptance regression: `38 passed`; the
  broader review/temperature/Workbench matrix: `82 passed`.
- Task-scoped verifier exited `0`: quality `290`, preprocessing `106`, Ruff,
  compile, type baseline, memory/task checks, and whitespace all passed.
- Exact fresh SAXS matrix exited `0`: `580 passed, 6 warnings` in `561.51s`.
- `git diff --check` and changed-file Ruff exited `0`.
- Storage report/clean remained dry-run only: `41` artifacts,
  `eligible_bytes=0`, `removed=0`; no test directory is in the allowlist.

The explicit checkpoint is created only after the final allowlist audit below.
