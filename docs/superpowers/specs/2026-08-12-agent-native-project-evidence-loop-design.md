# Agent-Native Project Evidence Loop Design

## Decision

PolyNexus will evolve from a GUI-led multi-technique application into a
deterministic scientific evidence engine for a Codex-managed research project.
The first real target is one PA6 paper project. It must turn a folder containing
DSC, FTIR, SAXS, and WAXS source data into a versioned
`ResearchEvidencePackage` that ARS can use for Results and Discussion work.

The project folder is the source of research context. Codex may start from a
user/ARS conversation, raw data, an existing manuscript, or any combination;
there is no required linear workflow.

## Goals And Non-Goals

Goals:

- Codex can inspect and organize a paper project without manual GUI sample or
  batch entry.
- AI interpretation of files remains separate from deterministic numeric and
  scientific analysis.
- ARS receives traceable figures, tables, result scope, and limitations.
- The project schema supports multiple formulations, preparation batches,
  treatment conditions, replicates, and mixed instrument files.
- Existing canonical DSC conversion and technique engines remain the first
  provider implementations.

Non-goals:

- A universal vendor-file recognizer or all technique converters in one task.
- Required human metadata entry before single-technique analysis.
- AI-created numeric series, hidden scientific parameters, or automatic
  scientific conclusions.
- Replacing/deleting the GUI, sample database, batch database, or Joint Hub.
- Modifying real project source files or storing them in this repository.

## System Shape

```text
Project folder: raw data, notes, manuscript, optional research brief
  -> Codex: inspect, classify, request and orchestrate work
  -> PolyNexus: canonical conversion, analysis, QC and figures
  -> project-local evidence workspace: runs, figures, tables, evidence
  -> ARS: draft Results/Discussion and request evidence gaps
  -> Codex: create the next analysis request when needed
```

Codex owns project understanding. PolyNexus owns validated numeric conversion,
scientific computation, plotting, provenance, and quality boundaries. ARS owns
manuscript organization but writes only within supplied result scopes.

## Project-Local Workspace

PolyNexus may create and update only the derived directory below a selected
paper-project root:

```text
PA6-paper/
  raw/                         # user data; never changed
  notes/                       # optional laboratory context
  manuscript/                  # optional draft/context
  .polynexus/
    project.json               # agent-maintained research graph
    inventory/                 # artifact identities and inspection output
    requests/                  # immutable analysis-request records
    canonical/                 # validated templates/conversion records
    runs/                      # immutable deterministic run manifests
    figures/                   # figure assets, data and recipes
    evidence/                  # versioned ResearchEvidencePackages
```

`project.json` is a machine-maintained index, never a required user form. Raw
files remain in place and are referenced by resolved local path and SHA-256.

## Research Graph

The index must not flatten research context into `sample -> batch -> file`:

```text
Study
  -> Formulation (material identity/composition)
    -> PreparationBatch (one preparation instance)
      -> Condition (thermal/mechanical/environmental treatment)
        -> Measurement (acquisition or logical acquisition segment)
          -> Artifact (raw, calibration, blank, log, attachment)
          -> CanonicalExperiment -> AnalysisRun -> EvidenceItem
```

- Studies can contain controls, blends, and multiple formulations.
- A formulation can have several batches; a batch can have several conditions.
- One condition can have multiple techniques and replicates. The actual pieces
  measured by DSC, WAXS, and SAXS need not be the same specimen.
- One artifact can yield multiple logical measurements. The PA6 multi-program
  DSC export is the first case: six isothermal-hold segments.
- One measurement can reference raw, background, calibration, and log files.
- Evidence is a result plus permitted interpretation scope and limits, not a
  manuscript conclusion.

Missing formulation/batch/condition links do not stop independent technique
analysis. They are needed only for a cross-technique assertion or comparison.

## Facts, Inferences, And Discrepancies

The first version has no user-facing probability score. Each property/link has
one explicit status with source references:

| Status | Meaning | Effect |
| --- | --- | --- |
| `verified_from_raw` | Instrument content, method program, or measured column directly establishes it. | Authoritative value. |
| `verified_from_record` | A linked instrument log or laboratory record explicitly establishes it. | Used when raw data cannot express it. |
| `inferred` | Codex inferred it from names, structure, nearby metadata, or manuscript context. | May organize and trigger single-technique work; cannot alone support a strong cross-technique claim. |
| `discrepancy` | A lower-priority label disagrees with authority. | Authority remains in use; mismatch is retained for audit. |
| `unknown` | No source establishes it. | Does not block independent analysis. |

Authority order is fixed: raw instrument facts, then same-run logs/lab records,
then directories, file names, and agent inference. A file named `WAXS_180C`
whose raw method says 185 C is classified as 185 C, with a naming discrepancy.
When missing context becomes necessary for integration, Codex asks the smallest
specific question and records the answer; it does not block unrelated work.

## Analysis Requests And Operations

`AnalysisRequest` is the only active input to PolyNexus. A user, Codex, or ARS
may create it; research brief, manuscript context, and data scope are optional.

```json
{
  "request_id": "pa6-kinetics-001",
  "question": "Compare PA6 isothermal crystallization kinetics from 180 to 185 C.",
  "purpose": "results_support",
  "requested_outputs": ["avrami_parameter_table", "temperature_comparison_figure"],
  "data_scope": ["raw/DSC-isothermal"],
  "context_sources": ["notes/experiment.md", "manuscript/draft.md"]
}
```

| Operation | Responsibility | Mutates |
| --- | --- | --- |
| `inspect` | Inventory artifacts and direct facts/recognized techniques. | `inventory/` only |
| `plan` | Resolve a request into provider-compatible, non-executing work. | `requests/` only |
| `run` | Invoke registered converters/providers and materialize run/evidence outputs. | Derived workspace only |
| `package` | Select compatible runs and create immutable evidence-package version. | `evidence/` only |

Codex resolves natural language before `run`. PolyNexus receives registered
template/provider IDs, artifact identities, output requirements, and
policy-approved parameters. The existing agent-workflow service remains the
provider/replay contract; the project service composes it.

## Replay And Packaging

Each immutable run identity includes:

```text
raw artifact hash(es) + canonical template hash(es) + provider/recipe version + approved parameters
```

Replay verifies source identity before provider invocation. Changed inputs,
templates, algorithms, or parameters create a new run and never overwrite an
existing figure/table. Expected data errors are `blocked` or `not_analyzable`;
quality-limited usable results are `review_required` and preserve restrictions.

`package` emits a versioned snapshot such as
`.polynexus/evidence/pa6-crystallization-v001/`:

```text
manifest.json             package identity, scope and status
evidence.json             observed facts and bounded result items
relations.json            cross-technique links used by this package
tables/                    CSV/XLSX/JSON source tables
figures/                   assets, plot data, recipes and captions
limitations.json          quality, missing-context and scope limits
writing-input.md          compact human/ARS entry point
```

Each item declares technique, claim scope, source runs, raw hashes, figures,
tables, status, limitations, and three distinct layers: observed results,
supported interpretation, and disallowed conclusions. ARS reads the package,
not arbitrary raw data. Later package versions coexist with older ones.

## PA6 First Slice

The first vertical slice succeeds when a PA6 project progresses from mixed
source folders to a versioned package with DSC, FTIR, SAXS, and WAXS
single-technique outputs, figures, citeable tables, provenance, scope, and
limitations. The existing PA6 DSC 180-185 C multi-program conversion is the
initial acceptance path. FTIR/SAXS/WAXS enter only through registered canonical
templates/adapters meeting the same validation/replay boundary. Unsupported
formats are blockers, never ad-hoc agent scripts.

Delivery is phased: the project contract and DSC end-to-end path precede each
new technique adapter. Until a technique passes its own boundary, absence is a
package limitation, not fabricated completeness.

## Compatibility, Failure, And Verification

Existing `AnalysisResult`, canonical templates, figure provenance,
agent-workflow recipes, GUI routes, SQLite records, and Joint Hub remain.
The GUI becomes a review/manual-correction/legacy-compatibility surface, not a
prerequisite. No database migration is needed initially.

Missing converters, unreadable files, and failed validation are actionable
records and do not stop unrelated work. AI can suggest mappings but cannot
submit unvalidated values. The implementation plan will add focused synthetic
tests for isolation, identity, fact priority, request planning, replay,
package immutability, and ARS-facing limitations, plus an external read-only
PA6 smoke replay.

## Review Boundary

After review, this design authorizes planning and implementation of the project
service, index, request contract, and DSC-backed package slice. Scientific
algorithms, FTIR/SAXS/WAXS canonical schemas, and manuscript conclusions remain
separate review boundaries.
