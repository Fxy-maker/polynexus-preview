# Release State Evidence Reconciliation Design

## Goal

Refresh one repository-grounded release-state snapshot after the latest
non-SAXS and parallel SAXS evidence, while preserving the conditional
scientific-release decision.

## Scope

- index the latest task cards and acceptance records;
- separate automated lifecycle, structural/visual, scientific, and owner
  approval evidence;
- state the safe publication consequence for IR mapping, NMR solid-C, Joint,
  SAXS, and the shared GUI.

## Non-goals

- no algorithm, threshold, quality, physical-gate, Figure, Manifest, Export,
  or publication-role changes;
- no invention of vendor coordinates, ROI bounds, NMR assignments, ppm
  calibration, or Joint conflict precedence;
- no data deletion, test-storage apply, GUI deployment, or external message;
- no modification of parallel SAXS source, test, or memory files.

## Decision boundary

The release state remains `conditional`. Existing fail-closed classifications
are authoritative: missing source-specific scientific evidence stays
diagnostic-only or assignment-limited, and a timeout or incomplete test is
never promoted to a pass.
