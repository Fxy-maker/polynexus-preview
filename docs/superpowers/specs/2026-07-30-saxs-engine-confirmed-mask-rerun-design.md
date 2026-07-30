# SAXS Engine Confirmed Mask Rerun Design

## Goal

Connect the existing confirmed SAXS detector-mask candidate contract to the
normal `SAXSEngine` and GUI worker pipeline so a later editor can request a
deterministic static-image rerun without bypassing existing quality or
physical gates.

## Scope

This slice transports one optional mask candidate through a complete static
image pipeline. `SAXSEngine.run_pipeline(..., mask_edit_candidate=...)` holds
the candidate only for that invocation, and `preprocess()` passes it to the
existing `preprocess_pipeline()` boundary. `AnalysisWorker` forwards the
optional keyword only when a candidate is supplied, preserving compatibility
with other technique engines and existing worker fakes.

Only a single image input is eligible for this transport. A candidate is not
applied during `skip_to="plot"`, 1D profile processing, directory loading, or
temperature/strain sequence analysis. Those routes remain unchanged until a
separate per-frame candidate transaction is designed.

## Safety Contract

- The candidate is read-only input to the run and is never written back.
- The engine clears its transient candidate reference after the run, including
  pipeline failure, so a later run cannot inherit an earlier edit.
- Pending, malformed, stale, and unconfirmed candidates still fail closed in
  the existing preprocessing contract and remain provenance-only/no-op.
- Confirmed candidates use the existing copied-mask application and detector
  quality report. Existing physical, data-quality, sequence, and publication
  gates remain authoritative.
- No GUI editor, automatic mask inference, interpolation, morphology, AI call,
  new threshold, or automatic rescue is introduced here.

## Verification

The focused regression must prove candidate forwarding through the engine and
worker, transient-state cleanup, and no candidate application in plot-only
reruns. The task verifier and complete current SAXS matrix are required before
the explicit allowlist checkpoint. Storage inspection remains report/dry-run;
no `--apply` is part of this task.
