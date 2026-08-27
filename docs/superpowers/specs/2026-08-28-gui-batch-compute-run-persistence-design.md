# GUI Batch ComputeRun Persistence

BatchWorker rows carry explicit source and output locators alongside the shared
ComputeRun. On batch completion, a pure persistence helper builds a derived
context per row and calls the existing `persist_analysis_run` contract. Rows
without a ComputeRun remain compatibility-only display rows, so no provenance
is invented.
