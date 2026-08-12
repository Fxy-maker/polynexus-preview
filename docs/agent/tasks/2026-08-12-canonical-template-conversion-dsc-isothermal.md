---
task_id: 2026-08-12-canonical-template-conversion-dsc-isothermal
kind: architecture
status: completed_review_required
date: 2026-08-12
title: Add canonical experiment templates with PA6 multi-program DSC conversion
---

# Canonical Templates and PA6 DSC Conversion

## Goal

Introduce a reusable, auditable canonical-data boundary for AI-assisted input
conversion, and implement its first real path for a Mettler PA6 DSC export that
contains multiple isothermal crystallisation programs in one source file.

## Non-goals

- Do not copy, edit, or commit the external PA6 raw data.
- Do not call an LLM, use an LLM to generate numeric data, or let an LLM bypass
  template validation.
- Do not change Avrami fitting equations, thresholds, or scientific conclusion
  policy.
- Do not add canonical converters for FTIR, SAXS, WAXS, or NMR in this task.
- Do not alter GUI workflow behavior.

## Affected boundaries

- Canonical experiment models and conversion records under `polynexus/core/`.
- DSC raw-file parsing and an explicit public canonical-isothermal execution
  boundary.
- Agent workflow proposal/run provenance for the TPAE DSC primary step.
- CLI JSON output and exported run evidence; raw inputs remain external.

## Acceptance criteria

- [x] A public canonical template is immutable, JSON-safe, versioned, and has
  an identity hash independent of the raw file representation.
- [x] A conversion record names the source artifact, converter, extracted
  source row/time ranges, mapping evidence, and validation status.
- [x] A Mettler-style single text export with alternating ramps and holds maps
  only stable isothermal crystallisation holds into a DSC canonical template.
- [x] Melt holds, ramps, short/unsteady holds, and incomplete source columns
  remain explicit conversion evidence and cannot silently become Avrami inputs.
- [x] The canonical DSC execution boundary consumes the template and invokes
  existing DSC kinetics analysis without duplicating or changing the algorithm.
- [x] The TPAE workflow accepts one converted DSC source file or a directory
  series only when it can produce a valid `dsc.isothermal.v1` template.
- [x] Focused synthetic regressions cover deterministic conversion, malformed
  data blocking, replay identity, and PA6-style multi-program segmentation.
- [x] An external PA6 read-only smoke replay is recorded outside the repository
  and marked `review_required`; it is not scientific publication acceptance.

## Implementation plan

1. Add immutable JSON-safe canonical experiment and conversion-record contracts.
2. Convert validated Mettler multi-program DSC holds into `dsc.isothermal.v1`.
3. Materialize each accepted template segment into the existing Avrami path.
4. Permit TPAE single-file DSC only when conversion can be replayed identically.
5. Verify synthetic regressions and the external PA6 read-only replay.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_canonical_experiment_templates.py tests/test_dsc_canonical_isothermal_conversion.py tests/test_tpae_golden_workflow.py tests/test_agent_workflow_cli.py
python scripts/verify.py --task docs/agent/tasks/2026-08-12-canonical-template-conversion-dsc-isothermal.md --changed --types
git diff --check
```

## Risks and compatibility

- A false program-segment classification could create invalid kinetic input.
  The converter and template adapter fail closed when time, heat flow, source
  indexing, mass, or template-level temperature stability is insufficient.
  Template execution intentionally validates the recognized hold directly,
  rather than rerunning raw-program segmentation and changing its boundary.
- Existing direct DSC file/directory analysis remains supported unchanged.
- A canonical template records interpreted data and provenance but does not
  replace the raw source or claim instrument calibration beyond observed fields.

## PA6 Read-Only Replay Evidence

- Source: external `PA6-DWJJ.txt` under the user-provided DSC folder; SHA-256
  `789531d03ee8d0da9652c7e0734e8fc40e907f282bd7771990e6948a59dd9db7`.
- Derived run bundle: `D:\PolyNexus-pa6-canonical-smoke-20260812-review-final\bundle`.
  It is outside both the repository and raw-data directory.
- The deterministic converter recognized six crystallisation holds at 180, 181,
  182, 183, 184, and 185 C, retaining 255 C melt holds and ramps only as
  conversion evidence. The sample block supplied 5.9500 mg.
- Template hash: `29659c6757fd98454e678cb4202739a2e2f95cb59c54e64592ab38f8a182331f`.
  Conversion hash: `b80c477d93bddb76ff16b7be6bc06874b1a4ab3a9010160dfbc32f7bb6c5cb0f`.
- This is an engineering replay, not a scientific conclusion or publication
  decision. Inspect the six Avrami fits and instrument/calibration context
  before promoting it beyond `review_required`.

## Memory impact

- [x] Update `docs/agent/memory/active-work.md` with final template boundary,
  PA6 external replay evidence, and remaining scientific-review limits.
