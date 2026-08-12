# Project Technique Adapters V2 Design

## Decision

Extend the project-local evidence workflow with a registered single-input
adapter for IR, WAXS, and SAXS. The adapter delegates all numeric work to the
existing technique engines through `AgentWorkflowService`; it owns only recipe
selection, input identity, and evidence packaging.

## V2 Boundary

- Supported: one indexed input artifact per requested technique.
- Supported: deterministic `inspect -> plan -> run -> package` for `ir`, `waxs`,
  and `saxs`.
- Status remains `review_required` for these techniques until the existing
  provider evidence has passed its review gates.
- Multiple files for one technique remain an explicit blocker until a series
  adapter declares ordering, grouping, and replicate semantics.
- FTIR directories and vendor formats are not reinterpreted by this adapter;
  existing readers and engines remain authoritative.

## Data Flow

```text
project raw artifact -> project index -> registered project technique recipe
  -> existing engine -> validated AnalysisRun -> EvidenceItem -> ARS package
```

The adapter never copies raw data, writes beside raw data, or creates numeric
values. Source hashes are checked before provider execution and again during
package validation.

## Later Versions

- V3: explicit multi-file series adapters, replicate grouping, and stable table
  projections for each technique.
- V4: Codex/ARS cross-technique relation requests and writing-input sections
  that cite DSC/IR/SAXS/WAXS evidence without inventing sample identity.
- V5: retry/resume, stale-run repair, and user-approved context corrections.
