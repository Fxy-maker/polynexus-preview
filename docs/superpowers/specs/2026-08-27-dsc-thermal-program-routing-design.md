# DSC thermal_program.v1 routing design

## Goal

Use the existing `thermal_program.v1` canonical template as the single DSC
container for heating, cooling, and isothermal segments, then route each role
to the existing deterministic calculations in one `ComputeRun`.

## Non-goals

- Do not create a second DSC parser or duplicate the legacy engine.
- Do not relax quality gates for Avrami or thermal-event fitting.
- Do not invent mass-normalized enthalpy when the source does not provide sample mass.
- Do not remove the compatibility name `run_isothermal_template`.

## Architecture

The converter will parse the Mettler text once, recover sample mass when present,
and emit a `thermal_program.v1` payload containing role-tagged segments. Stable
holds retain `isothermal_crystallization`; monotonic ramps are emitted as
`heating` or `cooling` with source ranges, rate, and arrays. The public DSC
executor `run_thermal_program_template` validates and dispatches those segments
to `analyze_scan` and existing kinetics functions. The old method delegates to
the new method and remains valid for templates containing only isothermal holds.

The output remains a legacy-shaped result projection so ComputeRun, CLI, GUI,
and evidence packaging continue to consume the same object. Parameters include
per-segment thermal results, isothermal Avrami series, and non-isothermal
kinetics when enough cooling curves are available. Missing mass produces a
review warning and leaves mass-dependent values non-public rather than
fabricating them.

## Acceptance criteria

1. A thermal-cycle text export converts to `thermal_program.v1` with at least
   one heating or cooling segment and preserves source ranges.
2. A template containing mixed heating/cooling/isothermal roles executes in one
   call and returns role-specific parameters without rejecting supported roles.
3. Existing isothermal-only tests and the compatibility method remain green.
4. ComputeRun uses the unified method when available and preserves provenance.
5. A missing sample mass is reported explicitly and never converted into a
   fabricated J/g value.

## Verification

Run the focused DSC/template/compute tests, then:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-27-dsc-thermal-program-routing.md --changed --types
```
