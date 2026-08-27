# Mixed-Technology Project Run

## Goal

Make one explicit `analyze-project` request over multiple techniques produce a
single replayable project workflow run while retaining one deterministic step
per technique or same-technique series.

## Design

`ProjectWorkflowService.analyze_project()` submits one request containing the
selected artifact paths. `plan()` keeps one plan step per technique but no
longer blocks merely because more than one technique is present. `run()` routes
multi-technique plans to a registered composite adapter.

The composite adapter delegates proposal and validation to the existing DSC,
single-input, and series adapters. It merges their immutable artifacts and
steps into `project.technique.composite.v1`; series `artifact_index` values are
rebased to the merged artifact tuple. `AgentWorkflowService.run_recipe()` then
executes every step through the existing shared `ComputeRunService` boundary.

The resulting `ProjectWorkflowRun` remains one request-level envelope. Its
`AnalysisRun.steps` and evidence items preserve technique-level provenance,
figures, limitations, and review status. A component failure fails the
composite run; a component review status keeps the composite `review_required`.

## Boundaries

- No provider algorithm or scientific eligibility rule changes.
- No automatic sample/batch identity inference.
- Mixed DSC inputs with more than one DSC artifact remain explicitly blocked by
  the existing DSC source-count rule.
- Existing single-technique and historical recipe readers remain compatible.

## Acceptance

- Mixed IR+WAXS input is planned and executed as one `ProjectWorkflowRun`.
- Provider runners are called once per component step and all steps retain
  canonical template provenance.
- The package contains one request run and a cross-technique relation.
- Single-technique and same-technique series behavior remains unchanged.
- Stale/hash/recipe validation still blocks before provider execution.
