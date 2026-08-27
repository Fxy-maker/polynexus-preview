# Package Context and ARS Consistency

Persisted run manifests already contain explicit request parameters used by
Codex/ARS to define groups. The package builder will collect the
`approved_context_corrections` and related status/approver fields, deduplicate
identical entries, and store them in the package manifest. The ARS handoff will
copy them under `project_context` with `source: user_or_ai_context` and
`is_instrument_fact: false`. This is additive and does not alter scientific
metric gates.
