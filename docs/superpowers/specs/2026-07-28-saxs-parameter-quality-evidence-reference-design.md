# SAXS Parameter Quality-Evidence Reference Design

## Goal

Make every exported SAXS parameter table row traceable to the authoritative
`quality_evidence.json` file without duplicating AI rescue or quality payloads
into CSV.

## Context and decision

The existing engine-parameter payload is already copied into `AnalysisResult`,
and GUI History persists that payload together with the full result. The full
SAXS AI audit is already owned by `quality_evidence.json`. The remaining
traceability gap is that `data/parameters.csv`, when consumed by itself, does
not identify that authoritative evidence file.

Add two read-only references at the bundle boundary:

- `parameters.json["quality_evidence_file"] = "quality_evidence.json"`;
- every row in `data/parameters.csv` gets
  `quality_evidence_ref = "../quality_evidence.json"`.

The CSV value is a relative path from `data/parameters.csv`; it is a pointer,
not a copy of the audit. Existing parameter columns and row ordering remain
unchanged.

## Non-goals

- No AI call, candidate application, rerun, interpolation, or frame repair.
- No new physical, quality, or publication threshold.
- No candidate configuration, raw q/I, detector array, or audit duplication in
  CSV.
- No History schema or GUI behavior change; the audit confirmed those paths are
  already complete.
- No changes to `quality_evidence.json` ownership or contents.

## Invariants

- The reference is present only for a successful bundle with parameter rows.
- The reference is deterministic and relative to the CSV location.
- Parameter values, row count, source order, and existing JSON audit content are
  unchanged.
- Missing or non-mapping parameter rows still serialize safely.
- The reference never implies that an AI candidate was accepted, applied, or
  physically valid.

## Verification boundary

Tests cover the bundle JSON/CSV reference, preservation of existing AI audit
content, safe mixed rows, exact SAXS tests, the task-scoped verifier, and diff
whitespace. Full/boundary verification is reported only if it completes in this
task.
