# Optional Vendor Converter Boundary Design

## Goal

Route ordinary FTIR/SAXS/WAXS table exports through the existing canonical
1-D templates, while keeping vendor-specific readers outside the default Core
path.

## Routing

`CanonicalConverterRegistry` first uses the generic one-dimensional converter
for supported table formats (`csv`, `tsv`, `txt`, `dat`, `asc`, `xy`, `chi`,
`xls`, `xlsx`, `xlsm`) when the technique is IR, SAXS, or WAXS. A valid result
is `spectrum_1d.v1` for IR and `scattering_1d.v1` for SAXS/WAXS. Explicit
mapping ambiguity or invalid numeric input remains `needs_input`; it is never
hidden by the compatibility fallback.

For directories and formats not handled by the generic table converter, the
existing raw-file compatibility envelope remains available. It records source
bytes and provider input identity but does not claim canonical measurements.
Future vendor readers can register at this boundary as optional adapters and
return canonical templates without changing Core capability code.

## Capability handoff

The registry exposes a small helper that executes the finite generic curve
capabilities for a ready canonical template. This returns the existing
immutable `CapabilityItemResult` tuple and does not invoke legacy scientific
providers or assign writing/evidence roles.

## Compatibility and failure behavior

- Generic-ready input: canonical template plus capability items.
- Generic `needs_input`: preserve that status and reason codes.
- Unsupported vendor/directory input: compatibility envelope as before.
- Unknown technique: existing blocked outcome.
- Raw sources are never rewritten or copied.

## Out of scope

No new vendor parser, no DSC `thermal_program.v1`, no GUI/Batch/Codex
migration, and no scientific peak/phase interpretation are included.
