# Scientific Release Confirmation Boundaries Design

Date: 2026-07-29
Status: high-level design approved by the user; conservative reviewer
dispositions recorded on 2026-07-30
Task: `docs/agent/tasks/2026-07-29-scientific-release-confirmation-boundaries.md`

## Goal

Define the reviewer-owned scientific decisions that sit between the existing
IR/NMR/Joint software contracts and a publication-ready release decision. The
design must preserve every raw result, evidence item, FigureDefinition,
manifest, export, and history record while preventing unconfirmed scientific
semantics from being promoted.

## Non-goals

- Do not infer an IR vendor coordinate convention, spectral meaning, or ROI
  rule from array shape or file order.
- Do not infer NMR solid-C peak assignments or promote Xc from proximity,
  model output, or an unapproved library.
- Do not resolve Joint conflicts by majority vote or overwrite a source
  technique's result.
- Do not change scientific thresholds, formulas, real datasets, or current
  publication roles before the reviewer record is supplied and validated.

## Existing contracts this design preserves

| Boundary | Existing contract | Design consequence |
| --- | --- | --- |
| IR mapping | `IRMappingResult` validates 2D values, explicit row/column coordinates, boolean invalid-pixel mask, unique ROI IDs, finite spectra, and `provenance.source_id`. | The decision record adds interpretation and promotion metadata; it does not reinterpret the arrays. |
| IR figures | `ir.mapping.roi` is Main, `ir.mapping.spectra` is SI, and `ir.mapping.invalid-pixels` is diagnostic. | Roles remain conservative until coordinate/ROI semantics are accepted. |
| NMR evidence | `Xc_assignment_status` distinguishes `supported`, `assignment_limited`, and missing assignment evidence; constraint symptoms already explain why assignment is required. | The reviewer record is the authority for an approved assignment source and the conditions for promotion. |
| Joint hub | Joint rows retain per-technique runs, provenance, validation severity, technique confidence, and `paper_conclusion_ready_by_technique`. | Conflict policy consumes these fields and preserves each source result. |
| Shared lifecycle | Results Workbench, FigurePipeline, Manifest/Gallery, Editor, export, and History already carry provenance. | A decision record travels as provenance/review state; it is not a GUI-only flag. |

## Decision record

The future implementation will use one immutable, JSON-safe reviewer record per
scientific scope. It contains:

- `record_id`, `scope`, `reviewer`, `reviewed_at`, `source_refs`, and
  `policy_version`;
- `ir_mapping`: vendor/source identity, coordinate order, origin, direction,
  units, ROI inclusion rule, invalid-pixel policy, and Main/SI/diagnostic
  promotion rule;
- `nmr_solid_c`: assignment source/truth-set identity, ambiguity label policy,
  solvent/overlap handling, phase-assignment requirements, and Xc promotion
  conditions;
- `joint`: conflict precedence, minimum evidence level for a conclusion,
  unresolved-conflict status, and the required conclusion class;
- `release`: `approve`, `conditional`, or `reject`, reviewer/date, and linked
  conditions or follow-up task IDs.

The record is incomplete until all fields relevant to the selected scope are
present. An incomplete record is valid input to the review workflow but cannot
change a diagnostic, assignment-limited, or conditional publication role.

## Conservative state flow

```text
analysis result
    -> structural validation and evidence
    -> review_required / assignment_limited when policy is absent
    -> reviewer decision record
    -> policy validation against source/provenance
    -> accepted or conditional review state
    -> role-specific Figure/Manifest/Gallery/Editor/export/History surfaces
```

The decision record never changes numeric analysis output. It only authorizes a
promotion boundary after the source references and reviewer identity are
consistent with the run being promoted. Replaying or restoring an older run
must restore the decision record and its policy version, or fall back to the
older conservative state.

## Mode-specific rules

### IR mapping

The reader/adapter remains responsible for supplying interpreted coordinates;
the reviewer record states what those coordinates mean. Missing or conflicting
coordinate semantics keep the map and ROI spectra diagnostic/SI as currently
defined. Invalid cells stay masked; no interpolation is introduced by the
release policy.

### NMR solid-C

Only an approved assignment source can support named peaks. Ambiguous peaks
remain explicitly ambiguous. Xc may leave `assignment_limited` only when the
reviewer-approved crystalline/amorphous assignment requirement, signal/fit
quality requirements, and source-run provenance all hold. Otherwise existing
warnings and diagnostic figures remain authoritative.

### Joint

Joint keeps source values and conflict rows side by side. The policy may rank
evidence classes, but it cannot erase a disagreement. An unresolved conflict
at or above the reviewer-selected severity keeps the Joint conclusion
diagnostic or conditional and prevents `paper_conclusion_ready` from being
reported as true for the affected conclusion.

## Review and GUI flow

The reviewer inspects the canonical GUI at normal display size, then reviews
the decision fields against the real run/source references. Results, Gallery,
History, Editor, and fallback Export must show the same record ID and policy
version. Screenshots are visual evidence only; the signed decision record is
the authority for scientific promotion.

## Failure and fallback behavior

- Missing record: analysis remains available; publication promotion is denied.
- Malformed record: surface a review error and preserve the prior conservative
  role; do not partially apply fields.
- Source/provenance mismatch: mark the decision stale and keep the run
  diagnostic/assignment-limited.
- Export without an accepted record: include the review state and reason in
  provenance; never fabricate an approval.
- AI-off, AI-failure, and fallback paths do not bypass the record.

## Verification strategy

The implementation plan adds focused tests for JSON-safe round-trip,
missing/malformed/stale records, per-mode promotion gates, shared lifecycle
propagation, History restore, and fallback export. Existing IR mapping,
NMR-evidence, Joint, Workbench, and real published-run matrices remain
regression gates. The current reviewer decision deliberately supplies
conservative dispositions, not scientific promotion values: no native IR map
means diagnostic-only, no NMR assignment truth set means assignment-limited,
and unresolved Joint conflicts remain diagnostic-only. Any future promotion
value still requires a source-linked reviewer record and its own focused task.

## Alternatives considered

1. **GUI-only reviewer checkbox** — rejected because export, History, and
   non-GUI consumers could lose the decision or apply it inconsistently.
2. **Hard-code conservative rules without a reviewer record** — rejected
   because vendor semantics and assignment policy are scientific decisions that
   must be auditable and revisable.
3. **Automatic confidence/majority promotion** — rejected because it would
   turn indirect evidence into an unsupported scientific conclusion.

## Acceptance boundary

This design now records the conservative decision workflow and its current
reviewer dispositions. It does not close the overall release goal: source-
specific payloads, remaining visual gates, SAXS, and any future promotion
values still require separate evidence and verification.
