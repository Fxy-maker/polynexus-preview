# IR Thermo/OMNIC Mapping Semantics

## Goal

Expose the Thermo Scientific OMNIC Picta official mapping coordinate and ROI
rules in the existing IR mapping evidence and figure recipes, while clearly
marking sample-level metadata as unverified because this workspace has no
vendor-native 2D mapping project file.

## Non-goals

- No vendor-native mapping reader.
- No inferred row-major/column-major scan order.
- No inferred sample ROI bounds or pixel calibration.
- No change to scientific review promotion rules.

## Affected boundaries

- Core: official mapping semantics profile and `IRMappingResult` evidence/
  figure recipe handoff.
- Tests: IR mapping contract/provider regression coverage.
- Docs: design, acceptance, and task evidence.

## Acceptance criteria

- [x] Mapping evidence and every mapping figure recipe contain the same official
  Thermo/OMNIC Picta profile.
- [x] Map axes identify X columns and Y rows as stage positions in `um`, with
  origin `(0, 0)` at stage home.
- [x] Serialization order and sample ROI calibration remain explicitly unknown.
- [x] Missing scientific review still leaves map and ROI figures diagnostic.

## Implementation plan

1. Add a JSON-safe official Thermo/OMNIC Picta semantics profile.
2. Publish the profile through mapping evidence, figure recipes, source units,
   and map axis labels without changing numeric payloads or review gating.
3. Add focused RED/GREEN tests and acceptance evidence.
4. Run the task verifier, diff check, and one explicit allowlist checkpoint.

## Verification

```powershell
python -m pytest tests/test_ir_mapping.py tests/test_ir_lifecycle_closure.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-30-ir-thermo-mapping-semantics.md --changed --types
```

## Evidence source

Thermo Fisher Scientific, `OMNIC Picta User Guide` 269-257900 Rev A:

- map categories and stage mapping overview: printed page 3;
- origin/home `(0, 0)`: printed page 28;
- area-map X columns and Y rows: printed page 44;
- X/Y step size and grid adjustment: printed pages 34-35 and 45;
- area-map X/Y physical positions: printed page 73;
- map collection/processing metadata: printed page 79.

## Explicit changed-file allowlist

- `polynexus/core/ir_engine/__init__.py`
- `polynexus/core/ir_engine/ir_mapping.py`
- `tests/test_ir_mapping.py`
- `docs/agent/tasks/2026-07-30-ir-thermo-mapping-semantics.md`
- `docs/superpowers/specs/2026-07-30-ir-thermo-mapping-semantics-design.md`
- `docs/superpowers/plans/2026-07-30-ir-thermo-mapping-semantics.md`
- `docs/acceptance/2026-07-30-ir-thermo-mapping-semantics.md`
- `docs/agent/memory/active-work.md`

The final commit uses the explicit allowlist above and message
`feat(ir): document thermo mapping semantics`.
