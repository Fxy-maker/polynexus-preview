# SAXS GUI Mask Editor Confirmed Rerun Acceptance

## Scope

This slice adds an explicit detector-mask review action for one static 2D SAXS
result. The editor works on detached image/mask state, validates a confirmed
candidate through the existing mask-edit contract, and starts one normal static
rerun. Existing detector-quality, quality, physical, and publication gates
remain authoritative.

Temperature, strain, directory, 1D, AI, automatic rescue, interpolation,
morphology, new thresholds, and publication promotion are not included.

## Evidence

- TDD RED was observed as pytest collection failure because the new GUI service
  boundary did not exist; the implementation then reached GREEN.
- Focused GREEN: `python -m pytest -q tests/test_saxs_gui_mask_editor_confirmed_rerun.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-gui-mask-editor-green-final`
  -> `5 passed in 0.59s`, exit code `0`.
- Structured verification:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md --changed --types`
  -> task/memory checks, Ruff, compile, type baseline, quality `292`,
  preprocessing `106`, and whitespace passed; exit code `0`.
- Exact SAXS matrix:
  `python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Sort-Object FullName | Select-Object -ExpandProperty FullName) -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-gui-mask-editor-saxs-matrix-final`
  -> `647 passed, 6 warnings in 552.67s (0:09:12)`, exit code `0`.
- Storage report/dry-run:
  `report --json` found `57` artifacts, total `15,802,080,308` bytes,
  `eligible_bytes=0`, and no emergency pressure. `clean --older-than-hours
  24` remained dry-run with `removed=0`; no apply, deletion, or migration was
  performed.
- `git diff --check` passed.

## Release Boundaries

This acceptance note records automated evidence for the task only. It does not
close full/boundary release verification, restarted-GUI review, or human
scientific review.
