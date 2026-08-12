# Project Workflow Recovery V4 Design

`ProjectWorkflowService.resume(run_id)` loads a persisted non-blocked run,
request, and plan, verifies their hashes and all source hashes, then delegates
to the existing deterministic run path. A retry never changes source bytes and
uses the same request/plan identity.

`ProjectWorkflowService.approve_context_correction(request, corrections)`
requires a non-empty mapping and the explicit `approved=True` marker. It
returns a new request whose `parameters.approved_context_corrections` records
the correction and approver string. Inventory facts remain untouched; package
writing input can cite the request provenance.
