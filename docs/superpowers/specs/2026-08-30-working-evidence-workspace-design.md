# Current evidence workspace design

The project gains a mutable `working.json` index under `.polynexus/evidence`.
It stores only validated run IDs, manifest paths, source artifact IDs/hashes,
techniques, and statuses. Upsert is keyed by source artifact ID, so rerunning a
corrected file replaces the prior working entry rather than creating a second
current result. Existing immutable package directories are never edited.

`ProjectWorkflowService` exposes `upsert_working_run`,
`working_evidence_status`, and `freeze_working_evidence`. The first two update or
read the index only; the last loads the referenced validated run manifests and
delegates to the existing `ProjectEvidencePackager`, producing the next package
version only when explicitly requested. Invalid, blocked, missing, or stale run
manifests are rejected before freezing.

This keeps the public run/evidence contracts shared by CLI, AI, and GUI while
making routine data additions cheap. The current package remains an auditable
snapshot; the working index is the mutable draft frontier.
