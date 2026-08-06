# SAXS strain feature tracking closure acceptance

Date: 2026-08-06
Task: `docs/agent/tasks/2026-08-06-saxs-strain-feature-tracking-closure.md`
Status: focused and structured automated acceptance passed

## Behavior

- The first credible total-profile lamellar peak seeds the series tracker.
  Adjacent q movement is capped at 25%, and loss is irreversible within a run.
- Unseeded, failed, lost, and locked-out frames do not publish authoritative
  L/lc/la/phi_c or feature-local orientation. Core exceptions retain an
  explicit failed frame result so frame and GUI row alignment is preserved.
- Orientation and detector-coordinate meridional/equatorial diagnostics use
  the exact accepted total-profile q.
- New strain output, figures, stability reports, history, and review summaries
  use `invariant_Q*`. Legacy `Q_star*` is accepted only at compatibility reads.
- Detector previews preserve raw log evidence and use finite positive-source
  percentile display values without allowing floor sentinels to set the scale.

## Evidence

- `python -m pytest -p no:cacheprovider -q` over the focused core/GUI/tracking/
  table matrix: `131 passed in 14.43s`.
- Expanded SAXS figure/orientation matrix: `245 passed, 2 skipped, 4 warnings
  in 40.95s`; warnings are existing Arial CJK glyph warnings.
- Analysis evidence/history/stability matrix: `307 passed in 11.05s`.
- Follow-up history/result-table/stability matrix after final review fixes:
  `246 passed in 0.71s`.
- Read-only `Desktop/edf/8` replay: `1 passed in 9.11s`; source mtimes were
  asserted unchanged.
- `python scripts/verify.py --task
  docs/agent/tasks/2026-08-06-saxs-strain-feature-tracking-closure.md
  --changed --types`: exit `0`; task/memory, Ruff, compile, quality `297`,
  preprocessing `107`, and whitespace checks passed.
- The cumulative diff was reviewed and checkpointed locally with an explicit
  task-file allowlist; no push, merge, deployment, or source-data mutation was
  performed.

## Scientific boundary

This accepts the software data flow, fail-closed behavior, and regression
evidence. It does not validate absolute intensity/contrast calibration, infer
a tensile axis, authorize a final Herman interpretation, or promote figures
for publication. Human scientific review remains required before merge.
