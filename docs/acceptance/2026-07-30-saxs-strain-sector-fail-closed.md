# SAXS strain sector fail-closed acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-28-saxs-strain-sector-fail-closed.md`
Status: focused automated acceptance passed

## Evidence

- Focused 2D/strain/batch matrix returned `69 passed in 1.12s`, exit code `0`,
  with external D: basetemp.
- Malformed nested sector payloads remain fail-closed as JSON-safe Unusable
  orientation evidence, while the strain frame and existing 1D results remain
  present. Valid sector behavior is covered in the same matrix.
- Production behavior was previously checkpointed in `916a8fe`; this follow-up
  records acceptance evidence only.

## Boundary

No sector repair, interpolation, threshold, rescue, or publication promotion is
introduced. Full/boundary evidence and scientific orientation interpretation
remain separate release gates.
