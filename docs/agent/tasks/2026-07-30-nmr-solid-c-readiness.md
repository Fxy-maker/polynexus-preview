---
task_id: 2026-07-30-nmr-solid-c-readiness
kind: scientific-semantics
status: completed
date: 2026-07-30
title: Surface NMR solid-C assignment and axis readiness
---

# NMR solid-C readiness

## Goal

Expose existing NMR solid-C assignment and ppm-axis boundaries in shared
evidence and Results review text without supplying scientific assignments.

## Non-goals

- Do not change peak detection, assignment, Xc calculations, or thresholds.
- Do not reinterpret JEOL metadata as ppm or calibrate the axis.
- Do not change scientific review decisions or Figure/Manifest roles.
- Do not touch SAXS, real NMR files, or temporary artifacts.

## Affected boundaries

- `polynexus/core/analysis_evidence_nmr.py`: JSON-safe readiness projection.
- `polynexus/gui/results_review_service.py`: shared Results review summary.
- `polynexus/gui/i18n.py`: localized labels.
- Focused evidence/review tests and durable task records.

## Implementation plan

1. Add RED tests for readiness states and visible axis provenance.
2. Project existing NMR assignment status into evidence.
3. Present readiness and axis status in the shared Results review summary.
4. Run focused/lifecycle/verifier/boundary checks and create an allowlist
   checkpoint.

## Acceptance criteria

- [x] Solid-C evidence exposes `assignment_readiness` with `class`, `allowed`,
      and a stable reason for supported, limited, and missing assignment.
- [x] Results review text shows readiness and source/calibration state from
      existing axis evidence.
- [x] Existing NMR evidence, figure, solid-C lifecycle, and GUI tests stay
      green; the full four-partition lifecycle command remains a documented
      tool-timeout limitation.
- [x] No scientific value, assignment, axis conversion, or promotion rule is
      invented or changed.
- [x] Task verifier, boundary audit, and diff checks are recorded below; the
      explicit allowlist checkpoint is `fddb8c5`.

## Verification

```powershell
$env:POLYNEXUS_TEST_ROOT='C:\PolyNexus-test-runs'; $env:POLYNEXUS_TEST_RETENTION='review'; python -m pytest -p no:cacheprovider -q tests/test_analysis_evidence.py -k nmr tests/test_results_review_service.py -k nmr
python -m pytest -p no:cacheprovider -q tests/test_nmr_engine.py tests/test_nmr_figure_provider.py tests/test_nmr_figure_document.py tests/test_nmr_lifecycle_closure.py
python scripts/boundary_audit.py --root D:\PolyNexus --json
python scripts/verify.py --task docs/agent/tasks/2026-07-30-nmr-solid-c-readiness.md --changed --types
git diff --check
```

## Known boundary

The evidence remains assignment-limited when the source lacks phase truth and
axis calibration. Human review is still required for assignment correctness,
vendor semantics, and final release authorization.

## Explicit changed-file allowlist

- `polynexus/core/analysis_evidence_nmr.py`
- `polynexus/gui/results_review_service.py`
- `polynexus/gui/i18n.py`
- `tests/test_analysis_evidence.py`
- `tests/test_results_review_service.py`
- this task's design, plan, acceptance, and memory entry

## Verification log

- Focused evidence: `13 passed, 129 deselected`, exit 0.
- Focused Results review NMR: `1 passed, 28 deselected`, exit 0.
- Changed-file Ruff: `All checks passed`, exit 0.
- NMR figure provider: `6 passed`, exit 0.
- NMR figure document: `5 passed`, exit 0.
- Solid-C lifecycle: `1 passed, 3 deselected in 148.24s`, exit 0.
- NMR engine: `19 passed in 112.93s`, exit 0.
- Full lifecycle command: tool-level exit `124`; no pytest summary. It is not
  recorded as a full-suite pass. The solid-C shard above is the authoritative
  lifecycle gate for this task.
- Task verifier: exit 0; quality `292`, preprocessing `106`; Ruff, compile,
  memory/task, whitespace, and boundary checks passed.
- `git diff --check`: exit 0. Explicit checkpoint: `fddb8c5`.

## Checkpoint

The implementation and evidence slice was checkpointed at `fddb8c5`. The
remaining assignment and axis limitations are intentional scientific review
boundaries, not incomplete parser work.
