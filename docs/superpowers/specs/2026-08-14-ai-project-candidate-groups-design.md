# AI Project Candidate Groups Design

## Decision

Project discovery produces `CandidateExperimentGroup` values from the
technique and filename shape only. For files such as `PA6-JW-30.csv`, the group
is `PA6 JW temperature series`, and its numeric condition is 30 C. For
`PA6-250-for 1min.csv`, the group is `PA6 250 C time series`, and its condition
is 1 min. These are filename-derived candidates, not verified experiment facts.

## Selection

- Explicit `data_scope` takes precedence and runs exactly that scope.
- With one candidate, the AI entrypoint selects it.
- With several candidates, it searches the normalized question for a group
  label or filename prefix. A `time` or `temperature` request also constrains
  selection to that condition kind. One match is selected.
- Otherwise it returns `computation=blocked`, candidate groups, and one
  `select_candidate_group` message. No provider runs are started.

## Boundary

The next Codex/ARS layer decides group selection from the paper conversation;
PolyNexus only exposes stable options and executes the selected files. Group
labels, full filename prefixes, and condition ranges remain
`inferred_from_filename` in output. Explicit paths are not de-duplicated.
