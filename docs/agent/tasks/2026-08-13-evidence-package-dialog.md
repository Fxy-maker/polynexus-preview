---
task_id: 2026-08-13-evidence-package-dialog
kind: architecture
status: in_progress
date: 2026-08-13
title: Read-only evidence package GUI dialog
---

# Evidence Package Dialog

## Goal

Provide a usable read-only Qt dialog for an `EvidencePackageView` so a user
can inspect package status, technique scope, provenance metrics, assets, and
mandatory review actions.

## Non-goals

- Do not invoke analysis, write package files, select figures, or edit claims.
- Do not branch on DSC/FTIR/SAXS/WAXS internal algorithm payloads.

## Affected boundaries

- `polynexus/gui/evidence_package_view.py`: technique-neutral visual surface.
- Focused Qt test, acceptance record, durable memory, and local checkpoint.

## Acceptance criteria

- [ ] Dialog renders overview, evidence, metrics, and review tabs from DTOs.
- [ ] Metric rows show value/unit/method/source/eligibility and reason codes.
- [ ] Review actions and package-level limitations remain visible.
- [ ] The surface is read-only and accepts no provider internal data.
- [ ] A real PA6 package opens with all four techniques.

## Implementation plan

1. Add a failing Qt dialog test using the existing synthetic DTO fixture.
2. Implement the panel with only `EvidencePackageView` records.
3. Open a real PA6 package, record acceptance, run verification, checkpoint.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_evidence_package_view.py
python scripts/verify.py --task docs/agent/tasks/2026-08-13-evidence-package-dialog.md --changed --types
git diff --check
```
