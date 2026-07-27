# SAXS Figure/Manifest Evidence Binding

## Goal

Bind existing SAXS quality evidence to static, temperature, and strain figure
definitions so Manifest-backed figure documents remain auditable without
recalculating analysis or changing publication roles.

## Non-goals

- No SAXS numerical algorithm, q-window, physical threshold, or applicability rule.
- No interpolation, frame repair, AI candidate execution, or automatic rescue.
- No change to publication roles, figure selection, output profiles, or Gallery policy.
- No raw detector/geometry inference or new 2D calculation.
- No replacement of the bundle-level `quality_evidence.json` contract.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_evidence.py`
- `polynexus/core/saxs_engine/figure_provider.py`
- `polynexus/core/saxs_engine/figure_static.py`
- `polynexus/core/saxs_engine/figure_temperature.py`
- `polynexus/core/saxs_engine/figure_strain.py`
- `tests/test_saxs_figure_evidence_binding.py`
- task/spec/plan and durable SAXS memory records

## Acceptance criteria

- [x] The compact evidence projection is detached, deterministic, and strict
  JSON-safe with non-finite values represented as `null`.
- [x] Static frame and batch FigureDefinitions expose existing frame evidence
  references and preserve existing publication roles.
- [x] Temperature FigureDefinitions preserve both provider frame indices and
  original `source_index` values after sorting; sequence evidence is not copied
  into individual frames.
- [x] Strain FigureDefinitions preserve frame/series evidence and keep
  orientation evidence separate from generic 1D metric evidence.
- [x] Missing or malformed evidence never creates a positive evidence record or
  prevents legacy definitions from being returned.
- [x] FigurePipeline serialization retains the binding in the figure document
  and existing SAXS export provenance remains authoritative.
- [x] Focused tests, the complete SAXS matrix, task-scoped verifier, strict JSON,
  whitespace, and explicit allowlist checkpoint all have recorded evidence.

## Implementation plan

1. Write RED tests for the projection, static/temperature/strain provider
   attachment, missing evidence, and FigurePipeline document serialization.
2. Implement the read-only `figure_evidence` projection and attachment helper.
3. Attach the helper in production static, temperature, and strain providers and
   in the compatibility provider without changing role calculation.
4. Run focused GREEN verification and the existing SAXS figure compatibility
   matrix; repair only failures caused by this task.
5. Run the task-scoped verifier, complete SAXS matrix, strict JSON/diff checks,
   update durable memory, and create one `auto_commit.py` checkpoint using the
   explicit changed-file allowlist.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_figure_evidence'
python -m pytest tests/test_saxs_figure_evidence_binding.py tests/test_saxs_mode_evidence_contract.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_publication_pack_upgrade.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-figure-evidence-binding.md --changed --types
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
git diff --check
```

Recorded evidence for this implementation:

- Focused Figure/Manifest/provider matrix: `33 passed`.
- Complete `tests/test_saxs_*.py` matrix: `317 passed, 4 warnings`; warnings
  are the existing Arial CJK glyph warnings from SAXS rendering tests.
- Task-scoped verifier: task/memory checks, changed Ruff, compile/type
  baseline, quality `282`, preprocessing `106`, and whitespace all passed.
- `git diff --check`: passed.
- Fresh `python scripts/verify.py --changed --types --full --boundary` was
  run with an isolated basetemp and timed out with exit `124` after about
  1204 seconds, without a test-failure summary. The timeout left the verifier
  and pytest child processes alive; they were identified as this run and
  terminated, then a post-stop audit found no remaining verifier or pytest
  process. No full/boundary pass is claimed for this task.

## Known limitations

This task makes evidence traceable from figures to the authoritative export;
it does not decide whether a metric is scientifically publishable. A future
role-gating task and human scientific review are still required before any
automatic publication claim.

## Changed-file allowlist

- `polynexus/core/saxs_engine/figure_evidence.py`
- `polynexus/core/saxs_engine/figure_provider.py`
- `polynexus/core/saxs_engine/figure_static.py`
- `polynexus/core/saxs_engine/figure_temperature.py`
- `polynexus/core/saxs_engine/figure_strain.py`
- `tests/test_saxs_figure_evidence_binding.py`
- this task card
- `docs/superpowers/plans/2026-07-27-saxs-figure-evidence-binding.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
