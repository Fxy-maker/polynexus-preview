# IR Thermo/OMNIC mapping semantics acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-30-ir-thermo-mapping-semantics.md`

## Scope

This checkpoint records the official Thermo Scientific OMNIC Picta semantic
fallback used by the IR mapping contract. It does not claim that the current
workspace contains a vendor-native two-dimensional mapping file.

## Official rules represented

The profile `thermo_omnic_picta_official` records:

- X position is the area-map column axis and Y position is the row axis;
- both spatial axes are microscope-stage positions in `um`;
- stage home/origin is `(0, 0)`;
- an area-map boundary or explicit ROI is adjusted to the vendor grid when
  X/Y step sizes require it;
- flattened scan order is unknown without a vendor map or coordinate export;
- sample-specific ROI bounds and calibration remain unverified.

Source: Thermo Fisher Scientific, `OMNIC Picta User Guide`, 269-257900 Rev A.
Relevant printed pages are 3 (map types), 28 (origin), 34-35 and 45 (area
boundary and step-size adjustment), 44 (X columns/Y rows), 73 (physical X/Y
positions), and 79 (map collection metadata).

- Official page:
  https://knowledge1.thermofisher.com/Molecular_Spectroscopy/Molecular_Spectroscopy_Software/OMNIC_Family/OMNIC_Picta_Software/OMNIC_Picta__Suite_Operator_Manuals/269-257900_-_REV_A_-_OMNIC_Picta_User_Guide
- Official PDF:
  https://knowledge1.thermofisher.com/@api/deki/files/41523/269-257900_-_REV_A_-_Omnic_Picta_User_Guide.pdf?revision=1

## Current data boundary

`测试数据/IR` contains two Thermo/OMNIC `.SPA` one-dimensional spectra and
CSV temperature-series data plus generated outputs. It contains no `.MAP`,
`.GAML`, `.PCIR`, ENVI map, or coordinate export. Therefore the implementation
does not infer a sample ROI, a detector grid, a pixel calibration, or a
row-major/column-major flattening order.

## Implementation evidence

- `IRMappingResult.to_evidence()` publishes the profile under
  `mapping_semantics`.
- All three IR mapping figure recipes publish the same profile.
- Map and invalid-pixel figure coordinates are labeled `X position (um)` and
  `Y position (um)` with `um` source units.
- Existing invalid-pixel validation and source-matching scientific review
  promotion are unchanged.

## Verification

Focused tests:

```text
python -m pytest tests/test_ir_mapping.py tests/test_ir_lifecycle_closure.py -q
18 passed in 22.89s
```

Full IR regression:

```text
python -m pytest (Get-ChildItem tests -Filter 'test_ir_*.py').FullName -q
55 passed in 41.70s
```

Task-scoped verifier:

```text
python scripts/verify.py --task docs/agent/tasks/2026-07-30-ir-thermo-mapping-semantics.md --changed --types
```

The command completed with exit code `0`: task-card/memory checks, Ruff,
compile, type baseline, quality gate (`290 passed`), preprocessing gate
(`106 passed`), and whitespace all passed.

The read-only storage report returned `55` artifacts and `eligible_bytes=0`;
no cleanup or `--apply` operation was performed.

The explicit allowlist checkpoint uses the message
`feat(ir): document thermo mapping semantics`. No push was performed.

## Remaining limitation

This is an official-rule, unverified-sample semantics profile. A future native
map or coordinate export can replace the unknown fields without changing the
figure lifecycle contract.
