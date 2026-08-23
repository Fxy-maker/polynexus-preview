# Paper-brief interface design

## Decision

PolyNexus will provide an AI/CLI-facing paper-brief interface that converts an
ARS/Codex-created brief plus one immutable evidence package into a separate,
validated `ManuscriptPlan` artifact.  It is a writing-preparation boundary, not
a manuscript editor and not an alternate analysis route.

The interface is deliberately outside the GUI in V1.  ARS/Codex already owns
the conversation about the research question and paper story; PolyNexus owns
the deterministic evidence, figures, metrics, comparability limits, and
provenance used to prepare that story.

## Problem addressed

The elastic-body manuscript revision history showed that a full draft was
started before the following were stable: the paper's main comparison, which
technique answered which question, the small set of main figures, the boundary
between display-only changes and analysis changes, and the limitations on
comparability.  This produced repeated document-wide revisions.

The interface moves those decisions ahead of drafting.  It does not claim that
all scientific review disappears; it makes the first full draft start from a
single, frozen evidence and figure plan rather than an evolving set of files.

## Considered approaches

### 1. Put the brief inside the evidence package

Rejected.  An evidence package is an immutable snapshot of analysis facts.  A
single package may support multiple manuscripts, target journals, or narratives.
Embedding a mutable paper brief would either mutate the package or multiply
package versions without an analysis change.

### 2. Let ARS write directly from `ars-writing-input.json`

Insufficient.  The existing input correctly maps evidence, eligible metrics,
limitations, and review requirements, but it has no explicit paper scope,
figure budget, or selected comparison structure.  ARS can still over-select
figures or join unrelated evidence while drafting.

### 3. Add a separate plan pinned to a package snapshot

Selected.  A new `ManuscriptPlan` references one package by ID, version, and
hash.  It can be regenerated for a different paper without altering package
facts.  Its references are validated against the existing package contracts,
so ARS/Codex and a future GUI consume the same plan rather than creating their
own lists.

## Data model

### `PaperBrief` input

ARS/Codex supplies a JSON-safe request.  Free text is allowed only for the
research question and declared evidence roles; all object references are
validated.

```text
version: 1
title_hint: optional string
research_question: required non-empty string
comparison_scope:
  selected_techniques: optional technique names
  selected_evidence_ids: optional evidence IDs
  selected_metric_ids: optional metric IDs
figure_budget:
  main_max: non-negative integer, default 6
  supporting_max: non-negative integer, default 12
figure_intent: optional mapping of existing logical figure key -> main | supporting
technique_roles:
  <technique>: observed_result | structural_context | diagnostic_context
notes: optional string
```

The brief cannot contain numeric analysis parameters, source paths, raw-data
references, conclusions declared as facts, or arbitrary new figures.

### `ManuscriptPlan` output

The deterministic builder reads `ars-writing-input.json`,
`citation-metrics.json`, the figure index, and package manifest through the
existing package-view contract.  It writes a JSON-safe, hashable artifact:

```text
version: 1
plan_id, plan_hash
package: package_id, version, package_hash, relative_path
brief: normalized PaperBrief
selection:
  techniques
  evidence_ids
  results_metric_ids
  discussion_metric_ids
  main_figure_ids
  supporting_figure_ids
writing_boundaries:
  limitations
  prohibited_conclusions
  human_review
status: draft | approved
```

The V1 plan uses `draft` only.  `approved` is reserved for a later review-action
contract; it must not be silently set by an LLM.

## Validation and failure behavior

- The package must load successfully and its existing hashes/contracts must
  validate before plan creation.
- Selected techniques, evidence IDs, metrics, and figure IDs must exist in the
  pinned package.  Unknown references fail with a machine-readable error.
- A `results_metric_id` must be a package Results candidate.  A
  Discussion-only metric cannot be promoted by the brief.
- The figure plan can select only indexed logical figures and cannot exceed its
  declared main/supporting budget.
- Brief roles are descriptive only.  They cannot erase limitations, prohibited
  conclusions, or human-review items inherited from package evidence.
- The builder does not rerun providers, alter an `AnalysisPlan`, write into the
  package directory, copy raw data, or make a scientific conclusion.

## Interface surface

V1 adds one core service and one project-workflow CLI route:

```text
polynexus project-workflow manuscript-plan \
  --package <evidence-package-path> \
  --brief <paper-brief.json> \
  --output <manuscript-plan.json>
```

The route is an export operation.  It reads the package snapshot and writes the
new plan only to the caller-selected output location.  It must not use an
LLM; Codex/ARS may create the brief before calling it.

The core service returns the same DTO used by the CLI, keeping a later GUI
consumer possible without duplicating validation or package parsing.

## Data flow

```text
ARS/Codex conversation
  -> PaperBrief JSON
  -> validated immutable EvidencePackage
  -> ManuscriptPlan builder
  -> manuscript-plan.json
  -> ARS full-draft prompt / later GUI review
```

The plan's figure choices are selections from existing package figure assets.
Changing display treatment or producing new figures remains a separate,
explicit figure-plan task that uses the frozen analysis outputs.  It is not
part of this interface.

## Testing

- A focused core test creates a representative package fixture and proves that
  the builder retains package identity, inherited limits, review items, and
  valid selections.
- Negative tests reject stale/tampered package identity, unknown evidence or
  figure IDs, Results promotion of a diagnostic metric, and figure-budget
  overflow.
- A CLI-orchestration test proves JSON input/output uses the same core DTO.
- Existing ARS/package-view tests remain the producer/consumer regression
  matrix because the plan reads their public contracts.

## Deferred work

- ARS document generation from an approved plan.
- Human approval persistence and targeted manuscript revision records.
- GUI display/editing of the plan.
- Generating new publication figures from a presentation specification.
- A real elastic-body paper rehearsal after the V1 interface is complete.

## Human review

This is an architecture and scientific-boundary change.  A local checkpoint
does not authorize merge.  Human review must verify that the interface keeps
the GUI optional, package snapshots immutable, and ARS unable to promote a
diagnostic result or causal mechanism through the brief.
