# Agent directory ComputeRun migration design

Non-DSC directory artifacts are already source-hashed by `InputArtifact`, but
the workflow currently bypasses `ComputeRunService` and returns a provider
result directly. The directory path will instead use a small provider adapter
inside the shared service. The registry emits its existing opaque
`raw-file-envelope.<technique>.v1` canonical template, preserving source
provenance without fabricating 1-D measurements from directory bytes.

For a custom `provider_runner`, the adapter invokes that runner exactly once.
For the default runner, it invokes the selected engine exactly once. In both
cases `ComputeRun` owns the shared artifact, dataset, plan, result, and template
projection. DSC directories remain on the established provider-only path until
the thermal-program converter can represent their multi-file semantics.

No provider algorithm, frame discovery, result fields, or evidence policy is
changed; this is an execution/provenance routing change only.
