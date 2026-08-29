# PolyNexus Research Suite Runtime and Skill Installation Design

**Date:** 2026-08-29
**Status:** Approved for implementation planning
**Scope:** Suite runtime discovery, optional skill installation/update, and evidence handoff

## Goal

Make PolyNexus present as one research suite that can install and manage its
Codex/ARS companion skills while keeping deterministic analysis in PolyNexus
Core and preserving a stable, versioned handoff to writing workflows.

## Non-goals

- Do not embed ARS source code, prompts, hooks, or model clients in Core.
- Do not make ARS, Codex, network access, or Chroma/RAG a required dependency for
  ordinary analysis.
- Do not recalculate scientific values in the adapter or in a skill.
- Do not silently install, update, upload, push, merge, or deploy anything.
- Do not change the existing project/run/chart/evidence object contracts in this
  slice.
- Do not force migration of existing evidence packages.

## Product shape

```text
PolyNexus Research Suite
├─ Core                 deterministic conversion, analysis, plots, evidence
├─ Suite Manager        discovery, install, update, lock, rollback
├─ Codex Adapter         capability detection and evidence handoff
└─ Optional Skills       ARS, Results Writer, Discussion Writer, review skills
```

The UI and CLI may expose one Suite experience, but each layer keeps one clear
ownership boundary. Core remains usable when Codex or ARS is absent.

## Components and contracts

### Suite manifest

Ship a repository-owned manifest describing supported companion components and
their compatibility range. The manifest is data, not executable installer code.
Each component entry contains:

- stable component id and display name;
- exact source URL or local-package contract;
- pinned version/ref;
- destination skill directory name;
- expected required files and optional files;
- SHA-256 hashes for the downloaded archive or file set;
- compatible Core/adapter/evidence-schema ranges.

The manifest itself has a schema version and is validated before use.

### Local lock

After a successful install or update, write `suite-lock.json` under the user's
PolyNexus configuration directory (never inside raw project data). It records:

- manifest version and timestamp;
- Core version;
- adapter version;
- evidence/handoff schema versions;
- installed component versions, source, and content hash;
- previous lock/backup location when an update occurred.

The lock is diagnostic and reproducibility metadata; it is not a second analysis
state or a replacement for project/run provenance.

### Suite Manager service

Expose a small, headless service used by both CLI and GUI:

- `doctor()` — detect Codex directory, installed components, versions, hashes,
  compatibility, and actionable missing prerequisites;
- `install(component_id, source_override=None, confirm=...)` — stage, validate,
  and activate a pinned component only after explicit confirmation;
- `update(component_id=None, ...)` — update one or all manifest components using
  the same staged activation path;
- `rollback(component_id=None)` — restore the last known-good backup;
- `lock()` — return the current lock projection;
- `handoff(package_path)` — validate an evidence package and return a compact,
  package-relative ARS handoff descriptor.

The service returns JSON-safe DTOs with status, reasons, paths, versions, and
next actions. It never imports or executes arbitrary skill code during doctor or
validation.

### Installation transaction

Installation and update use a recoverable transaction:

1. Resolve `%CODEX_HOME%` or the documented default Codex directory.
2. Check the source and show the component/version/destination to the user.
3. Download or copy into a unique staging directory.
4. Validate archive/file hashes, required files, manifest metadata, and path
   containment.
5. Run a local smoke check that only inspects the skill router and metadata; it
   must not call a model or upload user content.
6. Move the current installed directory to a timestamped backup.
7. Activate the staged directory and write `suite-lock.json` atomically.
8. If any activation or lock write fails, restore the backup and report the
   failure without deleting the user's previous installation.

Only explicit user confirmation permits network access and filesystem writes.
Offline packages use the same validation and activation path.

### Compatibility policy

Compatibility is evaluated using declared ranges for Core, adapter, and handoff
schema. A mismatch blocks activation of the new component but leaves the current
installation available. Existing evidence packages remain readable when their
schema is supported; no automatic rewrite is performed.

### Evidence handoff

`handoff(package_path)` validates the existing package and returns references to:

- `ars-writing-input.json`;
- `result-tables.json`;
- `writing-evidence.json`;
- `citation-metrics.json`;
- `review-decision.json` when present.

The descriptor contains package-relative paths, schema versions, package status,
and human-review requirements. It does not duplicate metric objects or promote
diagnostic values. ARS or another writing skill consumes this descriptor and the
shared files.

## User-facing entry points

CLI commands:

```text
polynexus suite doctor
polynexus suite install-ars
polynexus suite update [--component ID]
polynexus suite rollback [--component ID]
polynexus suite handoff --package PATH
```

The GUI may later expose the same operations through a Suite settings panel. It
must call the service DTOs and must not implement a second installer.

## Error and safety behavior

- Missing Codex directory: report `codex_not_found` and show manual setup steps.
- Missing ARS: report `component_missing`; Core remains fully usable.
- Network/source failure: report `source_unavailable`; offer a local package.
- Hash or required-file mismatch: discard only the staging directory and report
  `integrity_check_failed`.
- Compatibility mismatch: report `incompatible_component`; keep the old version.
- Activation failure: restore backup and report `activation_rolled_back`.
- Invalid handoff package: report `evidence_package_invalid`; do not invoke ARS.

All errors are deterministic, JSON-safe, and free of secrets or credential-bearing
URLs.

## Testing strategy

- Unit tests for manifest parsing, path containment, hash validation, lock
  serialization, compatibility decisions, and transaction rollback.
- CLI tests proving doctor/install/update/rollback/handoff use the service.
- GUI adapter smoke tests proving it consumes the same DTOs (no provider logic).
- Offline installation tests using a local fixture package; no live network or
  model calls in automated tests.
- Cross-entry handoff tests using the existing PA6 evidence package contract.

## Acceptance criteria

1. A clean machine can inspect Suite status without ARS installed.
2. An explicitly confirmed pinned ARS package installs into the Codex skills
   directory and creates a lock record.
3. Corrupt, incompatible, or failed updates leave the previous installation
   usable and produce an actionable reason code.
4. The same service DTOs are consumed by CLI and GUI entry points.
5. A valid evidence package yields a package-relative ARS handoff descriptor
   without copying or recomputing scientific values.
6. Existing Core analysis and evidence-package behavior remains unchanged.

## Open review boundaries

- The official ARS distribution URL and licensing terms must be confirmed before
  shipping a network installer.
- Human review remains mandatory for scientific interpretation and manuscript
  promotion; Suite installation cannot alter those decisions.
- Release-wide historical test failures remain a separate release boundary.
