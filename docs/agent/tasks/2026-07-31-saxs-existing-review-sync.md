# SAXS Existing Review Evidence Synchronization

Status: completed with SAXS matrix timeout limitation

## Goal

When a SAXS Workbench scientific review is saved after a Figure run already
exists, update the review evidence in the existing manifest-linked Figure
documents without changing scientific or publication semantics.

## Non-goals

- no Figure rerun, interpolation, rescue, recalculation, or data mutation;
- no changes to physical thresholds, quality levels, publication roles, or AI
  candidate behavior;
- no changes to non-SAXS or legacy-recovery artifacts;
- no `test_storage.py --apply`, deletion, or migration of test directories;
- no inclusion of pre-existing parallel worktree files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_evidence.py`: manifest-linked document
  synchronization and fail-closed review projection;
- `polynexus/core/saxs.py`: engine entry point using current frame views;
- `polynexus/gui/main_window_results_mixin.py`: invoke sync after the existing
  Workbench persistence and in-memory update;
- focused SAXS Figure/Workbench regression tests and task artifacts.

## Acceptance criteria

- [x] An accepted source-matched `saxs.1d` review reaches every ready existing
   Figure document selected by the manifest.
- [x] Detector/orientation documents use the existing `saxs.2d` scope boundary.
- [x] Missing, cancelled, source-mismatched, scope-mismatched, malformed, or
   unavailable reviews remain disallowed and do not raise through the save
   route.
- [x] The manifest's entry paths, Figure IDs, roles, revisions, assets, data
   sources, and all non-review document fields remain unchanged.
- [x] Existing AI/rescue, quality, metric, detector, orientation, and acceptance
   audit evidence remains byte-equivalent outside the review subtree.
- [x] A later SAXS export still emits the same review evidence and the manifest
   remains a structural index only.
- [x] Tests and verification report exact real outcomes, including limitations.

## Implementation plan

1. Add RED tests for existing manifest-linked Figure documents, 1D/2D scope,
   fail-closed reviews, and the SAXS Workbench route.
2. Implement the core manifest-linked synchronization service with safe paths,
   detached evidence projection, and atomic document writes.
3. Add the SAXS engine entry point and invoke it after the existing Workbench
   result update without changing persistence failure semantics.
4. Run focused consumers, the structured verifier, the SAXS matrix, and storage
   report/dry-run; record exact outcomes before creating the allowlist checkpoint.

## TDD evidence

- RED command and failure: to be recorded after the focused regression is
  added.
- GREEN and regression commands: to be recorded in the acceptance note.

## Verification

- focused Figure/Workbench review matrix;
- exact SAXS matrix;
- `python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-existing-review-sync.md --changed --types`;
- storage `report` and dry-run `clean` only.

## Allowlist checkpoint

Explicit files for the atomic checkpoint:

- `polynexus/core/saxs_engine/figure_evidence.py`
- `polynexus/core/saxs.py`
- `polynexus/gui/main_window_results_mixin.py`
- `tests/test_saxs_figure_evidence_binding.py`
- `tests/test_scientific_review_workbench.py`
- `docs/superpowers/specs/2026-07-31-saxs-existing-review-sync-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-existing-review-sync.md`
- `docs/agent/tasks/2026-07-31-saxs-existing-review-sync.md`
- `docs/acceptance/2026-07-31-saxs-existing-review-sync.md`
- `docs/agent/memory/lessons/2026-07-31-saxs-existing-review-sync.md`

The final checkpoint must list only files changed for this task. Existing
changes in `docs/agent/memory/active-work.md`, `docs/agent/memory/current-state.md`,
`.superpowers/`, and untracked test/storage directories remain untouched.

## Evidence

- RED: the focused command failed during collection with the expected
  `ImportError` for the new core sync API.
- GREEN focused sync route: `5 passed, 51 deselected in 4.88s`.
- GREEN sync-only including the SAXSEngine entry point: `5 passed, 33
  deselected in 6.08s`.
- Figure/Export/Workbench consumer matrix: `69 passed in 14.03s`.
- Independent quality gate: quality `297 passed in 7.47s`, preprocessing `106
  passed in 2.03s`, compile and whitespace passed.
- `python scripts/verify.py --task ... --types`: exit `0`; task check, memory
  check, Pyright (`0 errors`), quality `297 passed`, preprocessing `106
  passed`, compile, and whitespace passed.
- `python scripts/verify.py --task ... --changed --types`: exit `1` before
  task quality checks because the pre-existing modified
  `polynexus/core/saxs_engine/io.py` has 10 Ruff baseline errors. That file,
  along with pre-existing `preprocess.py`, `saxs_quality_contracts.py`, and
  memory changes, is outside this task and was not fixed or checkpointed.
- SAXS matrix command `python -m pytest -q tests -k saxs`: tool timeout exit
  `124` after about `603.6` seconds with no pytest final summary; it is not
  claimed as passed.
- Storage `report --json` and dry-run `clean --older-than-hours 24` both exited
  `0`; report saw `54` artifacts, `4,317,125,742` bytes, `12` emergency-eligible
  entries totaling `7,873` bytes, and `0` removed. No `--apply` was run.

## Known limitations

- The SAXS full matrix needs a fresh bounded rerun after the external storage
  situation is resolved; the current feature evidence is focused and consumer
  scoped, not a full-matrix pass.
- Human scientific review and publication approval remain required. This sync
  only transports an existing review snapshot and cannot promote a Figure.
