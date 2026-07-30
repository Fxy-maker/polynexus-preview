# IR Thermo Mapping Semantics Design

## Goal

Represent the Thermo Scientific OMNIC Picta mapping rules in PolyNexus so IR
mapping figures and evidence explain their spatial axes and ROI interpretation
without pretending that a real vendor-native map file was supplied.

## Source boundary

The authoritative source is the Thermo Fisher Scientific `OMNIC Picta User
Guide` (269-257900, Rev A). The guide states that:

- an area map uses X-position columns and Y-position rows;
- the microscope stage home/origin is `(0, 0)`;
- map step size is specified independently in X and Y and can expand the drawn
  area to fit an integer grid;
- a map can be an area map, line map, or discrete-point map;
- map information is available through `Show Map Info`.

Official page:
https://knowledge1.thermofisher.com/Molecular_Spectroscopy/Molecular_Spectroscopy_Software/OMNIC_Family/OMNIC_Picta_Software/OMNIC_Picta__Suite_Operator_Manuals/269-257900_-_REV_A_-_OMNIC_Picta_User_Guide

Official PDF:
https://knowledge1.thermofisher.com/@api/deki/files/41523/269-257900_-_REV_A_-_Omnic_Picta_User_Guide.pdf?revision=1

## Non-goals

- Do not implement a `.MAP`, `.GAML`, `.PCIR`, or ENVI map reader.
- Do not infer row-major versus column-major serialization from a scalar
  matrix.
- Do not infer the sample ROI bounds, pixel spacing, scan direction, or
  detector configuration from a 1D `.SPA` file or generated CSV output.
- Do not promote a mapping figure to publication-ready status without the
  existing source-matching scientific review record.

## Design

Add a typed, JSON-safe official semantics profile with these fields:

- `profile_id`: `thermo_omnic_picta_official`;
- `spatial_x`: columns, microscope-stage X position, `um`;
- `spatial_y`: rows, microscope-stage Y position, `um`;
- `origin`: stage home `(0, 0)`;
- `roi_kind`: area-map acquisition boundary or explicitly supplied ROI;
- `step_size_policy`: vendor may expand the drawn area to fit the grid;
- `serialization_order`: unknown until a vendor-native map or coordinate export
  is available;
- `status`: official rule documented, sample metadata unverified.

The profile is attached to mapping provenance and copied into figure recipes and
`to_evidence()`. Figure source columns and axis labels use `X position (um)` and
`Y position (um)`. This changes interpretation visibility only; it does not
change map array values, invalid-pixel masking, ROI spectra, or publication
promotion rules.

## Acceptance criteria

1. Every mapping evidence payload exposes the profile and its unverified status.
2. Every mapping figure recipe exposes the same profile and does not claim a
   serialization order or sample-specific ROI bounds.
3. The map figure labels its axes as vendor X/Y stage positions in `um`.
4. Existing structural validation and scientific-review gating remain intact.
5. Focused mapping tests cover JSON round-trip, evidence, figure recipes, and
   non-promotion when review is absent.
