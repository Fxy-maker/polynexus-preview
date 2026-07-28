---
task_id: 2026-07-30-results-summary-long-token-layout
kind: gui-regression
status: completed
---

# Results Summary long-token layout

## Goal

Keep long diagnostic evidence readable in the Results Summary and Result Review
panels without changing the source text or its scientific meaning.

## Non-goals

- Do not change analysis engines, thresholds, evidence severity, or publication
  roles.
- Do not shorten, normalize, or otherwise rewrite diagnostic evidence strings.
- Do not remove existing native route, scientific, or release-review limitations.
- Do not delete or migrate test data.

## Affected boundaries

- `polynexus/gui/main_window_results_mixin.py`: display-only QLabel subclass for
  evidence labels.
- `tests/test_saxs_results_evidence_layout.py`: focused Qt regression.
- Existing Results Workbench native route harness and external D: captures.

## Implementation plan

1. Add a failing Qt regression proving that a delimiter-free diagnostic token
   cannot require a multi-screen minimum width.
2. Introduce a display-only wrapped evidence label that keeps `.text()` exact,
   then apply it to Results Summary and Result Review evidence labels.
3. Run focused GUI regressions, the Results/Persistence summary slice, the
   native 17-route matrix, and the structured verifier before checkpointing.

## Verification

```powershell
python -m pytest -q tests/test_saxs_results_evidence_layout.py -vv
python -m pytest -q tests/test_main_window_persistence.py -k "summary or review or finished" -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-30-results-summary-long-token-layout.md --changed --types
git diff --check
```

The native route command uses the bundled Python 3.14 runtime with
`QT_QPA_PLATFORM=windows` and a D: basetemp/capture directory as recorded in
the acceptance note.

## Acceptance criteria

- [x] A delimiter-free diagnostic token can wrap within a 640-pixel label.
- [x] The public `QLabel.text()` value remains exactly the source string.
- [x] Existing Results Summary, Review service, and persistence regressions
  remain green.
- [x] The native 17-route matrix remains green and its warnings are recorded.
- [x] Human visual/scientific/release review remains explicitly open.

## Verification evidence

- TDD RED: the new regression failed with `minimumSizeHint().width() == 14664`.
- Focused layout/semantic matrix: `12 passed in 5.91s`.
- Review service matrix: `28 passed in 0.51s`.
- Results/Persistence summary matrix: `52 passed in 73.38s`.
- Structured verifier: exit code `0`; task/memory checks, Ruff, compile, type
  baseline, quality gate (`287 passed`), preprocessing gate (`106 passed`), and
  whitespace checks passed.
- Native Windows Qt route matrix: `17 passed, 15 warnings in 307.72s`, exit
  code `0`. It produced 68 captures under
  `D:\PolyNexus_native_all_routes_long_token_wrap_20260730` and exercised the
  no-Origin PackageExporter route.
- The initial combined Qt matrix hit the 180-second command timeout without a
  pytest summary; this is recorded as a tool timeout and was replaced by the
  collected split results above.

## Known limitations

The native matrix proves route construction and fallback export only. Synthetic
IR mapping vendor/ROI semantics, NMR solid-C assignment correctness, Joint
conflict interpretation, SAXS diagnostic/validation meaning, and final release
approval remain human review gates.

## Explicit changed-file allowlist

- `polynexus/gui/main_window_results_mixin.py`
- `tests/test_saxs_results_evidence_layout.py`
- `docs/superpowers/plans/2026-07-30-results-summary-long-token-layout.md`
- `docs/agent/tasks/2026-07-30-results-summary-long-token-layout.md`
- `docs/acceptance/2026-07-30-results-summary-long-token-layout.md`
- `docs/agent/memory/active-work.md`
