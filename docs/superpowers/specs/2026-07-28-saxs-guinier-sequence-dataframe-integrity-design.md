# SAXS Guinier sequence DataFrame integrity projection design

## Context

`TempSeriesResult.to_dataframe()` already repeats sequence level and reason
codes on each temperature row. The source-index integrity slice now emits
additional fields in `GuinierSequenceEvidence`, but those fields remain buried
in the nested result payload. This makes a CSV/table review less explanatory
than the authoritative JSON evidence.

## Design

Add one private projection helper in `saxs_temperature.py`. It accepts the
existing mapping, returns a fixed dictionary of CSV-safe fields, and returns
`None` for absent/empty sequence facts. Index collections are represented in
their existing order with `|` separators; the reorder field is copied only
when the payload supplies a boolean. The helper never mutates the payload and
does not calculate validity or a replacement ordering.

Projected fields are:

- `Rg_sequence_frame_source_indices`
- `Rg_sequence_missing_frame_indices`
- `Rg_sequence_diagnostic_frame_indices`
- `Rg_sequence_invalid_temperature_indices`
- `Rg_sequence_duplicate_temperature_indices`
- `Rg_sequence_nonmonotonic_temperature_indices`
- `Rg_sequence_continuity_break_indices`
- `Rg_sequence_duplicate_source_index_indices`
- `Rg_sequence_invalid_source_index_indices`
- `Rg_sequence_source_index_order_reordered`

The helper is merged into every existing temperature row after the level and
reason fields. This preserves row cardinality, the sorted-temperature source
mapping, and all existing consumer behavior. It intentionally does not add a
new aggregate `status` field: the existing `level` and `reason_codes` remain
the authoritative classification.

## Failure and compatibility behavior

An absent sequence mapping keeps the row and returns the same empty/`None`
style used by existing flat provenance projections. An empty index collection
is represented as an empty field (`None` in pandas/CSV), while explicit
`False` for the reorder flag remains `False`. Malformed non-mapping input is
treated as absent for this presentation-only projection; core evidence
construction remains unchanged.

## Testing

Use a pure `TempSeriesResult` fixture with a copied nested payload to assert
all fields, strict value preservation, and no mutation. Add a second test with
no sequence payload to assert row preservation and empty projection fields.
Run the existing temperature sequence and data-quality DataFrame tests plus
the exact SAXS matrix and structured verifier.
