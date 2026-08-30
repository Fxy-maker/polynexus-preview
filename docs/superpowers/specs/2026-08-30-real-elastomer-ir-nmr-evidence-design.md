# Real elastomer IR/NMR evidence design

## Context

The real elastomer directory contains six FTIR temperature-series directories
and headerless two-column NMR CSV exports. Existing canonical conversion safely
blocks the NMR CSVs because their first row is numeric and cannot identify the
coordinate and intensity columns. The user has confirmed the file convention:
the first column is chemical shift in ppm and the second column is intensity.

## Design

Extend the existing `MappingProposal` contract with a validated deserializer,
allow registered table converters and replay to receive a proposal, and have
the single-input project adapter carry an optional proposal from its manifest
into the canonical template. Replay derives the proposal from the registered
template, so a recipe remains self-contained and source-hash bound. The public
project workflow passes the proposal through request parameters for one-file
NMR runs; no header is inserted into the raw file.

The evidence build uses one project run per NMR file (explicit liquid/solid and
H/C submodule) and one run per FTIR temperature-series directory. Existing
`ProjectEvidencePackager` remains the sole package writer. All package items
state observed provider output and retain review limitations; no article claim
is generated automatically.

## Alternatives

1. Normalize CSVs by writing temporary headered copies. Rejected because it
   weakens source identity and replay provenance.
2. Infer numeric two-column mappings globally. Rejected because it silently
   changes the canonical safety boundary.
3. Persist the explicit proposal in the canonical template and replay it.
   Chosen because it is minimal, deterministic, and compatible with existing
   evidence contracts.

## Error handling and tests

Invalid proposals remain `needs_input`; missing or mismatched proposals never
reach provider execution. Tests cover proposal round-trip, headerless NMR
conversion, adapter propagation, replay, and a real-file smoke run. Raw data
is read only; generated outputs stay under the project `.polynexus` workspace.
