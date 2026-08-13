# ARS Writing Evidence Handoff Acceptance

Date: 2026-08-14

Project evidence packages now expose `writing-evidence.json` plus a structured
“Writing evidence by technique” section in `writing-input.md`. The handoff
groups existing provider evidence by technique and preserves source run IDs,
source hashes, figures, tables, supported interpretations, disallowed
conclusions, observed results, and limitations.

This is a writing input contract, not an automatic Results/Discussion writer.
ARS or a writing skill must still choose the narrative, calibrate claims, and
request human review where evidence remains review-bound.

The real PA6 FTIR+WAXS package can now be consumed without scanning raw run
manifests: `techniques.json` provides the index and `writing-evidence.json`
provides the evidence map.

Verification: AI-native/package matrix and structured gates are recorded with
the associated checkpoint commit.
