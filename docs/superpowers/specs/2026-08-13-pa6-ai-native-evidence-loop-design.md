# PA6 AI-Native Evidence Loop Design

## Decision

PolyNexus will be an evidence-computation service for Codex and ARS, not a
second research-agent conversation layer.  Codex or ARS chooses a project
question, selects file groups, and can propose a data interpretation template.
PolyNexus validates that template, reruns deterministic conversion from the
raw artifact, performs the existing technique analysis, and writes an
immutable evidence package.  ARS consumes the package to draft bounded
Results or Discussion input; it does not receive a license to promote a
review-bound observation into a scientific conclusion.

The first success criterion remains one real PA6 project, not support for
every vendor or technique: selected DSC, FTIR, SAXS, and WAXS artifacts must
produce one traceable, review-bounded package containing selected figures,
numeric observations, source hashes, method identities, and writing-ready
claim boundaries.

## Non-goals

- Do not infer that artifacts belong to the same specimen, batch, or
  formulation from filenames or directory placement.
- Do not change technique algorithms, calibrations, or raw artifacts merely
  to make a package look complete.
- Do not let an LLM execute provider calculations, replace deterministic
  conversion, or silently repair malformed files.
- Do not create publication-ready prose, citations, or final figure selection
  without an ARS request and human scientific review.

## Architecture

### 1. Project selection

`analyze-project` remains the AI-facing entrypoint.  It inventories a supplied
scope, returns candidate groups when the scope is ambiguous, and only analyzes
the explicit paths or group IDs selected by Codex/ARS.  The project request
records the question, selected paths, and any user-approved context correction;
it does not record an inferred sample identity as fact.

### 2. Canonical conversion boundary

Every executable single-file technique route is represented by a versioned
`CanonicalExperiment` before it reaches a provider.  A canonical template has:

- a technique-specific template ID and payload schema;
- source artifact identity and a conversion record;
- observed columns/shape, excluded regions, warnings, and reason codes;
- stable content and conversion hashes.

The converter registry is closed: it maps a registered technique/format pair
to one deterministic converter.  An AI-supplied template is only a proposed
template.  PolyNexus reconstructs the template from the indexed raw source and
compares hashes before the provider runs.  Missing, invalid, unsupported, or
mismatched templates block that technique with a specific reason code while
other selected techniques may still produce their own evidence.

DSC's existing `dsc.isothermal.v1` converter becomes one registry entry.
IR, SAXS, and WAXS receive narrow initial templates that preserve their native
arrays or file-derived representation without redefining their analysis
algorithms.  Vendor-specific adapters remain later extensions behind the same
registry contract.

### 3. Deterministic provider execution

The existing engines remain the only calculation path.  Recipe steps carry the
canonical template hash and conversion hash, and replay validates both against
the source artifact hash.  Provider output is normalized only at the public
boundary, where non-finite values remain absent rather than fabricated.

### 4. Evidence and provenance

Evidence is preserved at three levels:

| Level | Purpose | Required links |
| --- | --- | --- |
| Observation | One provider result or derived metric | technique, source run, raw hash, method ID, status |
| Figure/table | A rendered or tabular representation | source observations, source artifacts, selection intent |
| Claim boundary | What ARS may say about an observation | supported wording, prohibited conclusion, limitations, human review need |

Every numeric item intended for writing has a stable metric ID, value and unit,
calculation/method identifier, evidence ID, run ID, raw source hash, and
review status.  Package limitations are package-level only.  Technique and
item limitations are derived solely from their own run/evidence item and must
not inherit unrelated limitations from another technique.

Package relations may state explicit request membership and user-approved
links.  They must distinguish `explicit_package_membership`,
`user_confirmed_context`, and `inferred_from_filename`; only the latter can be
used for candidate selection, never for a scientific cross-technique claim.

### 5. ARS writing handoff

The package publishes a versioned `ars-writing-input.json` in addition to its
audit-friendly JSON and Markdown files.  It provides ARS with an evidence map,
not a manuscript:

- study question and selected evidence scope;
- technique sections with observations, metric provenance, figure/table links,
  and confidence/review status;
- allowed Results wording, Discussion-only interpretations, prohibited claims,
  and mandatory human-review items;
- explicit gaps such as absent calibration, background uncertainty, or
  unresolved grouping identity.

This matches ARS's need for a claim-evidence map while leaving paper
configuration, literature, citations, outline approval, and final peer review
in the ARS workflow.  A consumer may produce a bounded Results/Discussion
draft only when it preserves these gates verbatim.

### 6. GUI

The GUI consumes a technique-neutral evidence-package view model.  It shows
the selected scope, per-technique statuses, selected candidate figures,
numeric provenance, and review boundary.  It must not inspect internal
technique algorithm state.  The GUI does not auto-select a manuscript figure
or clear review requirements.

## Delivery order

1. Register canonical converters and replay validation for IR, SAXS, and WAXS;
   correct technique-scoped provenance and limitations.
2. Add writing-grade metric/provenance and figure-to-observation relations.
3. Publish the ARS handoff contract and exercise it through an ARS
   Results/Discussion preparation route.
4. Add the package view model and GUI evidence-package surface.
5. Run an external, read-only PA6 DSC/FTIR/SAXS/WAXS replay, inspect the
   resulting package, and record acceptance evidence.

Each item is a separate structured task, focused test matrix, verification,
acceptance note, and local checkpoint.  No stage pushes, merges, or modifies
raw inputs.

## Failure boundaries

- A technique converter unavailable for a selected source yields
  `canonical_converter_unregistered`; it cannot fall back to raw direct
  provider execution.
- A canonical replay mismatch yields `canonical_conversion_mismatch`; stale
  artifacts cannot be packaged as current evidence.
- A missing method/unit/value link prevents a numeric observation from being
  offered to ARS as citable writing evidence.
- A review-required run can be packaged, but its writing item remains
  review-required and lists the specific human-review action.
- A cross-technique package can coexist without a cross-technique scientific
  conclusion.  Such a conclusion requires explicit user-confirmed context and
  remains review-bound.

## Verification strategy

Synthetic tests prove registered conversion, replay mismatch blocking,
technique-local limitations, metric provenance completeness, and ARS handoff
validation.  A bounded external PA6 replay proves all four techniques appear
in one package with their own template/method/source links.  Structured
verification and an allowlisted checkpoint follow every atomic task.
