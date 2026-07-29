# IR Mapping Scientific Review Gate

## Goal

Apply the accepted scientific default for `ir.mapping`: consume row/column
coordinates exactly as supplied, require explicit ROI payloads, preserve
invalid pixels as a mask, and keep all mapping publication roles diagnostic
until an accepted, source-matching scientific review record is present.

## Non-goals

- Do not add a vendor file reader or infer coordinate orientation.
- Do not transpose, flip, interpolate, or fill invalid pixels.
- Do not move technique-specific interpretation into GUI code.
- Do not change standard IR or temperature-2D numerical analysis.

## Affected boundaries

- `polynexus/core/ir_engine/ir_mapping.py`: deserialize the optional review
  record from mapping provenance, calculate the fail-closed promotion decision,
  and write a JSON-safe decision snapshot into evidence and figure recipes.
- `polynexus/core/ir.py`: preserve the mapping review decision in the shared
  `AnalysisResult` metadata/evidence handoff.
- `tests/test_ir_mapping.py`: regression coverage for pending, accepted,
  source mismatch, and JSON round-trip behavior.
- `docs/acceptance/2026-07-29-ir-mapping-scientific-review-gate.md`: evidence
  and known limitations.

## Scientific acceptance criteria

1. No review record, a pending record, an invalid record, or a source mismatch
   produces `diagnostic` roles for `ir.mapping.roi` and
   `ir.mapping.spectra`; `ir.mapping.invalid-pixels` stays diagnostic.
2. An accepted record with scope `ir.mapping`, source matching the mapping
   `source_id`, reviewer metadata, policy version, and all required decisions
   promotes only the scalar map to `main` and ROI spectra to `si`.
3. Coordinate arrays and invalid-pixel values remain unchanged; no scientific
   inference or interpolation is introduced.
4. The persisted decision is JSON-safe, includes reason/record/scope/source,
   and survives figure recipe and AnalysisResult evidence serialization.
5. Existing IR provider and lifecycle tests remain green.

## Verification

```powershell
python -m pytest -q tests/test_ir_mapping.py tests/test_scientific_review.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-ir-mapping-scientific-review-gate.md --changed --types
python scripts/verify.py --changed --types --full --boundary
```

## Checkpoint allowlist

The atomic checkpoint may include only the implementation/test/task/acceptance
files listed above plus the dedicated plan and any durable memory file whose
scientific state actually changed.
