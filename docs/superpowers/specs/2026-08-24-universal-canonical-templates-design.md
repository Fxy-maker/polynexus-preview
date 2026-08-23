# Universal Canonical Templates and Maximal Computation Design

## Decision

PolyNexus will use material-neutral canonical datasets to turn one raw export
into every independently executable deterministic calculation that the export
directly supports. A successful conversion is not restricted to one selected
analysis: one artifact can produce multiple measurements, and a failure in one
planned calculation never prevents its siblings from running. The system runs
the finite set of declared capabilities that have validated inputs; it does
not perform an unbounded parameter sweep.

This design supersedes the temporary direct envelope as the intended conversion
boundary. It does not change a scientific method in this documentation task.

## Scope and product boundary

The first canonical families describe data shape and acquired context, not a
polymer or an interpretation:

| Family | Canonical content | Initial use |
| --- | --- | --- |
| `thermal_program.v1` | ordered time, temperature, and heat-flow segments | DSC ramps and holds, including multi-program exports |
| `spectrum_1d.v1` | ordered x/intensity points | FTIR curves |
| `scattering_1d.v1` | ordered q or 2theta/intensity points plus declared background and normalization state | SAXS/WAXS curves |

PA6, PA11, PA12, additives, formulations, and similar labels are not data
schemas. They may be optional project-catalog metadata, but they cannot choose
coordinates, invent channels, or cause a converter to manufacture a scientific
value. Material interpretation, literature review, evidence packaging, RAG,
ARS, Joint, and paper workflows are separate products and are not invoked by
the conversion path.

## Canonical contracts and provenance

`CanonicalDataset` is immutable, ordered, JSON-safe, and hashable. It records
the source artifact identity/hash, template family/version, converter identity
and version, and conversion/mapping provenance. Its ordered `Measurement`
objects are also immutable. A measurement has:

- an ID, family, and role;
- ordered channels and declared units;
- acquisition metadata and any observed instrument context;
- source locators, such as file/sheet/table references, row ranges, point
  ranges, and time ranges; and
- mapping-source annotations and warnings.

Ordering preserves acquisition/program order rather than silently sorting
independent experiments into an assumed scientific series. A source can yield
many measurements: for example, a thermal export can hold ramps and several
isothermal segments, while a workbook can hold multiple independent 1D curves.
The raw artifact remains the source of record; canonical data is the validated,
replayable derived input.

### Conversion and mapping

Conversion begins with deterministic inspection of format, sheets/tables,
headers, candidate coordinate/intensity/thermal channels, units, and available
segmentation evidence. The result may be completed by deterministic rules,
heuristics, or a `MappingProposal` from AI. Each mapped field states one source:
`observed`, `user`, `AI proposal`, or `default`.

AI may rank candidates and select the best mapping only when validated
coordinates, channels, and required segmentation already exist. It records its
choice, warnings, and alternatives in provenance. If a valid coordinate/channel
or required segmentation cannot be established, the relevant measurement is
`needs_input`; uncertain but validated mapping is not a reason to stop sibling
work. AI never emits substituted measurements, fills missing scientific numeric
values, or bypasses deterministic canonical validation.

```text
raw artifact
  -> deterministic inspection
  -> rule/heuristic/AI MappingProposal
  -> canonical validation and immutable CanonicalDataset
  -> all eligible finite capabilities
  -> one ComputeRun with item results, figures, warnings, and provenance
```

## Capability routing and statuses

`CapabilityRegistry` is a finite public registry. Each declared capability
names its accepted measurement family/role and required channels or metadata,
the deterministic adapter, output contract, and figure declarations. It may
not inspect a material name to unlock a calculation, and it may not expand into
an open-ended search for parameters.

Every planned measurement-capability item receives exactly one status:

| Item status | Meaning |
| --- | --- |
| `completed` | The deterministic adapter produced its declared result (and any available figures). |
| `needs_input` | A resolvable prerequisite such as a coordinate, channel, segmentation, calibration, or required metadata is absent or invalid. |
| `failed` | Valid planned input reached the adapter but deterministic execution failed. |
| `not_applicable` | The capability does not apply to this family/role or declared state. |

`ComputeRun` aggregates those item results. It is `completed` when at least one
item completes; it is `needs_input` when no executable measurement exists; and
it is `failed` only when no planned item completes because execution failed.
The per-item record retains mixed outcomes so a calculation failure cannot hide
a usable sibling result. Figures are capability outputs, but concise UI display
is allowed to choose a useful subset; a UI is not required to show every
generated graph at once.

Initial routing examples are:

- an individual validated isothermal hold can run an Avrami capability;
- a thermal ramp can produce the directly supported thermal values;
- nonisothermal analysis runs only when the actual required series is present;
- neutral one-dimensional curves can produce applicable peak/curve items;
- scattering can produce direct peak items from usable q or 2theta data, while
  a quantity needing missing calibration is `needs_input` rather than guessed.

## Shared entry path

Quick Analysis, CLI, Batch, and Codex use one public route:

```text
Quick Analysis / CLI / Batch / Codex
  -> inspect and propose mapping
  -> validate canonical dataset
  -> route every eligible capability
  -> one ComputeRun
```

The GUI may ask a user to resolve a `needs_input` field, and AI/Codex may offer
ranked mapping proposals, but neither owns a private conversion, analysis,
provenance, or persistence format. Batch and Agent/Codex migration occurs only
after their explicit consumer tasks; before then their current routes remain
compatibility paths rather than evidence that this shared path is complete.

## Migration sequence

The migration is staged to protect existing scientific behavior and consumers:

1. Add contracts, validation, mapping provenance, and the finite capability
   registry with contract tests.
2. Add generic 1D CSV, TXT, and XLSX conversion for the spectrum/scattering
   families, including source locators and units.
3. Add general DSC multi-program conversion into `thermal_program.v1`.
   Preserve the existing Mettler PA6 converter's regression behavior as a
   protected adapter; do not alter its Avrami method or qualified-hold rules.
4. Route the general families through capabilities and one `ComputeRun`.
5. Migrate Batch and Agent/Codex consumers to the shared route.
6. Replay the six approved samples (PA6, PA6-50, PA11, PA11-50, PA12, and
   PA12-50) against the benchmark ledger before deleting legacy paths.
7. Delete legacy conversion/workflow code only after consumer/import checks and
   replay acceptance establish that the shared route has replaced it. NMR is
   deferred and is not a deletion precondition for these first families.

## Testing and acceptance

Implementation tasks must add focused tests for immutable ordering/hashes,
field-source provenance, valid and invalid mapping proposals, coordinate/unit
validation, source locators, and mixed independent item outcomes. Converter
tests cover generic 1D CSV/TXT/XLSX inputs plus multi-program thermal fixtures.
The Mettler PA6 fixture remains a regression test; no real source file is
committed or changed.

Cross-entry tests prove Quick Analysis, CLI, Batch, and Codex consume the same
canonical/run contracts as each is migrated. Capability tests prove that one
item failure leaves a sibling result accessible, that missing required input
becomes `needs_input`, and that no material label changes data mapping or
numeric output. The six-sample replay compares arrays, metrics, parameters,
and source segment locations against the approved benchmark ledger; discrepancies
remain explicit rather than being normalized away.

## Risks and controls

| Risk | Control |
| --- | --- |
| AI selects plausible but wrong columns or segments. | Validate all selected coordinates/channels/segments deterministically and retain alternatives/warnings. |
| A material-specific shortcut leaks into conversion. | Restrict schemas and capability eligibility to observed families, channels, metadata, and declared state. |
| One unusable measurement suppresses useful data. | Isolate planned item status and aggregate `ComputeRun` only after all eligible items are attempted. |
| Broad routing creates unbounded or opaque computation. | Use a finite, versioned capability registry with declared inputs, adapters, outputs, and figures. |
| Migration changes retained DSC results. | Protect Mettler PA6 behavior with regression tests and run the six-sample benchmark before deletion. |
| Research/paper logic again blocks computation. | Keep interpretation, evidence, RAG, ARS, and Joint outside conversion and deterministic capability execution. |

## Approval and review boundary

This is an approved architecture record, not an implementation or scientific
method change. It authorizes separate, reviewable migration tasks in the stated
order. No real data is committed, no legacy module is removed now, and human
architecture review remains required before merge.
