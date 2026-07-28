# SAXS Static publication gate binding

## Goal

Make Static SAXS `publication_role="main"` depend on the existing emitted
publication/quality evidence instead of render success or `quality_flag="OK"`
alone. Preserve all curves and diagnostic figures when the gate fails.

## Non-goals

- No new physical threshold, metric calculation, rescue, interpolation, or
  frame deletion.
- No changes to temperature/strain calculations or their existing figure IDs.
- No GUI-specific scientific branching.
- No claim that a rendered `status="ready"` asset is scientifically approved.

## Affected boundaries

- Eligibility: `polynexus/core/saxs_engine/figure_eligibility.py`.
- Static figure role/fallback metadata:
  `polynexus/core/saxs_engine/figure_static.py`.
- Regression coverage: `tests/test_saxs_static_publication_gate.py` plus the
  existing Static provider contracts that currently rely on implicit
  `quality_flag="OK"` promotion.
- Durable records: this task card, its design/plan, and agent memory.

## Contract

1. `ERROR` evidence remains `diagnostic` and cannot be overridden.
2. Explicit `paper_figure_candidate=False` remains `diagnostic`.
3. Explicit `paper_figure_candidate=True` may be `main` only when the
   existing reliability vetoes do not reject the frame.
4. Missing publication authorization is `si` (fail closed), even when the
   curve can be rendered and `quality_flag` is `OK`.
5. Static provider keeps the profile and diagnostic evidence available. If no
   Main definition remains, emitted definitions carry a deterministic
   `no_publication_ready_figure` reason in recipe metadata.

## Implementation plan

1. Add RED tests for explicit approval, missing authorization, explicit
   rejection, and no-Main downgrade provenance.
2. Make Static eligibility require the existing explicit candidate field while
   leaving temperature/strain classification unchanged.
3. Preserve an SI profile and attach deterministic no-publication metadata
   when Static has no Main definition.
4. Run focused, SAXS, and structured verification, then checkpoint only the
   allowlisted files.

## Acceptance criteria

- [x] RED proves an unqualified Static `OK` frame is incorrectly promoted before
  the change.
- [x] GREEN proves explicit candidate approval can produce Main, while missing or
  rejected authorization cannot.
- [x] Existing physical evidence payloads and figure data are unchanged.
- [x] Static provider, figure pipeline, and the full SAXS matrix pass with an
  external basetemp.
- [x] Structured verification and `scripts/auto_commit.py` use an explicit
  allowlist; unrelated GUI/editor/release/scratch files remain untouched.

## Verification

```powershell
python -m pytest tests/test_saxs_static_publication_gate.py tests/test_saxs_mode_evidence_contract.py tests/test_saxs_publication_pack_upgrade.py tests/test_saxs_static_figure_panels.py -q --basetemp <external-dir>
$testFiles=@(Get-ChildItem tests -File -Filter 'test_saxs*.py' | ForEach-Object { $_.FullName })
python -m pytest $testFiles -q --basetemp <external-dir>
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-static-publication-gate.md --changed --types
git diff --check
```

## Known limitations

The fresh real SAXS walkthrough now produces no Static Main figure when the
existing data has no explicit publication candidate; its SI/Diagnostic
Manifest entries carry `no_publication_ready_figure`. Human GUI restart and
scientific publication review remain separate release gates. Full repository
`--full --boundary` verification is not claimed for this focused task.

## Changed-file allowlist

- `docs/agent/tasks/2026-07-28-saxs-static-publication-gate.md`
- `docs/superpowers/specs/2026-07-28-saxs-static-publication-gate-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-static-publication-gate.md`
- `polynexus/core/saxs_engine/figure_eligibility.py`
- `polynexus/core/saxs_engine/figure_static.py`
- `tests/test_saxs_static_publication_gate.py`
- existing Static role regression tests updated only where their fixtures
  intentionally exercise the new explicit gate
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
