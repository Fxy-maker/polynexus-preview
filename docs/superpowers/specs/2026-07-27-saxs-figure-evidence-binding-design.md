# SAXS Figure and Manifest Evidence Binding Design

**Date:** 2026-07-27
**Status:** approved working design for the next SAXS atomic task

## Goal

Bind already-emitted SAXS quality evidence to every static, temperature, and
strain `FigureDefinition` so a Figure Manifest can explain which frames and
quality records support a figure, while preserving the existing publication
roles and numerical analysis results.

## Problem and evidence boundary

The SAXS analysis and export paths already emit frame-level `metric_evidence`,
Guinier evidence, temperature sequence evidence, detector-quality evidence,
orientation evidence, and the authoritative `quality_evidence.json` export.
Figure providers currently preserve frame role/reason metadata, but do not
carry a stable reference to those existing evidence records. This makes a
manifest-backed figure inspectable as an artifact, but not fully auditable as
an evidence consumer.

This task is a transport and provenance closure. It does not recalculate a
metric, infer applicability, select a missing frame, or decide whether a
scientific claim is true.

## Alternatives considered

1. **Change publication-role eligibility now.** This would make figures more
   conservative, but requires method-specific scientific rules for deciding
   which metrics are required by each figure. That is a separate reviewable
   task and would risk changing existing roles accidentally.
2. **Attach a compact, read-only evidence reference to each FigureDefinition.**
   This reuses the current contracts, makes Manifest/Gallery/Editor audit
   context available, and leaves role policy unchanged. This is the selected
   approach.
3. **Copy the complete quality-evidence payload into every figure.** This would
   duplicate large data and create synchronization ambiguity between a figure
   manifest and the bundle-level `quality_evidence.json`.

## Contract

The FigureDefinition recipe may contain an `evidence` mapping with:

- `schema_version`: integer `1`;
- `mode`: `static`, `temperature`, or `strain`;
- `quality_evidence_file`: the stable bundle-level filename
  `quality_evidence.json`;
- `frame_indices`: the figure's source-frame indices;
- `source_indices`: original source indices when the mode provides them;
- `frame_records`: compact per-frame records containing condition, source path,
  evidence levels, reason codes, and source references;
- `series_record`: compact series-level records when a completed condition
  series provides them, including metric summaries, Guinier sequence summary,
  detector/orientation summary, and their source references.

Only existing fields are projected into the compact record:
`metric_name`, `level`, `applicable`, `reason_codes`, `source_ref`,
`data_quality_ref`, `processing_ref`, and the existing sequence/2D summary
fields needed to locate the authoritative record. Unknown or malformed input is
not repaired; an absent field remains absent. The projection is detached and
strictly JSON-safe.

`frame_indices` identify the frame in the Figure provider's source order.
`source_indices` identify the original acquisition order when available. Both
are retained so temperature sorting cannot silently change provenance.

## Architecture and data flow

Add one provider-side helper in the SAXS figure common layer. It accepts
existing `SAXSFrameView` objects, an optional completed series object, and the
resolved mode. It returns a detached evidence mapping and never calls an
analysis routine. A small decorator/attachment function adds that mapping to
the existing recipe without replacing existing `recipe["evidence"]` role and
omission data; the two are merged under the same mapping with stable keys.

The helper is used by both the production providers and the compatibility
provider:

```text
SAXSResult / TempSeriesResult / StrainSeriesResult
       -> existing SAXSFrameView / series DTOs
       -> compact FigureDefinition.recipe["evidence"]
       -> Figure Manifest / Gallery / Editor
       -> bundle-level quality_evidence.json via quality_evidence_file
```

The existing Export Bundle remains the authoritative source of full evidence.
The Figure Manifest stores a reference and compact audit context, not a second
quality database.

## Mode behavior

- **Static:** frame records use the existing static frame payloads. Batch
  figures retain frame index order and do not acquire a temperature/strain
  trend interpretation.
- **Temperature:** frame records are aligned to the Figure provider's frame
  index and retain the corresponding original `source_index`; the completed
  series record retains `metric_evidence` and `guinier_sequence_evidence`
  without copying one frame's evidence to another.
- **Strain:** frame records and series records use the existing strain point
  order and evidence fields. Orientation remains a separately named record and
  is not folded into generic 1D metrics.
- **Missing evidence:** the figure remains available under existing role
  policy, but the corresponding reference is absent or marked as missing in
  the compact record. No positive evidence is manufactured.

## Failure and compatibility behavior

Evidence attachment failure must not prevent a legacy figure definition from
being returned. The provider records a deterministic `evidence_attachment_failed`
reason in the recipe only when the existing recipe can accept an evidence
mapping; it leaves figure data, roles, and legacy recipe keys unchanged.
Existing callers that construct figures without quality fields continue to
produce valid definitions. Strict JSON validation must pass for all attached
records, including non-finite numeric input converted to `null` by the shared
projection helper.

## Testing and acceptance

TDD tests first cover:

1. compact projection is detached, deterministic, and strict JSON-safe;
2. static frame and batch definitions retain existing roles and expose frame
   metric evidence references;
3. temperature definitions preserve sorted-frame/source-index mapping and the
   sequence-level reference without interpolation or frame copying;
4. strain definitions preserve frame and series evidence, with orientation
   separate from 1D metrics;
5. malformed/missing evidence does not break definitions or create positive
   records;
6. `FigurePipeline`/Manifest serialization and the existing SAXS export
   contract retain the binding.

The task gate is the focused figure/provider matrix, the complete
`tests/test_saxs_*.py` matrix, the structured task verifier, strict JSON
validation, `git diff --check`, and one explicit allowlist checkpoint. Real
scientific sign-off and any future role-gating policy remain separate gates.

## Non-goals

- No SAXS algorithm, q-window, physical threshold, or applicability rule.
- No interpolation, frame repair, AI candidate execution, or automatic rescue.
- No change to publication role, figure selection, or publication profile.
- No raw detector/geometry inference or new 2D calculation.
- No replacement of `quality_evidence.json` or the existing Manifest schema.
