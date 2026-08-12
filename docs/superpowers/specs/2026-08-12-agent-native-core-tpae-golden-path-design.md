# Agent-Native Core and TPAE Golden Path Design

## Decision

PolyNexus will retain its technique engines as deterministic scientific
providers and add a narrow orchestration layer for AI agents. The first
complete consumer is an external-data TPAE research workflow. This is not a
rewrite of the GUI, `AnalysisResult`, or every technique pipeline.

The architecture therefore separates the work into two layers:

```text
Agent / CLI / future GUI
          |
          v
Agent workflow contract and registry
          |
          +--> TPAE workflow adapter
          |       +--> DSC pipeline
          |       +--> IR / 2D-COS pipeline
          |       +--> WAXS pipeline
          |       +--> SAXS pipeline
          |
          v
AnalysisResult + AnalysisEvidence + figure recipe provenance
```

The GUI continues to consume persisted results and view models. It must not
call workflow-step internals or implement technique-specific decision rules.

## Problem Being Solved

In the TPAE manuscript task, an AI agent bypassed PolyNexus and created an
ad-hoc Python pipeline. The existing code already has quality evidence, figure
recipes, and `AnalysisResult`, but it lacks one stable machine-facing boundary
that can inspect data, compose analyses, surface explicit limitations, and
replay a result. A generic AI can therefore make faster progress with local
scripts than with the application while losing the application's provenance and
review controls.

The target state is that an AI can use PolyNexus as a constrained instrument:
it asks what is available, proposes a non-mutating recipe, runs it, receives
quality/conclusion limits, and exports a reproducible bundle. The AI never
silently creates a competing analysis path inside a task directory.

## Contract Model

All public agent-workflow payloads are JSON-safe dictionaries generated from
frozen dataclasses. They are stored separately from `AnalysisResult` so existing
GUI, CLI, persistence, and figure code remain compatible.

### InputArtifact

An `InputArtifact` identifies one raw input without loading it into an agent
prompt.

Required fields:

- `artifact_id`: stable identifier from a SHA-256 digest and canonical path
  representation.
- `path`: resolved local path, emitted only to the local caller.
- `technique`: declared technique or `unknown`.
- `format`: suffix/directory form recognized by the adapter.
- `sha256`: file hash; directory artifacts use a deterministic manifest hash.
- `header_facts`: only directly observed facts such as EDF geometry values.
- `inspection_status`: `ready`, `review_required`, or `blocked`.
- `reasons`: machine-readable reason codes with human-readable detail.

Inspection never guesses calibration. A complete EDF geometry header may enable
q-axis processing while a missing background remains an intensity/absolute
quantity limitation; both facts must be returned separately.

### AnalysisRecipe

An `AnalysisRecipe` is a versioned, immutable description of an intended run.
It contains a `workflow_id`, `contract_version`, input artifact identifiers,
ordered `RecipeStep` objects, and a SHA-256 `recipe_hash` computed from a
canonical JSON representation.

Each step identifies an existing provider boundary, declared parameter values,
and their source: `user`, `manifest`, `header`, or `default`. AI-generated
values must be qualitative intents and cannot directly become scientific
numeric parameters without a policy-approved mapping or user confirmation.

### AnalysisRun

`AnalysisRun` records execution without serializing engine-private arrays. Each
step records `status`, result-summary reference, result evidence, figure recipe
references, and structured reasons. Status vocabulary is:

- `completed`: output is available and within the configured quality boundary;
- `review_required`: output exists but human scientific review is required;
- `blocked`: the step cannot produce its declared output safely;
- `failed`: unexpected execution failure, with sanitized error data.

The parent run is successful only when every required step is `completed` or
`review_required`; a blocked required step prevents report promotion.

### EvidenceRecord

`EvidenceRecord` normalizes existing `analysis_evidence`, validation flags, and
workflow-specific evidence into three explicit scopes:

- `observed`: direct outputs such as a DSC half-crystallization time or a SAXS
  q coordinate calculated from recorded detector geometry;
- `supported_interpretation`: bounded statements supported by the applicable
  technique evidence;
- `disallowed_conclusions`: statements that the current data cannot support,
  such as absolute crystallinity without appropriate intensity/background
  treatment or a unique hydrogen-bond species from a 2D-COS sign alone.

This prevents a high score or attractive figure from being converted directly
into a manuscript-grade causal conclusion.

## Agent Operations

The initial public service contains exactly five operations:

| Operation | Input | Output | Mutation |
| --- | --- | --- | --- |
| `inspect_data` | local paths and optional declared techniques | `InputArtifact` collection | none |
| `propose_recipe` | workflow id, inspected artifacts, qualitative intent | `AnalysisRecipe` | none |
| `run_recipe` | recipe and output directory | `AnalysisRun` | output directory only |
| `validate_run` | completed run | run-level `EvidenceRecord` and status | none |
| `export_run` | validated run and destination | manifest/result bundle | destination only |

The service returns structured failure objects for expected user/data errors.
Unexpected exceptions are caught at the public boundary, logged locally, and
returned with an opaque error code rather than a traceback or silent fallback.

No operation writes to an input artifact directory. `propose_recipe` and
`validate_run` are read-only. The CLI prints exactly one JSON envelope per
operation so an AI can consume it reliably.

## TPAE Golden Workflow

`tpae.characterization.v1` is a manifest-driven adapter, not a hard-coded
external path. An external manifest maps named input artifacts to steps:

```text
dsc_isothermal      required, primary quantitative evidence
ftir_temperature    required, local-environment support
waxs_profile        optional, structural context
saxs_profile        optional, structural context
```

The first implementation validates the manifest, inspects each artifact,
proposes steps only for available inputs, invokes established engine/service
boundaries, and aggregates their existing evidence. It does not add new DSC,
FTIR, WAXS, or SAXS scientific algorithms. Where a provider has no safe
adapter yet, the step is `blocked` with a next-action reason rather than a
silent ad-hoc analysis.

Evidence rules are deliberately asymmetric:

- DSC is the primary quantitative evidence for thermal/kinetic values produced
  by the existing qualified path.
- FTIR and 2D-COS describe bounded local-environment and response information;
  they do not by themselves identify one unique hydrogen-bond species.
- WAXS/SAXS are structural-context evidence. Header-derived geometry may
  support q/angle coordinates; missing background/normalization requirements
  constrain intensity-derived or absolute claims rather than erasing direct
  header evidence.
- The workflow report preserves technique limitations even if another step is
  successful.

## Data, Replay, and Export

Real TPAE experimental data remains outside the repository. The user creates a
local manifest containing paths; PolyNexus inspects the paths and emits their
hashes into the recipe and export bundle. Repository tests use synthetic files
and fixture manifests only.

`export_run` writes an output bundle with:

```text
run.json                 run and step statuses
recipe.json              canonical recipe and recipe hash
artifacts.json           paths, hashes, formats, and header facts
evidence.json            observed/support/disallowed scopes
results/<step>.json      public result summaries
figures/                 provider-created immutable figure assets and manifests
```

Replaying a recipe checks artifact hashes before invoking any provider. A hash
mismatch is `blocked`; PolyNexus does not claim reproducibility from a changed
input file.

## Compatibility and Rollout

`AnalysisResult` remains the individual-technique result object. Existing
`run_pipeline`, GUI routes, `ai-tune`, persistence, and figure providers keep
their public behavior. The new workflow layer adapts them at the boundary.

Rollout is staged:

1. Contract types, service, registry, JSON serialization, and synthetic tests.
2. TPAE manifest validation and inspection with provenance/hash replay gates.
3. Adapter bindings for existing qualified DSC and IR paths, followed by
   WAXS/SAXS context bindings only when their current evidence contracts fit.
4. CLI command and export bundle.
5. GUI review surface only after the CLI/API golden path is stable.

No current technique engine is removed during this rollout. The first working
slice must be useful on synthetic fixtures and produce honest blockers for
unimplemented adapters; it is not allowed to pretend that all TPAE data is
automatically publication-ready.

## Testing Strategy

Focused tests cover public behavior, not engine private state:

1. Inspection hashes an artifact and separates present geometry from absent
   background information.
2. Recipe proposal is deterministic for the same artifact identities and
   intent, and fails when required TPAE DSC input is absent.
3. A synthetic workflow run returns a JSON-safe step/run envelope and preserves
   provider evidence limits.
4. Hash mismatch blocks replay before provider invocation.
5. Missing/unsupported files become structured `blocked` results.
6. Export contains the recipe, artifact hashes, evidence, result summaries, and
   no raw data copy.
7. Existing `AnalysisResult.to_dict()` and current CLI tests remain green.

## Risks and Controls

| Risk | Control |
| --- | --- |
| New layer duplicates technique logic | The adapter only calls existing public provider/engine boundaries. |
| AI invents processing parameters | Recipes record parameter source; unapproved numeric mutation is rejected. |
| QC hides useful direct evidence | Evidence separates coordinate/header facts from intensity/interpretation limits. |
| Real data leaks into Git | Only path/hash manifest references are supported; tests use synthetic fixtures. |
| Large migration stalls delivery | The first slice is contract + manifest + one real workflow, not all techniques or GUI. |

## Approval Boundary

Implementation may begin after review of this design. The initial code slice is
limited to contracts, registry/service, synthetic TPAE manifest inspection,
recipe/replay gates, and focused CLI/export behavior. Scientific-method changes
inside DSC, FTIR/2D-COS, WAXS, or SAXS require separate task cards and human
review.
