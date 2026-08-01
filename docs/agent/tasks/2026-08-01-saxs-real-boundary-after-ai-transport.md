---
task_id: 2026-08-01-saxs-real-boundary-after-ai-transport
kind: scientific-verification
status: completed
date: 2026-08-01
title: Recheck real SAXS boundaries after AI context transport
---

# Current-head real SAXS boundary recheck

## Goal

Refresh read-only real-fixture evidence after the SAXS AI parent-review
transport checkpoint, covering method evidence across Parameter/Figure/Export,
the PAD8 2D scientific-acceptance boundary, and the Static/Temperature/Strain
shared lifecycle.

## Non-goals

- no production code, algorithm, threshold, quality level, physical gate,
  rescue, AI candidate, Figure role, Manifest, Export, or publication change;
- no detector calibration, beam-center inference, mask-validity decision,
  orientation assignment, interpolation, frame repair, or reviewer decision;
- no edits to real fixtures, generated outputs, D: test directories, memory,
  scratch, or parallel worktree files;
- no `scripts/test_storage.py --apply`.

## Affected boundaries

- `tests/test_saxs_real_method_evidence_surfaces.py`: existing real method
  evidence replay and Parameter/Figure/Export projection;
- `tests/test_saxs_real_2d_scientific_acceptance.py`: existing PAD8 audit and
  publication fail-closed boundary;
- `tests/test_real_published_run_walkthrough.py`: existing real SAXS lifecycle
  selector;
- this task's spec, plan, acceptance record, and evidence only.

## Acceptance criteria

- [x] Real Static, Temperature, and Strain fixtures replay with strict-JSON
      method evidence preserved through Parameter, Figure/Manifest, and Export.
- [x] PAD8 returns the existing `diagnostic_only` scientific-acceptance state
      with unchanged publication flags and no inferred geometry/mask/orientation
      approval.
- [x] The real SAXS lifecycle selector produces a complete pytest summary and
      exit code `0`.
- [x] Task-scoped verification, storage report/clean dry-run, and diff check
      produce complete evidence; a timeout or no-summary run is incomplete.
- [x] A documentation-only allowlist checkpoint records exact outcomes and
      keeps human scientific and release approval open.

## Implementation plan

1. [ ] Run the real method-evidence surface test with an external writable
   basetemp and require a complete pytest summary.
2. [ ] Run the PAD8 scientific-acceptance boundary with a separate external
   basetemp and require a complete pytest summary.
3. [ ] Run the SAXS Static/Temperature/Strain lifecycle selector and classify
   only its actual exit code and final summary.
4. [ ] Run the task verifier, storage report/dry-run clean, and `git diff
   --check`; record any tool or disk limitation without relabeling it.
5. [x] Review the disjoint diff and create one checkpoint containing only the
   four documentation files in this task.

## Evidence

- Real method-evidence replay: `3 passed in 94.63s`, exit code `0`. Static,
  Temperature, and Strain each preserved strict-JSON method evidence through
  final parameters, Figure/Manifest provenance, and Export quality evidence.
- PAD8 scientific-acceptance boundary: `4 passed in 34.74s`, exit code `0`.
  The existing contract retained `diagnostic_only`, conservative publication
  flags, and no inferred geometry, mask, beam-center, or orientation approval.
- Real SAXS lifecycle selector: `3 passed, 12 deselected in 94.99s`, exit code
  `0`, covering Static, Temperature, and Strain.

- Task-scoped structured verifier exited `0`: quality `297 passed`,
  preprocessing `106 passed`, task/memory, Ruff, compile, type-baseline, and
  whitespace checks passed.
- Storage report and dry-run clean both exited `0`: `145` artifacts,
  `34,459,621,656` total bytes, `15,743,185,346` eligible bytes,
  `failures=[]`, and `removed=0`. No `test_storage.py --apply` was executed.
- `git diff --check` exited `0`. The documentation-only checkpoint is the
  remaining finalization step. These automated results do not close human
  scientific or release approval.

## Verification

```powershell
python -m pytest -q tests/test_saxs_real_method_evidence_surfaces.py -vv -o addopts= --basetemp=D:\PolyNexus-test-runs\saxs-real-boundary-methods-20260801
python -m pytest -q tests/test_saxs_real_2d_scientific_acceptance.py -vv -o addopts= --basetemp=D:\PolyNexus-test-runs\saxs-real-boundary-pad8-20260801
python -m pytest -q tests/test_real_published_run_walkthrough.py -k saxs -vv -o addopts= --basetemp=D:\PolyNexus-test-runs\saxs-real-boundary-lifecycle-20260801
python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-real-boundary-after-ai-transport.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Each pytest command counts only with a complete summary and exit code `0`.
Storage commands are non-destructive dry-runs. No storage apply is authorized
by this task.

## Scientific boundary

Passing automation demonstrates software transport and conservative gate
behavior only. It does not establish detector geometry calibration, beam-center
meaning, mask validity, orientation interpretation, temperature/strain
scientific meaning, or publication/release approval. Those remain explicit
human and instrument-aware gates.

## Explicit changed-file allowlist

- `docs/superpowers/specs/2026-08-01-saxs-real-boundary-after-ai-transport-design.md`
- `docs/superpowers/plans/2026-08-01-saxs-real-boundary-after-ai-transport.md`
- `docs/agent/tasks/2026-08-01-saxs-real-boundary-after-ai-transport.md`
- `docs/acceptance/2026-08-01-saxs-real-boundary-after-ai-transport.md`

Parallel memory, source, test, real-data, generated-output, scratch, and
test-storage changes remain outside this checkpoint.
