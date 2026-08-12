# Canonical Experiment Templates and PA6 DSC Conversion Design

## Decision

PolyNexus will introduce a canonical experiment template boundary between raw
instrument artifacts and deterministic scientific providers. AI may identify a
format and propose a mapping to a registered template, but it cannot submit
unvalidated numeric data or select scientific conclusions. The first provider
is a deterministic converter for a Mettler-style, multi-program DSC text export
such as the external PA6 `PA6-DWJJ.txt` file.

## Why

File extensions do not express experimental meaning. The PA6 file is one text
artifact containing ramps, melt holds, and independent isothermal
crystallisation holds at 180--185 C. Treating it as one thermogram loses the
kinetic structure; treating a directory as a universal series would mix samples
and conditions. The algorithm needs experiments, not files.

## Boundary

```text
raw artifact (path + SHA-256, read only)
  -> converter proposal (rule or AI)
  -> canonical template + conversion record
  -> strict validator
  -> public provider adapter
  -> AnalysisResult / workflow evidence
```

### Canonical template

The template is a frozen JSON-safe DTO. It has a template id/version, source
artifact identity, ordered segments, a content hash, and conversion-record id.
The initial DSC schema is `dsc.isothermal.v1`:

```json
{
  "template_id": "dsc.isothermal.v1",
  "source_artifact_id": "sha256-derived-id",
  "sample": {"label": "PA6", "mass_mg": 5.95},
  "segments": [
    {
      "segment_id": "iso-180C-001",
      "role": "isothermal_crystallization",
      "setpoint_C": 180.0,
      "time_s": [0.0, 1.0],
      "sample_temperature_C": [180.4, 180.1],
      "heat_flow_mW": [9.44, 9.40],
      "source_range": {"start_row": 780, "end_row": 1080}
    }
  ]
}
```

Arrays retain data values because they are the validated analysis input. They
are persisted only in a derived run/template output outside raw-data
directories, never into Git or the source directory. The raw artifact hash and
source row/time range make each value traceable back to the original export.

### Conversion record

The record records converter id/version, input hash, observed columns/units,
source ranges, rules applied, per-segment confidence, warnings, and blockers.
It distinguishes facts such as `time_column_seconds`, `setpoint_column_C`, and
`sample_mass_mg` from an inference such as `isothermal_crystallization`.

The record has no free-text scientific conclusion. An eventual AI recognizer
returns the same declarative mapping proposal; a deterministic validator must
accept it before a template is created.

## PA6 Mettler converter

The converter parses the observed numeric form `[index, time_s, sample_C,
setpoint_C, heat_flow_mW]` and sample mass metadata. It groups contiguous rows
with an equal setpoint, then considers a group an isothermal candidate only if:

- duration meets the existing configured DSC isothermal minimum;
- sample temperature is finite, has at least 30 points, a minimum duration,
  bounded offset/span (0.5 C), bounded noise (0.05 C standard deviation), and
  bounded whole-hold drift around the setpoint;
- time is strictly increasing and heat flow is finite;
- it is not a high-temperature melt hold, identified conservatively as a
  preceding preparation segment when a lower-temperature candidate follows.

The converter preserves all groups in the conversion record. Only accepted
crystallisation holds appear in the canonical template. If no candidate passes,
the outcome is blocked with source-based reasons, never a guessed fallback.

The execution adapter repeats this template-level qualification before fitting.
It intentionally does not invoke raw-program `detect_isothermal_segments` a
second time: that detector uses adjacent-point drift to discover holds inside a
mixed ramp/hold scan, and reapplying it to an already accepted Mettler hold
splits the PA6 180--185 C segments because of point-level instrument noise.
The canonical contract instead preserves the converter's explicit boundaries
and validates the same durable constraints before deterministic Avrami fitting.

For PA6 the expected converted series is the six holds at 180, 181, 182, 183,
184, and 185 C. The 255 C holds remain preparation evidence, not Avrami input.

## Provider integration

`DSCEngine` gains one public method that accepts a validated
`dsc.isothermal.v1` template. It materializes the template's accepted segments
as the existing `DSCScan` objects and calls existing `run_kinetics` / figure /
evidence paths. It does not reimplement Avrami fitting.

The agent workflow's DSC step may reference either a directory series or a
single file when a registered converter yields the required template. The step
stores the template hash and conversion record in public step provenance. Hash
replay checks still occur before conversion and provider invocation.

## Error handling

- Unsupported raw format: `conversion_format_unsupported`.
- Required columns/units unavailable: `conversion_columns_missing`.
- No qualified isothermal hold: `conversion_no_qualified_isothermal_hold`.
- Template mutation/hash mismatch: `canonical_template_invalid`.
- Provider receives only a validated template; unvalidated maps are rejected.

## Testing and real-data boundary

Synthetic tests use a small Mettler-like multi-program fixture and assert exact
segment selection, source ranges, hashes, and rejection conditions. A separate
read-only PA6 smoke replay can use the external desktop path and writes derived
outputs only outside that directory. It provides integration evidence, not
scientific publication sign-off.
