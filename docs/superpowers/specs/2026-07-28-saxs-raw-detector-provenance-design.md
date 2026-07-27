# SAXS Raw Detector Geometry and Mask Provenance Design

**Date:** 2026-07-28
**Status:** Approved for implementation in the current SAXS quality goal
**Related task:** `docs/agent/tasks/2026-07-28-saxs-raw-detector-provenance.md`

## Goal

Make the source of raw detector geometry and the origin of the existing mask
explicit in the detector quality payload, so downstream diagnostics and Figure
evidence can distinguish header evidence from configuration fallback without
making a scientific validity claim.

## Design

Extend `DetectorQualityReport` with two optional mappings:

```text
geometry_provenance = {
  source: header | config_default | mixed | invalid_header,
  field_sources: {
    wavelength_m: header | config_default | invalid_header,
    pixel_size_m: header | config_default | invalid_header,
    sdd_m: header | config_default | invalid_header,
    beam_center_x: header | config_default | invalid_header,
    beam_center_y: header | config_default | invalid_header,
  },
  values: { ...effective config values... },
  validity: not_assessed,
}

mask_provenance = {
  source: saxs_config.dummy_value | none,
  configured: true | false,
  shape: [height, width] | null,
  validity: not_assessed,
}
```

The preprocessing boundary receives the original EDF header and the effective
`SAXSConfig` after the existing header extraction. It classifies only whether a
known explicit header value is finite and physically representable for the
existing extraction path. A missing field uses `config_default`; a present but
unparseable or invalid field uses `invalid_header`; valid explicit values use
`header`. The effective config values are transported as evidence, not judged.
The aggregate source is `header` when every field is explicit and valid,
`config_default` when all fields fall back, `mixed` otherwise, and
`invalid_header` when invalid header input is present without a usable mixed
classification.

The mask source is derived only from whether the existing `_build_mask()` was
configured by `cfg.dummy_val`. No image statistic is consulted. Its shape is
reported only when the image is two-dimensional and the mask is shape-aligned.
`validity="not_assessed"` is a deliberate non-approval marker.

Sector-map callers continue to use the existing builder defaults and do not
receive raw detector provenance. The Figure evidence allowlist gains only the
two explicit field names, preserving the existing detached JSON projection.

## Compatibility and error handling

The new builder parameters default to `None`, so old raw and sector-map callers
remain valid. `from_dict()` preserves absent fields as `None` and accepts only
JSON-safe nested values through the existing contract serializer. Header parsing
errors do not abort preprocessing and do not alter the existing quality level
or reason-code rules.

## Verification

Tests will cover complete and mixed headers, invalid header values, absent and
configured dummy masks, strict `json.dumps(..., allow_nan=False)`, Figure frame
and series projection, and sector-map separation. The SAXS matrix and the
structured verifier are required before the explicit allowlist checkpoint.
