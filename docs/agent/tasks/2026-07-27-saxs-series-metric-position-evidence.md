# SAXS Series Metric Position Evidence

## Goal

Add deterministic frame-position and optional original `source_index` evidence
to existing SAXS series metric summaries so partial data can be audited without
guessing from frame payloads.

## Non-goals

- Do not change any SAXS numerical calculation, physical gate, or quality level
  rule.
- Do not interpolate, repair, delete, reorder, or replace frames.
- Do not add trend thresholds, AI calls, rescue execution, or publication-role
  changes.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_series_metric_evidence.py`
- `tests/test_saxs_temperature_guinier_evidence.py`
- this task card, its spec/plan, and durable memory

## Acceptance criteria

- [x] `MetricEvidenceSummary` round-trips positional tuples as strict JSON-safe
  data.
- [x] The builder reports evidence, missing, diagnostic, unusable, and invalid
  level positions without changing existing counts or levels.
- [x] A valid optional source-index list is preserved in the input order.
- [x] A source-index length mismatch emits a stable reason and no partial map.
- [x] Temperature metric summaries retain the existing sorted point order and
  original `source_index` values.
- [x] Existing frame evidence, DataFrame shape/values, Export, Workbench, and
  physical thresholds remain unchanged.
- [x] TDD RED and GREEN are observed; the focused/SAXS/code-specific checks
  pass.
- [x] The exact structured `--changed --types` verifier was attempted and its
  unrelated shared-worktree/environment limitation is recorded below.
- [ ] The explicit-allowlist checkpoint is pending because
  `scripts/auto_commit.py` cannot create `.git/index.lock` in the shared
  workspace (`Permission denied`).

## Implementation plan

1. Add failing contract tests for positional classification, strict JSON
   round-trip, source-index mapping, mismatch downgrade, and sorted
   temperature alignment.
2. Extend the immutable summary contract and existing builder with positional
   tuples and an optional complete source-index mapping, without changing
   existing counts or levels.
3. Pass the existing temperature `source_index` order into the summary builder
   and verify consumer compatibility.
4. Run focused tests, the isolated complete SAXS matrix, the structured
   verifier, and `git diff --check`; then record exact outcomes and create one
   explicit-allowlist checkpoint.

## Verification

```powershell
python -m pytest tests/test_saxs_series_metric_evidence.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_mode_evidence_propagation.py tests/test_saxs_workbench_series_evidence.py tests/test_saxs_export_bundle.py -q
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-series-metric-position-evidence.md --changed --types
git diff --check
```

The required structured verifier command is:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-series-metric-position-evidence.md --changed --types
```

## Verification evidence

- TDD RED was observed with `4 failed, 10 passed`; the failures were the new
  missing positional fields/source mapping and the missing temperature
  propagation.
- Focused GREEN consumer matrix: `38 passed, 2 warnings`.
- Isolated-basetemp SAXS matrix: `353 passed, 6 warnings`. The first shared
  `.pytest_tmp` invocation reported `350 passed, 2 failed` in pre-existing 2D
  anisotropy state; the two tests pass in isolation and the isolated-basetemp
  full rerun is the authoritative SAXS result for this task.
- Direct quality-gate equivalent: `282 passed, 2 warnings`; direct
  preprocessing gate equivalent: `106 passed, 2 warnings`.
- Allowlist Ruff and `py_compile` passed; `git diff --check` passed with only
  existing CRLF normalization warnings.
- The exact structured `--changed --types` verifier reached task/memory checks
  but stopped at pre-existing changed-file Ruff findings in `config.py`; a
  verifier run without `--changed` then stopped before tests because its
  `pytest` child could not be launched (`WinError 5`). These are environment
  and shared-worktree limitations, not claims of a structured verifier pass.
- Two attempts to run `scripts/auto_commit.py` with the exact allowlist failed
  before staging with `Unable to create 'D:/PolyNexus/.git/index.lock':
  Permission denied`; no commit hash exists and no lock file was deleted.

## Known limitations

The new fields identify evidence positions and existing source indices only.
They do not establish physical continuity, calibrate a method, authorize
rescue, or constitute real-data scientific sign-off.

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_series_metric_evidence.py`
- `tests/test_saxs_temperature_guinier_evidence.py`
- `docs/agent/tasks/2026-07-27-saxs-series-metric-position-evidence.md`
- `docs/superpowers/specs/2026-07-27-saxs-series-metric-position-evidence-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-series-metric-position-evidence.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
