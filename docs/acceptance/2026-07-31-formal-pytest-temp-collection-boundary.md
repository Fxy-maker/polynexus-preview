# Formal pytest temporary-directory collection boundary

Date: 2026-07-31
Task: `docs/agent/tasks/2026-07-31-formal-pytest-temp-collection-boundary.md`
Status: collection boundary verified; single-process release wrapper timed out

## Evidence

- Baseline full verifier result before this change:
  `1 failed, 3224 passed, 18 skipped, 12 warnings in 1983.04s`.
  The only failure was the untracked temporary test
  `tests/_tmp_phase3/test_visual_audit_capture.py::test_capture_real_result_gui_routes`,
  which searched for the obsolete repository-root output path
  `PolyNexusPolyNexus.pytest_tmp_release_real_dsc`.
- Baseline collection included `_tmp_phase3`; `3251 tests collected`.
- `pytest.ini` now declares `norecursedirs = _tmp*`.
- Fresh collection after the change returned exit code `0`, excluded
  `_tmp_phase3`, and reported `3275 tests collected in 3.50s`.

## Acceptance classification

- [x] Temporary diagnostic directory is excluded from formal collection.
- [x] Canonical tests remain in the formal collection.
- [x] User-owned temporary diagnostic file was not edited or deleted.
- [ ] Full verifier has a fresh complete passing summary and wrapper exit code.
- [x] Canonical tests were rerun in four explicit slices with complete
  summaries: `3233 passed, 18 skipped, 12 warnings`, all slice exit codes `0`.
- [x] Boundary audit and task-scoped verification pass.
- [x] Scoped explicit allowlist checkpoint is complete; shared concurrent
  `active-work.md` changes remain outside this checkpoint.

## Limitations

The single-process `python scripts/verify.py --changed --types --full --boundary`
attempt reached the tool's 30-minute limit with exit `124` and no pytest
summary; it is classified as a tool-level timeout, not a release pass or test
failure. The four canonical pytest slices each returned a complete summary and
exit `0`, but they do not change the wrapper classification. Scientific IR
mapping, NMR solid-C, Joint conflict, restarted-GUI, and final publication
approval gates remain separate from this test-infrastructure fix.

## Fresh verification rerun

On 2026-07-31 the full/boundary wrapper was rerun with an external D: test
root. It reached the 2104-second tool limit with no pytest summary and exit
`124`; this is recorded as incomplete evidence. The spawned verifier/pytest
processes were reaped afterward.

The fresh collection check returned exit `0` with `3275 tests collected in
3.50s`. The task-scoped verifier returned exit `0`, including quality `297
passed` and preprocessing `106 passed`; the boundary audit and `git diff
--check` also returned exit `0`.

Storage report and clean remained non-destructive dry-runs: `64` artifacts,
`22,285` eligible bytes, no cleanup failures, and no directories removed
because `--apply` was not supplied. No `test_storage.py --apply` was run.
