# Task: SAXS 1D quality provenance source binding

**Status:** complete; explicit local allowlist checkpoint created

## Goal

Bind every available SAXS 1D quality report and its sanitization actions to the
actual loaded frame/file across static, temperature, and strain analysis while
preserving existing scientific behavior.

## Finding

`DataQualityReport` already has `source_id` and `raw_data_ref`, and downstream
consumers already transport those fields. `analyze_single()` currently does
not accept source metadata, while temperature and strain series calls do not
pass the high-level engine's `_file_list` mapping. A report can therefore show
that a profile was cleaned without identifying the source frame that was
cleaned.

## Design decision

- Add optional `source_id` and `raw_data_ref` to `analyze_single()`.
- Use `frame-{original_index}` as the high-level logical ID and the exact
  `_file_list` value as `raw_data_ref`.
- Pass source metadata through temperature and strain series APIs using
  aligned optional sequences. Temperature retains original source indices after
  condition sorting; strain stays positional.
- Treat missing or length-mismatched source metadata as unavailable. Do not
  infer a path, copy a neighboring source, or rewrite a source reference.
- Reuse current report-copy and export/evidence projections; no new consumer
  contract is added.

## Non-goals

- No analysis, cleaning, threshold, quality-level, rescue, AI, or publication
  behavior changes.
- No frame fabrication, interpolation, or source guessing.
- No changes to detector/orientation provenance or GUI-specific branching.

## Acceptance criteria

- [x] Direct single-frame provenance is stored when explicitly supplied.
- [x] Static, temperature, and strain paths preserve frame/file binding.
- [x] Temperature source mapping remains correct after sorting.
- [x] Missing/mismatched sources remain empty and fail closed as provenance.
- [x] Existing actions and report fields reach current consumers unchanged.
- [x] TDD RED/GREEN, SAXS matrix, structured verifier, and diff check are run.
- [x] One explicit allowlist checkpoint is created after fresh verification.

## Implementation plan

1. Add focused RED tests for direct binding, temperature sorting, strain
   position, missing metadata, and high-level static source forwarding.
2. Add the optional source parameters to `analyze_single()` and pass them into
   the existing report builder.
3. Thread aligned source metadata through temperature and strain series APIs.
4. Thread `_file_list`/single-file provenance through `SAXSEngine` paths.
5. Run focused GREEN tests, exact SAXS matrix, task verifier, and diff check.
6. Update durable memory with actual evidence and create one allowlist
   checkpoint, leaving all pre-existing parallel files untouched.

## Affected boundaries

- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `polynexus/core/saxs.py`
- `tests/test_saxs_1d_quality_provenance.py`
- `tests/test_saxs_temperature_status.py` (compatibility-only test-double signature)

## Verification

The task uses the focused TDD commands, the complete SAXS test matrix, the
structured repository verifier, and `git diff --check` below.

Required structured command:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-1d-quality-provenance-source-binding.md --changed --types
```

## Verification commands

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_provenance_red'
python -m pytest -q tests/test_saxs_1d_quality_provenance.py
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_provenance_focus'
python -m pytest -q tests/test_saxs_1d_quality_provenance.py tests/test_saxs_dirty_profile_sanitization.py tests/test_saxs_quality_contracts.py tests/test_saxs_temperature_guinier_evidence.py
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=C:\Temp\PolyNexus_saxs_provenance_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-1d-quality-provenance-source-binding.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `polynexus/core/saxs.py`
- `tests/test_saxs_1d_quality_provenance.py`
- `tests/test_saxs_temperature_status.py` (compatibility-only test-double signature)
- `docs/agent/tasks/2026-07-28-saxs-1d-quality-provenance-source-binding.md`
- `docs/superpowers/specs/2026-07-28-saxs-1d-quality-provenance-source-binding-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-1d-quality-provenance-source-binding.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`

## Verification record

- TDD RED: `5 failed`; all failures were the expected missing source-binding
  parameters/forwarding.
- Focused GREEN/final regression: `27 passed`.
- Exact SAXS matrix: `411 passed, 6 warnings`.
- First task-verifier attempt was blocked by the repository's pre-existing
  `.pytest_tmp` Windows permission lock during cleanup (`54 setup errors`).
  With external D: basetemp, the structured verifier exited `0`: quality gate
  `283 passed`, preprocessing gate `106 passed`, Ruff, compile, type baseline,
  memory, task card, and whitespace checks all passed.
- Final focused regression and `git diff --check` exited `0`. No full/boundary
  repository rerun was required for this atomic provenance task; the exact
  SAXS matrix and structured verifier are the authoritative fresh checks.
