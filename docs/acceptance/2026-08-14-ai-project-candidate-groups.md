# AI Project Candidate Groups Acceptance

Date: 2026-08-14

The AI-native project entrypoint now derives conservative candidate experiment
groups before an unscoped mixed-directory analysis. Candidate labels and
conditions are explicitly `inferred_from_filename`; they do not establish
sample, batch, formulation, or scientific comparability.

## Behavior

- `PA6-JW-30.csv`, `PA6-JW-40.csv` -> `PA6 JW temperature series`.
- `PA6-SW-30.csv` -> `PA6 SW temperature series`.
- `PA6-250-for 1min.csv`, `PA6-250-for 2min.csv` -> `PA6 250 C time series`.
- A question containing one distinctive label such as `JW` selects that group.
- A single candidate is explicitly recorded as the selected scope.
- Generic condition units such as `C` do not select an unrelated candidate.
- `time series` only considers time candidates; it cannot select a temperature
  series based on another label token.
- An ambiguous question returns `candidate_group_selection_required` and a
  concise candidate list without executing a provider.
- Explicit `--paths` remains authoritative, including same-stem companion
  files listed deliberately by the caller.

## Real PA6 Read-Only Discovery

External PA6 FTIR raw data through the existing read-only junction produced:

- PA6 JW temperature series: 22 CSV files.
- PA6 SW temperature series: 23 CSV files.
- PA6 250 C time series: 3 CSV files.

The generic question `Analyze PA6 FTIR data` returned the candidate list and
did not start a whole-directory analysis. A small real JW provider smoke was
stopped after the local IR figure provider ran longer than the bounded check;
it is not claimed as a completed replay. No raw files were modified.

## Verification

- Candidate-group focused tests: `9 passed`.
- Project workflow regression matrix: `47 passed`.
- Structured verifier: passed, including Ruff, compilation, quality gate
  (`303 passed`), preprocessing gate (`157 passed`), and whitespace check.
