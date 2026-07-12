# SAXS Evidence Filtering and Publication-Rollout Design

Date: 2026-07-12
Task: `mainline-integration-reconciliation-2026-07-12`
Scope: SAXS temperature/strain provider migration, incremental path A

## Goal

Extend the current `origin/main` SAXS figure provider with publication evidence filtering while preserving the current provider API, figure IDs, existing scientific calculations, and shared figure publisher. The migration must make eligibility decisions explicit without importing the integration branch's full provider rewrite.

The first implementation target is evidence filtering for temperature and strain series. Temperature and strain remain separate implementation commits with separate focused regressions, even though they share the same evidence contract.

## Non-goals

- Do not replace `polynexus/core/saxs_engine/figure_provider.py` with the integration branch's provider stack.
- Do not re-run analysis, infer missing scientific values, or repair low-confidence frames in the figure provider.
- Do not change SAXS scientific algorithms, temperature/strain detection, or raw data loading.
- Do not introduce the integration branch's time/Avrami provider, detector-specific panel architecture, or full representative-frame selection in this slice.
- Do not modify GUI code, `D:\PolyNexus`, user-local scripts, or PR #9.

## Current contracts to preserve

- `SAXSEngine.build_figure_definitions()` returns `FigureDefinition` objects consumed by `BaseEngine.publish_figure_definitions()`.
- Existing current-main figure IDs remain stable for this rollout:
  - `saxs.frame.temperature.scattering.*`
  - `saxs.series.temperature.waterfall`
  - `saxs.series.temperature.parameters`
  - `saxs.series.temperature.heatmap`
  - `saxs.frame.strain.scattering.*`
  - `saxs.series.strain.waterfall`
- Existing data source column names and units remain stable unless a focused test proves a compatibility-preserving addition is required.
- Legacy definitions without explicit evidence continue to default to `publication_role="si"`.
- Shared manifest, publisher, audit, persistence, and recovery services remain the only publication lifecycle.

## Design

### 1. Evidence snapshot boundary

`SAXSFrameView` is the provider input boundary. It copies q/intensity arrays and freezes parameter mappings. Providers may read:

- emitted frame arrays;
- emitted `_batch_params` or `analysis.final_parameters`;
- emitted quality and reliability flags;
- existing temperature/strain result points.

Providers must not call analysis functions or derive replacement values while deciding publication eligibility.

### 2. Eligibility decision

Each frame receives one immutable `FigureEligibilityDecision`:

| Evidence | Role | Reason |
|---|---|---|
| emitted `quality_flag` contains an `ERROR` token | `diagnostic` | `analysis_error` |
| emitted `paper_figure_candidate=False` | `diagnostic` | `analysis_rejected_paper_figure` |
| emitted `paper_figure_candidate=True` | `main` | `analysis_approved_paper_figure` |
| emitted `lc_reliability_status="usable"` | `main` | `usable_lamellar_result` |
| emitted `quality_flag="OK"` | `main` | `quality_ok` |
| no promoting evidence | `si` | `limited_or_unclassified_quality` |

An explicit error or rejection vetoes a promoting flag. A warning containing the text `ERROR` but not an `ERROR` token does not become diagnostic. The provider records the decision in definition metadata/recipe; it does not silently discard the evidence trail.

### 3. Temperature filtering slice

The temperature provider keeps the current frame, waterfall, parameters, and heatmap definitions. It adds only:

- eligible-frame filtering for main parameter/trajectory sources;
- stable omission reasons and omitted source indices in the recipe;
- role propagation to per-frame and series definitions;
- regression coverage for a rejected middle frame, missing evidence, and a fully diagnostic series.

The source arrays for omitted frames are not repaired or replaced. If no frame supports a main-series source, that source/panel is omitted or assigned `si`/`diagnostic` according to the emitted evidence; the provider must never fabricate a main trend.

### 4. Strain filtering slice

The strain provider applies the same evidence contract to the current strain frame and waterfall definitions. It keeps current labels, condition values, and figure IDs. Strain-specific scientific interpretation remains in existing analysis output; the provider only filters and annotates evidence-backed content.

Temperature and strain commits must not share a large provider rewrite. Shared helpers may be committed once, then each technique gets its own test and rollback boundary.

### 5. Failure and compatibility behavior

- Mixed completed temperature and strain results remain `unsupported` and publish no figures.
- Declared temperature/strain mode without a completed result remains `incomplete` and does not fall back to static.
- Missing evidence defaults to SI, not main.
- Explicit analysis errors remain diagnostic even if another emitted flag requests main.
- Existing legacy manifests and current publisher behavior remain unchanged.
- A provider exception still propagates through the existing pipeline error handling; this design does not add a new fallback renderer.

## Data flow

```text
SAXSEngine completed result
        |
        v
SAXSFrameView snapshot
        |
        v
FigureEligibilityDecision per frame
        |
        +--> current temperature/strain definitions
        |       +--> stable source arrays
        |       +--> omitted-index/reason recipe metadata
        |       +--> publication_role
        |
        v
shared FigureDefinition -> FigurePipeline -> manifest/audit/export
```

## Testing strategy

Each implementation slice follows RED -> GREEN -> REFACTOR:

1. Add a focused failing test for one evidence/filtering behavior.
2. Verify the failure is caused by the missing behavior, not a fixture or import error.
3. Implement the smallest provider change.
4. Run the focused test and the existing SAXS provider/cutover tests.
5. Run the shared figure contract/pipeline regression group.
6. Run compileall and `git diff --check` before committing.

Required temperature cases:

- eligible main frames retain emitted final values;
- rejected middle frames are omitted from main sources;
- missing evidence is SI;
- diagnostic-only frames are not promoted;
- current temperature figure IDs and validation remain stable.

Required strain cases:

- the same role precedence and veto rules apply;
- condition labels and waterfall ordering remain stable;
- rejected frames are represented only in evidence-backed SI/diagnostic output;
- current strain cutover publishing remains compatible.

## Rollback boundaries

- Shared evidence contract: revert its single commit if role metadata breaks non-SAXS figure consumers.
- Temperature filtering: revert only the temperature provider commit and its tests; retain the shared contract if it remains compatible.
- Strain filtering: revert only the strain provider commit and its tests.
- Do not force-reset, close PR #9, push, or merge as part of these local slices.

## Deferred follow-ups

- deterministic representative-frame selection and manual overrides;
- curated multi-panel temperature/strain publication packs;
- full parity with integration `figure_temperature.py` / `figure_strain.py`;
- DSC/WAXS provider migrations;
- Unified Tables and GUI wiring.

## Acceptance criteria

- Current-main SAXS figure IDs and shared publication lifecycle remain compatible.
- Every published role is derived from emitted evidence and is explainable by a stable reason.
- No main figure contains a value that was recomputed or repaired by the provider.
- Temperature and strain each have independent focused regression evidence and commits.
- The design does not include user-local files or integration branch history as an opaque merge.
