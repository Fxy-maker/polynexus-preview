# PolyNexus Workbench Surface Convergence Design

## Decision

PolyNexus remains a full polymer research workbench. It is not an AI-only
evidence backend and it is not a GUI-only desktop application. Codex/AI and a
researcher must operate the same `Project`, `Run`, `Chart`, `Evidence package`,
and `Export` objects through public contracts.

The product is simplified by converging entry points and hiding low-frequency
complexity. It is not simplified by removing the ability to inspect data,
adjust an analysis, compare alternatives, edit a figure, or export a result.

## User Surfaces

### Project Workbench: default

The default entry starts with a project directory and a research question. It
uses `ProjectWorkflowService.analyze_project()` and presents discovered files,
candidate experiment groups, the execution plan, three-layer status, generated
runs, figures/tables, evidence packages, and required human review.

Both a researcher and Codex can start here. The GUI is a public-object client;
it must not reimplement discovery, grouping, canonical conversion, or analysis
rules in event handlers.

### Quick Analysis: direct and flexible

Quick Analysis keeps direct file and temporary-series analysis for exploratory
work. It uses the same analysis/run/chart contracts as the project route. A
quick run can later be attached to a project; it is not a private GUI result.

### Advanced Tools: explicit, contextual, and optional

Low-frequency or specialist controls remain available without occupying the
main navigation. They are shown only when they have a current run, selected
project data, or a deliberate expert request. Their operations must still write
the shared run/chart/evidence/export objects.

## Target Navigation

```text
Project Workbench
  discover -> choose group if needed -> analyze -> review -> evidence -> export

Quick Analysis
  open file/series -> analyze -> inspect -> attach to project when useful

Results and Evidence
  runs -> metrics -> review actions -> evidence package -> writing handoff

Charts and Export
  project/run charts -> edit -> export standard assets or optional Origin

Advanced Tools
  analysis configuration, candidate-plan evaluation, specialist diagnostics,
  experimental adapters, legacy compatibility
```

`Results and Evidence` and `Charts and Export` are views over shared objects,
not independent analysis workflows. A project-workbench implementation may
initially link to existing views rather than recreate them.

## Module Disposition

| Existing capability | Target surface | Decision now | Removal precondition |
| --- | --- | --- | --- |
| DSC, IR, WAXS, SAXS engines | Project + Quick | Retain as deterministic producers | None |
| `analyze-project`, canonical conversion, evidence/ARS handoff | Project | Retain and make GUI-accessible first | None |
| Single-file analysis | Quick | Retain; later allow project attachment | Shared run contract is proven |
| Batch processing | Project + Quick | Merge into project plan or temporary series; no deletion yet | Project route covers current batch use cases |
| Sample Hub / SampleDB | Project metadata | Move from mandatory entry to contextual metadata/history | Project model supports ordinary sample/batch edits |
| History | Results and Evidence | Reframe as run/evidence history; retain existing persistence | Project and quick runs appear together |
| Joint Analysis | Results and Evidence | Reframe as cross-technique evidence relation and conflict view | Project evidence relation view covers selection and review |
| AI tuning | Advanced Tools | Rename in product language to candidate analysis-plan evaluation | Candidate proposals and confirmation path are accessible from a run |
| RAG / vector retrieval | Candidate optional feature | Freeze expansion; do not remove in this task | Adviser/candidate-plan replacement is proven and its dependency graph is tested |
| Polymer reference tables | Core deterministic support | Retain; they are not vector RAG | None |
| Chart editor | Charts and Export | Retain common scientific editing and standard export | None |
| Origin integration | Advanced optional export | Keep optional; defer compatibility cleanup | Standard export satisfies active workflows |
| NMR | Advanced experimental adapter | Do not expose as a default project promise | A validated NMR project adapter and review policy exist |
| Residual/convergence/specialist diagnostics | Advanced contextual tools | Retain behind result/configuration context | Replacement diagnostic summary exists where an entry is removed |

## Migration Sequence

1. **Project Workbench shell**: add a small GUI entry that accepts a directory
   and question, invokes the existing public project-workflow service, and
   displays its status and selection-required outcome. It does not duplicate
   old result, chart, or export views.
2. **Shared-object handoff**: link project-generated runs, evidence packages,
   and figure assets to existing Results, evidence dialog, gallery, and export
   consumers.
3. **Surface convergence**: re-label and route Batch, Sample Hub, History,
   Joint, and AI tuning through the appropriate Project, Quick, Results, or
   Advanced surfaces while retaining legacy entry points as compatibility paths.
4. **Usage-backed retirement**: after the replacement route covers real PA6
   project work and direct expert work, remove duplicate entries one at a time.
   Each deletion requires a separate task card, dependency audit, regression
   test, and human review.
5. **Optional dependency reduction**: only after step 3 establishes an adviser
   replacement, make RAG/vector storage opt-in or remove it. Do not remove the
   deterministic polymer reference knowledge with it.

## First Runtime Task

The first implementation task is a **minimal Project Workbench entry**. It
will consume the existing `ProjectWorkflowService.analyze_project()` public
result and expose selection-required, completed, and review-required states.
It will not reorganize the complete navigation, retire old pages, or change a
project/run/evidence schema.

Its affected shared objects are `Project`, `Run`, and `Evidence package`; the
producer is the existing project workflow. Required proof will include the
workflow service/CLI contract and a focused GUI view-model or widget test.

## Boundaries

- AI can choose a question, request analysis, and summarize public result
  objects. It cannot bypass canonical conversion or promote diagnostics.
- The GUI can inspect and request operations through public DTOs. It cannot
  maintain a second analysis/provenance model.
- Cross-technique association remains explicit project evidence membership; no
  module may infer sample identity or scientific causality.
- Architecture review is required before runtime migration because it affects
  the product navigation and multiple entry points.

## Review Outcome Required

Before implementing the Project Workbench entry, a human reviewer must confirm
that Project Workbench is the default surface, Quick Analysis remains an
independent expert path, and RAG removal is deferred until the candidate-plan
workflow has a tested replacement.
