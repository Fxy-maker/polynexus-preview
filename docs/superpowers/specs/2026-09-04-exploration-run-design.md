# ExplorationRun foundation design

## Purpose

`ExplorationRun` is the shared Core path for an analysis method that is not
yet a formal PolyNexus capability, including bounded parameter exploration and
a future Codex-proposed method. It preserves the product baseline:

```text
raw artifact -> CanonicalExperiment / source binding -> ExplorationRun
             -> ProviderResultInput / Metric Manifest -> curated EvidenceItem
```

It does not declare an unknown method publication-ready or promote it into the
capability catalog.

## Scope

The first slice provides:

- immutable, content-addressed executor descriptors, requests, and outcomes;
- an explicit in-process callable registry keyed by executor id and version;
- source artifact ID and content-hash binding on each request and returned
  provider result;
- a shared `ProviderResultInput` + metric-manifest output rather than an
  AI-only metric payload;
- complete, needs-input, and failed retained outcomes with a consistent
  `ComputationState`;
- append-only project manifests under
  `.polynexus/research/exploration/`; and
- a completed-run adapter to the existing `EvidenceItem`, always marked
  `review_required`.

## Safety and reproducibility boundary

Only a callable explicitly registered in the current process may run. The
first slice deliberately does not accept code strings, dynamic imports,
subprocesses, network execution, notebooks, or a generic Codex sandbox.

The descriptor attests to an implementation hash. A request repeats the exact
executor ID, version, and implementation hash. The runner will not run if that
binding no longer matches the registry. A result must return a valid shared
`ProviderResultInput` whose technique, source artifact ID, and declared source
content hash match the request.

The run ID is request-derived. A persisted result cannot be overwritten with a
new outcome for the same request; a modified parameter, implementation hash,
or source identity produces a distinct request and run ID.

## State and evidence semantics

`completed` requires a computed provider state and is reprojected with
`promotion=review_required`. `needs_input` and `failed` retain the request,
reason code, and bounded failure metadata but have no provider result. They
are part of project history, not evidence candidates.

A completed run can create an ordinary project `EvidenceItem` containing the
shared provider result and metric manifest. This does not make a scientific
claim. Curating that item into an Evidence Package remains a separate Codex or
user decision.

## Deferred work

- a sandboxed execution model for user/Codex-generated code;
- stop policies and candidate scheduling for broad parameter searches;
- UI and CLI commands to register or choose exploration executors;
- direct inclusion of exploration runs in `ProjectEvidencePackager`;
- a formal custom-code review/capability-promotion lifecycle.

These require separate architecture, security, and scientific-semantics
review. They are intentionally not hidden behind this initial data model.
