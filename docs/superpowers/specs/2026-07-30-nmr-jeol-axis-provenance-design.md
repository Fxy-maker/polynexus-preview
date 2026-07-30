# NMR JEOL Axis Provenance Design

## Decision

Treat the JEOL record values as raw vendor metadata until their physical unit
is explicit. The observed records use a 64-byte layout with the field name at
record offset 4 and payload fields after the record type. The reader may
preserve those values, but it must not reinterpret frequency-like values as
ppm.

## Data contract

The loaded spectrum metadata will contain:

```json
{
  "ppm_axis_source": "default_range",
  "ppm_axis_reason": "jeol_metadata_units_unconfirmed",
  "ppm_axis_units": "ppm",
  "ppm_axis_calibrated": false,
  "ppm_range": [240.0, -20.0]
}
```

Raw vendor fields remain under `metadata.params`; they are evidence of what the
file contains, not a calibration claim. A vendor-derived axis is allowed only
when the existing numeric range guard confirms a plausible ppm value and the
source field is explicitly ppm-calibrated.

## Failure behavior

Missing, malformed, or implausible vendor fields retain the default axis and
emit a machine-readable reason. The lifecycle remains diagnostic or
assignment-limited where its existing review policy requires it.

## Verification boundary

The checked-in solid 13C JDF files are read-only fixtures for the parser and
real lifecycle tests. No generated output under those fixture directories is
modified.
