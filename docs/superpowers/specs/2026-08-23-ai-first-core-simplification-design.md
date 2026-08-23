# AI-First Compute-Core Simplification Design

## Decision

PolyNexus will become an AI-first deterministic analysis workbench.  Its
default path will convert real instrument data, calculate results, render
figures, and preserve minimal reproducibility data.  It will not decide
whether a result is manuscript-ready before it allows analysis to run.

The current paper/evidence/review architecture is not merely hidden.  It will
be removed from the supported runtime in staged, dependency-safe deletion
batches.  Git history retains the old implementation for recovery; no legacy
"advanced" code remains silently imported by the new default path.

This decision responds to the six-sample replay: real DSC files need more
flexible canonical conversion, while FTIR and scattering data need transparent
warnings and better data contracts, not a growing collection of blockers and
publication-role gates.

## Product boundary

The product has one primary outcome:

```text
Raw files -> AI-assisted conversion -> deterministic calculation -> figures,
numbers, and rerunnable analysis record
```

Writing, evidence-package creation, claim ranking, cross-technique conclusion
making, and literature retrieval are not prerequisites to this outcome.  They
may be rebuilt later as explicitly invoked, external or optional layers, but
they are outside this migration's supported runtime.

## Target architecture

The physical top-level package may remain `polynexus/core` during migration to
avoid a disruptive import rename.  Its ownership boundary becomes the small
compute kernel below; non-compute modules are drained out and then deleted.

```text
                     +-------------------------+
                     | Quick Analysis GUI      |
                     | AI/Codex tools and CLI  |
                     +------------+------------+
                                  |
                                  v
                     +-------------------------+
                     | Application adapters    |
                     | inspect / convert / run |
                     | rerun / read / export   |
                     +------------+------------+
                                  |
                                  v
                     +-------------------------+
                     | Compute kernel          |
                     | contracts               |
                     | conversion              |
                     | technique providers     |
                     | generic figures         |
                     +------------+------------+
                                  |
                                  v
                     +-------------------------+
                     | Raw files + outputs     |
                     | hashes + plans + data   |
                     +-------------------------+
```

Neither AI/CLI nor the GUI may calculate through a private code path.  AI can
recognize formats, propose mappings, select an analysis plan, and request
reruns.  The compute kernel validates the mapping, performs numerical work,
and records the actual plan and source artifacts.

## Shared compute contracts

The new kernel uses five compact, JSON-safe public objects.

### `RawArtifact`

Identifies a local input or an explicitly associated auxiliary input.  It
contains a path reference, content/manifest hash, detected format, directly
observed header facts, and acquisition context if present in the source.  It
does not infer manuscript relevance or material identity from a curve.

### `CanonicalDataset`

Is the universal, technique-specific data template produced after conversion.
It contains coordinate/data channels, units, acquisition metadata, explicit
segments/events when applicable, conversion version, and source locators back
to `RawArtifact`.  It supports real multi-program experiments rather than
assuming one file equals one ideal experiment.

Examples include a DSC program with named ramps/holds, a one-dimensional FTIR
spectrum, and a SAXS/WAXS profile with declared normalization/background
state.  New materials and new sample counts normally require new catalog rows
or interpretation configuration, not a new compute type.

### `AnalysisPlan`

Is an immutable, versioned request to apply deterministic transforms and a
technique provider to a `CanonicalDataset`.  It records parameter values,
parameter source (`observed`, `user`, `AI proposal`, or `default`), and figure
requests.  It contains no manuscript figure role, writing eligibility, or
paper-review status.

### `AnalysisResult`

Contains computed arrays, metrics, diagnostics, warnings, rendered figure
descriptions/assets, the input/plan hashes, and provider version.  A warning
does not downgrade a successfully calculated result into a non-result.

### `AnalysisRun`

Ties artifact, canonical dataset, plan, and result into one rerunnable record.
It gives both entry points the same provenance without serializing separate
AI-only or GUI-only representations.

The lightweight project catalog is not a research graph.  It only associates
sample IDs, known material/formulation labels, conditions, groups, and raw
artifacts.  AI may propose those associations; unknown or conflicting fields
remain visible instead of being guessed into scientific facts.

## Status and warning semantics

The runtime has exactly four statuses:

| Status | Meaning | Typical next action |
| --- | --- | --- |
| `ready` | Conversion and plan have sufficient executable input. | Run it. |
| `needs_input` | A resolvable field is missing or ambiguous. | AI/user supplies a mapping, unit, segment, or auxiliary file. |
| `failed` | The data cannot be parsed or the numerical run failed. | Inspect error and repair/retry. |
| `completed` | A result was calculated and recorded. | Inspect, edit figure, export, or rerun. |

Warnings are attached to `CanonicalDataset` or `AnalysisResult`, for example
missing background, automatic baseline choice, unverified material label, or
no replicate.  They never turn a usable curve or metric into
`review_required`.  Only genuinely non-executable input is `needs_input` or
`failed`.

This preserves scientific honesty: a warning limits the wording a later
writer may use, but it does not prohibit data processing or hide the output.

## Keep, replace, and remove inventory

### Retain and simplify

- Technique engines: DSC, IR/FTIR, SAXS, WAXS, and NMR numerical providers.
- Readers, unit handling, and generic preprocessing primitives.
- `canonical_experiments` as the basis for a universal conversion registry;
  expand it beyond the current DSC isothermal slice.
- Generic Figure Document, rendering, chart editing, export, and Origin
  compatibility.  Publication-specific audits are excluded.
- Raw-input hashing and plan/version recording required for reruns.

### Replace

- `agent_workflow` becomes thin application tools over the five contracts:
  inspect, convert, run, rerun, read result, and export.  It has no recipe
  receipt, evidence record, or review-gated success state.
- `project_workflow` is replaced by a light project catalog and batch runner.
  Quick runs may later be attached to a catalog, but neither path creates a
  research graph or evidence package.
- `preprocess_optimization` is reduced to an AI-proposed plan/re-run loop.
  Current policy scoring, stability promotion, and confirmation gates are not
  retained as Core requirements.  Deterministic transforms remain available
  as ordinary plan operations.
- Current analysis-plan evaluation becomes explicit AI/user comparison of
  proposed plans and resulting metrics/figures, rather than a universal
  eligibility service.

### Remove from supported runtime

- `analysis_evidence_*`, scientific-review, evidence constraints, action
  hints, writing eligibility, manuscript figure role assignment, and review
  decision flows.
- Evidence-package generation/view/gallery, metric citation ledgers, ARS
  writing handoff, PaperBrief, and ManuscriptPlan.
- `project_workflow` research graph, package, selection, grouping-for-writing,
  and plan-evaluation paths.
- `agent_workflow` evidence records, HMAC receipt machinery, TPAE-only recipe
  constraints, and `review_required` propagation.
- Joint conclusion/validation workspaces, convergence views, and associated
  cross-technique scientific promotion logic.
- Publication audit, figure eligibility, retirement gates, and other
  paper-readiness logic in figure paths.
- Default RAG runtime dependencies, warmup scripts, and RAG-driven advisory
  entry points.

Tests, GUI pages, CLI commands, documentation, dependencies, and persisted
compatibility adapters for a removed feature are deleted with that feature.
The product does not retain a hidden switch for removed behavior.

## AI and human flows

### Quick Analysis

```text
Select files or folder -> inspect -> convert -> choose/propose plan -> run
-> inspect data/figure -> edit/export -> optionally add to project catalog
```

The GUI is a direct consumer of `AnalysisRun` and `AnalysisResult`.  It may
show warnings, request missing information, and allow explicit parameter
changes.  It does not duplicate DSC/FTIR/SAXS/WAXS private algorithm rules.

### AI/Codex

```text
Inspect project files -> propose grouping/conversion/plan -> run deterministic
tools -> compare reruns -> return figures, values, warnings, and run IDs
```

AI may use surrounding project context to infer the likely technique, sample,
and experimental segment.  It must state uncertain mappings in the plan so a
later run remains intelligible.  It cannot invent a numeric result or bypass
the converter/provider route.

## Migration and deletion batches

The migration is a sequence of atomic tasks.  Deletion begins only after each
replacement boundary has a focused compatibility test.

1. **Inventory and protection tests.** Map imports/entry points for current
   workflow, review, joint, RAG, and figure-audit code.  Add contract tests
   that assert Quick Analysis and AI/CLI obtain the same public run/result
   object.  No behavior deletion yet.
2. **Foundation contracts and direct run path.** Introduce the five compact
   contracts and a generic conversion registry.  Route one quick analysis and
   one AI/CLI command through it.  Existing engines remain numerical sources.
3. **Universal conversion first.** Generalize canonical conversion around
   real DSC multi-program, heating/cooling, FTIR, SAXS, and WAXS datasets.
   A converter returns a usable template or `needs_input`; it does not create
   a paper-review state.
4. **Technique-by-technique numerical migration.** Bind each provider to the
   new run path.  Freeze a set of known-good numerical expectations from
   verified calculations/Origin methods where appropriate.  Use direct AI
   output only to discover discrepancies, never as the sole numerical oracle.
5. **Drain application consumers.** Move Quick Analysis, batch, and AI tools
   to the new contracts.  Preserve chart editing and Origin export over the
   new Figure Document boundary.
6. **Delete review and writing systems.** Delete the evidence, ARS, package,
   workflow, review, publication-audit, joint, and RAG paths once no supported
   entry point imports them.  Delete their tests and dependencies together.
7. **Six-sample acceptance replay.** Run PA6/PA6-50/PA11/PA11-50/PA12/PA12-50
   through the new path, classify outcomes only as completed/needs-input/
   failed, and compare numerical outputs against the approved benchmark
   ledger.  Do not write a manuscript in this acceptance task.

## Accuracy strategy

Simplification alone does not make calculations correct.  Accuracy is repaired
at the conversion/provider boundary, where the six-sample replay actually
found the problems.

- Every real input that previously blocked becomes a regression fixture or a
  hash-addressed external replay case.
- DSC tests cover multi-program segmentation, isothermal holds, and
  heating/cooling data separately.
- FTIR tests separate universal spectrum processing from material-specific
  band attribution.  Unknown material never silently receives PA6 claims.
- SAXS/WAXS tests distinguish directly observable peak/curve outputs from
  quantities that require background, calibration, or replicate context.
- Regressions compare numerical arrays/metrics, parameter plans, and source
  segment locations, not merely whether a figure file exists.

## Acceptance criteria for the implementation program

- A user or AI can process a supported real file without any manuscript,
  evidence-package, or review workflow being created.
- A multi-file project returns reusable calculations/figures for all
  executable data, and actionable `needs_input` objects for ambiguity.
- Quick Analysis and AI/CLI share one canonical dataset, plan, run, result,
  and figure contract.
- `review_required`, writing eligibility, evidence-package, and RAG imports
  are absent from supported runtime paths.
- Existing retained engine golden tests pass, and the six-sample benchmark
  records any numerical discrepancy explicitly.
- The user can export raw-linked data, plan, metrics, and figures without
  entering a paper workflow.

## Risks and controls

| Risk | Control |
| --- | --- |
| Broad deletion breaks hidden GUI/CLI imports. | Use dependency inventory, consumer tests, and small deletion batches. |
| A review rule was concealing a numerical defect. | Replace it with explicit conversion/provider tests before removal. |
| AI infers a wrong material or experimental segment. | Preserve mapping source and uncertainty in the plan; ask for input only when execution is impossible. |
| Reruns stop being reproducible. | Preserve artifact hashes, canonical data, plan version, provider version, and output hashes. |
| Direct AI looks better because it silently changes assumptions. | Compare against an approved numerical benchmark ledger, including source segment and parameters. |
| The refactor never ends. | Require a usable Quick Analysis + AI tool vertical slice before every broad deletion batch. |

## Out of scope

- Generating a final paper or automatically approving scientific conclusions.
- A universal material-chemistry knowledge base.
- A new GUI redesign beyond routing the existing quick path to the new
  contracts.
- Supporting every vendor format before the first simplified vertical slice.

## Approval boundary

This design authorizes only the next planning step: a dependency inventory and
the first protected direct-run vertical slice.  Each deletion batch requires
its own task card, focused tests, structured verification, and cumulative-diff
review.  Any new scientific method or material-specific interpretation remains
subject to separate scientific review.
