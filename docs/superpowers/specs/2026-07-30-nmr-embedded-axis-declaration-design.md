# NMR embedded axis declaration design

## Decision

Parse the explicit `acquisition` block embedded in JEOL/Delta JDF payloads as
read-only provenance. The declaration identifies the vendor's first and only
1D dimension (`x`, dimension 1), its physical domain, and the fields that define
the declared axis origin, sweep, and point count.

For the checked-in files, the source text is explicit:

```text
x_domain => "Carbon13";
x_offset => 100[ppm];
x_sweep  => 300[ppm];
x_points => 1024;
```

and:

```text
x_domain => "Proton";
x_offset => 0[ppm];
x_sweep  => 200[ppm];
x_points => 2048;
```

## Boundary

The parsed object is named `vendor_axis_declaration` and carries the original
vendor field names, values, units, source, and `status=declared_not_applied`.
The existing ppm axis remains the current guarded/default result because this
text does not, by itself, establish whether `x_offset` is the displayed-axis
origin, a reference/center offset, or the processed-spectrum orientation.
No assignment, phase split, Xc calculation, or publication decision consumes
the declaration.

Only complete declarations with ppm units, a positive finite sweep, and a
positive integral point count are retained. Missing or malformed declarations
are omitted without changing the existing fallback behavior.

## Data flow

```text
JEOL acquisition text
  -> NMRSpectrum.metadata.vendor_axis_declaration
  -> NMR output_parameters
  -> AnalysisEvidence.feature_evidence.axis_evidence.vendor_declaration
  -> Results review / export provenance
```

## Verification

The two checked-in real files are read-only fixtures. Regression coverage
checks both domains and rejects non-ppm declarations. Existing NMR lifecycle,
assignment-limited solid-C, and Xc-gate tests remain authoritative for the
scientific boundary.
