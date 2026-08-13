# Cross-Technique Project Evidence Index Acceptance

Date: 2026-08-14

The AI-facing `analyze-project` route now exposes a package-level
`techniques.json` index for explicitly selected multi-technique runs. The index
maps each technique to its run IDs, evidence count, statuses, and provider
limitations. It is a transport/indexing surface only: it does not infer sample,
batch, formulation, or cross-technique scientific identity.

The focused smoke used one FTIR CSV and one WAXS file in the same project,
executed both selected routes, and materialized one evidence package containing
both techniques and the existing explicit membership relation.

Verification: `15 passed` for the AI-native entrypoint and package matrix.
