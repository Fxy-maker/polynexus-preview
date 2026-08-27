# GUI batch ComputeRun persistence — 2026-08-28

Successful GUI BatchWorker rows now retain source/output locators and their
shared ComputeRun. Batch completion persists each row through the existing
single-run history contract with a derived per-row context. Compatibility-only
rows without a ComputeRun remain display-only.

Focused matrix: **20 passed**. Structured verification and quality gates are
recorded after the checkpoint.
