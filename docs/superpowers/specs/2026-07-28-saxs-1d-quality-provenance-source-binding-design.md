# SAXS 1D quality provenance source binding design

## Context

The SAXS 1D quality report now records deterministic sanitization actions, and
static/temperature/strain consumers already transport the report. The core
`analyze_single()` boundary still has no way to identify which loaded frame
produced a report, so a review of a repaired profile can lose the link back to
the source file.

## Design

Extend `analyze_single()` with optional `source_id` and `raw_data_ref`
arguments. These values are passed unchanged into the existing
`DataQualityReport`; omitted values remain empty. The logical source ID used by
the high-level SAXS engine is `frame-{index}` where `index` is the original
loaded-frame position. The physical reference is the corresponding `_file_list`
entry. A source is bound only when a non-empty file reference exists; no source
ID or path is fabricated for an unbound frame.

The direct temperature and strain series APIs accept optional aligned
`source_ids` and `raw_data_refs` sequences. Temperature sorts conditions but
passes the original input index to `analyze_single()`, preserving the existing
`TemperaturePointResult.source_index` mapping. Strain remains positional. A
source sequence with the wrong length is treated as unavailable for that
sequence, preventing accidental positional misbinding.

The `SAXSEngine` passes the same source mapping through its static,
temperature, and strain paths, including public `analyze_temperature()` and
`analyze_strain()` calls and single-file static analysis. Existing report
fields, sanitization actions, DataFrame/CSV/Workbench projections, and figure
evidence receive the same report object through their current copy paths.

## Non-goals

- No numerical algorithm, smoothing, fitting, threshold, quality level, or
  physical gate changes.
- No interpolation, frame repair, source guessing, or source-path rewriting.
- No new GUI-specific provenance logic; consumers continue to use report DTOs.
- No change to detector/orientation provenance or figure source IDs.

## Acceptance criteria

- `analyze_single()` records explicitly supplied source ID and raw reference.
- Static, temperature, and strain engine paths bind report provenance to the
  corresponding frame/file, including temperature frames after sorting.
- Missing or length-mismatched source metadata remains empty and does not bind
  a neighboring frame.
- Existing report actions and quality levels remain unchanged and continue to
  reach Workbench, DataFrame/CSV, History, Export, and Figure provenance.
- Focused RED/GREEN tests, SAXS matrix, task verifier, diff check, and an
  explicit allowlist checkpoint are recorded.

## Affected boundaries

- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `polynexus/core/saxs.py`
- focused SAXS provenance tests and durable agent memory
