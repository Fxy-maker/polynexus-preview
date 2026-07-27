# SAXS Static 1D Evidence Product Chain Design

Date: 2026-07-27
Status: approved working design
Related Goal: 建立可解释、可验证、可降级的 PolyNexus SAXS 数据质量与分析体系

## Goal

Close the existing static 1D evidence transport boundary so that a static
single frame and a static multi-file batch expose the same existing SAXS
quality evidence through parameters, Workbench, History, and Export.

## Scope and non-goals

This slice covers:

- static single-frame `SAXSResult` evidence transport;
- static multi-file frame evidence and an unconditioned batch summary;
- Results Workbench and History consumption of the transported payload;
- static Export quality provenance for the frame and batch paths;
- regression tests for missing, malformed, diagnostic, and unusable evidence.

This slice does not:

- change Guinier, Porod, Kratky, invariant, or lamellar calculations;
- add or calibrate physical thresholds or quality gates;
- infer, repair, interpolate, or copy evidence between frames;
- interpret a static file collection as a temperature or strain trend;
- add 2D detector/orientation logic, AI rescue execution, or publication
  authorization.

## Existing boundary audit

`analyze_single()` already attaches JSON-safe `data_quality_report`,
`guinier_evidence`, and `metric_evidence` to each `SAXSResult`. The existing
SAXS Export quality payload reads these fields for a static analysis. The
missing product boundary is that static `SAXSEngine.get_parameters()` exposes
only legacy structural numbers, and static batch rows do not carry their
aligned frame evidence. The existing Workbench serializer already preserves
nested evidence in Diagnostics once it is present in the parameters payload.

## Contract

### Static single frame

The static parameters payload retains all legacy numeric keys and additionally
copies, without mutation or reinterpretation, any present fields from the
analysis result:

- `data_quality_report`;
- `guinier_evidence`;
- `metric_evidence`.

Absent fields remain absent. Non-finite values are handled by the existing
JSON-safe transport boundary; no placeholder numeric result is created.

### Static batch

Each `_batch_data` row is aligned by frame index with `_batch_results` and may
carry the same three evidence fields. A failed or missing analysis row carries
no fabricated evidence. Existing structural and status fields remain
unchanged.

The top-level payload carries:

- `metric_evidence`: the existing conservative frame aggregation built from
  the aligned per-frame `metric_evidence` mappings;
- `metric_evidence_scope: "static_batch"`.

The aggregation reports coverage, frame-level quality counts, and deterministic
reason codes using the existing `build_series_metric_evidence()` contract. It
is a batch-quality summary only. `metric_evidence_scope` is consumed by the
presentation layer so static batches are labelled as batch quality and never
as a temperature/strain trend. The existing `Trend` value remains an evidence
quality level and is not reinterpreted as a physical condition trend.

### Workbench and History

The SAXS presentation service continues to consume DTO-like parameters rather
than technique-specific engine state. For `metric_evidence_scope=static_batch`
it uses the existing risk/next channels to show:

- metric name and existing evidence level;
- evidence coverage and diagnostic/unusable/missing counts;
- deterministic reason codes when downgraded;
- batch-quality wording rather than condition-axis wording.

The Diagnostics section keeps the complete nested evidence JSON. History
persists and restores the same parameters payload through the existing
analysis-run persistence path.

### Export

Static single-frame Export keeps its current `static` evidence shape. Static
batch Export adds aligned frame evidence under the static quality payload and
retains the batch summary, without changing numeric result or figure schemas.
The existing JSON sanitization remains authoritative.

## Data flow

```text
analyze_single()
  -> SAXSResult evidence fields
  -> SAXSEngine.get_parameters()
  -> parameters / History
  -> build_saxs_results_presentation()
  -> Workbench review + Diagnostics

static _batch_results
  -> aligned _batch_data frame evidence
  -> conservative batch metric summary
  -> parameters / History / quality_evidence.json
```

## Failure and downgrade policy

- Missing result or missing metric mapping stays missing.
- Malformed nested evidence is preserved for Diagnostics and ignored by the
  compact review formatter when it cannot be summarized.
- Diagnostic and unusable frames lower the existing aggregate level; they do
  not delete legacy numeric outputs.
- A static batch with no analyzable frames remains explicitly unusable in the
  aggregate evidence rather than being treated as an empty successful batch.
- No GUI path performs recalculation, imputation, or physical acceptance.

## Verification and acceptance

Focused tests must prove:

1. static single parameters transport exact evidence without mutation;
2. static batch rows preserve index alignment and missing-frame absence;
3. static batch summary has coverage and downgrade reasons but no condition
   trend wording;
4. Workbench shows batch-quality review text and full nested Diagnostics;
5. History round-trips the evidence payload unchanged;
6. Export contains static single and batch frame/summary evidence;
7. strict JSON, existing SAXS regression tests, the task verifier, and
   `git diff --check` pass.

## Review notes

This design deliberately reuses existing evidence builders and presentation
channels. It adds transport scope metadata only to disambiguate static batch
aggregation from condition-axis semantics; it does not introduce a new
scientific claim.
