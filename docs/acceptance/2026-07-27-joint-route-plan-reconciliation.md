# Joint Route Plan Reconciliation — 2026-07-27

The stale Phase 7 note saying that `joint.compare` still needed to consume the
shared figure entrypoint is no longer accurate. Current code routes
`JointHubWorker` through `JointCoordinator.publish_hub_report()`, which
publishes the three shared FigureDefinition entries and preserves the run
context used by Workbench, Gallery/Editor, export, and History restore.

The current focused matrix passed `14` tests. This closes only the automated
route/provenance boundary. Cross-technique consistency, conflict semantics,
real-data behavior, restarted-GUI review, and final release approval remain
open.

Evidence and the precise allowlist are tracked in
`docs/agent/tasks/2026-07-27-joint-route-plan-reconciliation.md`.
