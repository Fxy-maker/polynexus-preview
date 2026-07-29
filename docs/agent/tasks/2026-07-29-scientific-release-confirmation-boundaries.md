---
task_id: 2026-07-29-scientific-release-confirmation-boundaries
kind: scientific-semantics
status: awaiting-review
date: 2026-07-29
title: Define reviewer-owned IR, NMR solid-C, Joint, and release boundaries
---

# Scientific release confirmation boundaries

## Goal

Turn the remaining IR, NMR solid-C, Joint, and final release questions into a
reviewer-owned, provenance-linked decision contract without guessing scientific
semantics or changing current result roles.

## Non-goals

- No vendor reader, coordinate transform, ROI interpolation, assignment
  inference, conflict threshold, formula, or publication promotion is changed
  in this documentation task.
- No real dataset, generated output, scratch directory, or runtime state is
  modified.

## Affected boundaries

- `polynexus/core/ir_engine/ir_mapping.py` structural mapping/ROI contract.
- `polynexus/core/analysis_evidence_nmr.py` and NMR assignment evidence.
- `polynexus/core/joint/dataset.py` Joint confidence and conflict rows.
- Shared Figure/Manifest/Gallery/Editor/export/History provenance.
- Release decision packet and durable agent memory.

## Design and evidence

- Design: `docs/superpowers/specs/2026-07-29-scientific-release-confirmation-boundaries-design.md`
- Existing release packet: `docs/agent/tasks/2026-07-29-release-decision-packet.md`
- IR reconciliation: `docs/acceptance/2026-07-28-ir-release-evidence-reconciliation.md`
- NMR reconciliation: `docs/acceptance/2026-07-28-nmr-release-evidence-reconciliation.md`
- Joint reconciliation: `docs/acceptance/2026-07-28-joint-evidence-weighted-conflicts.md`

## Implementation plan

1. Record the reviewer-owned decision fields and conservative fail-closed
   behavior in the design and acceptance documents.
2. Keep the existing IR, NMR, Joint, Figure, Manifest, export, and History
   contracts unchanged while the scientific values are pending.
3. After the reviewer supplies values, create separate value-specific task
   cards for IR, NMR solid-C, Joint, and the release decision; each card must
   include a focused regression and an explicit changed-file allowlist.
4. Verify each value-specific implementation with the task verifier, focused
   lifecycle matrix, full/boundary evidence where applicable, and an updated
   acceptance note before any release promotion.

## Acceptance criteria

- [x] Reviewer fields are explicitly defined for IR coordinate/ROI semantics.
- [x] Reviewer fields are explicitly defined for NMR solid-C assignment and
      Xc promotion.
- [x] Reviewer fields are explicitly defined for Joint conflict precedence and
      conclusion class.
- [x] Final release decision fields and linked conditions are explicit.
- [x] Conservative defaults preserve current diagnostic/assignment-limited
      behavior when the record is absent or invalid.
- [x] The design states how the decision must travel through shared lifecycle
      provenance, History restore, and fallback export.
- [ ] Reviewer supplies the scientific values for the selected real sources.
- [ ] Follow-up implementation task cards are created after the reviewer
      values are fixed.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-scientific-release-confirmation-boundaries.md --changed --types
python scripts/boundary_audit.py --root D:\PolyNexus --json
git diff --check
```

## Explicit changed-file allowlist

- `docs/superpowers/specs/2026-07-29-scientific-release-confirmation-boundaries-design.md`
- `docs/agent/tasks/2026-07-29-scientific-release-confirmation-boundaries.md`
- `docs/acceptance/2026-07-29-scientific-release-confirmation-boundaries.md`
- `docs/agent/memory/active-work.md`
