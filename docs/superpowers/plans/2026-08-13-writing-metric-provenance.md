# Writing Metric Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Materialize every writing-facing project value as an auditable numerical record instead of a shallow, unitless scalar projection.

**Architecture:** A package-local extractor reads only immutable `EvidenceItem` public results.  It recognizes documented technique payload shapes, maps known metrics to explicit units/methods, and carries existing applicability/support gates into an eligibility field.  The packager writes `citation-metrics.json` and links metric IDs back into `writing-evidence.json`; no provider or raw data changes.

**Tech Stack:** Python dataclasses/mappings, existing project evidence package, pytest.

---

## File map

- `polynexus/core/project_workflow/writing_metrics.py`: immutable metric record
  schema, technique extractors, and JSON-safe validation.
- `polynexus/core/project_workflow/package.py`: package-relative asset links,
  `citation-metrics.json`, manifest, and writing handoff projection.
- `tests/test_project_writing_metrics.py`: direct extractor units, methods,
  eligibility, omissions, and stable IDs.
- `tests/test_project_workflow_package.py`: package file/link regression.
- `docs/acceptance/2026-08-13-writing-metric-provenance.md`: real PA6 output.
- `docs/agent/memory/active-work.md`: durable summary.

### Task 1: Metric record contract and DSC/IR extraction

**Files:**
- Create: `polynexus/core/project_workflow/writing_metrics.py`
- Create: `tests/test_project_writing_metrics.py`

- [ ] **Step 1: Write the failing extraction tests**

```python
def test_dsc_isothermal_metrics_have_segment_method_units_and_provenance():
    records = extract_writing_metrics(_dsc_evidence_item())

    half_time = next(record for record in records if record.metric_key == "t_half_min")
    assert half_time.value == 1.2
    assert half_time.unit == "min"
    assert half_time.method == "dsc.isothermal_avrami_fit"
    assert half_time.source_locator == "parameters.segment_01_180C.t_half_min"
    assert half_time.writing_eligibility == "results_candidate"
    assert half_time.evidence_id == "run-dsc:dsc_isothermal"
    assert half_time.raw_source_hashes == ("raw-dsc",)


def test_uncalibrated_ftir_xc_is_an_index_not_percent_crystallinity():
    records = extract_writing_metrics(_uncalibrated_ir_item())

    index = next(record for record in records if record.metric_key == "PA6_A1200_A1637")
    assert index.unit == "index"
    assert index.method == "PA6_A1200_A1637_uncalibrated"
    assert index.writing_eligibility == "diagnostic_only"
    assert "absolute_crystallinity_not_supported" in index.reason_codes
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_project_writing_metrics.py`

Expected: FAIL because `writing_metrics` does not exist.

- [ ] **Step 3: Implement the frozen record and two narrow extractors**

```python
@dataclass(frozen=True)
class CitationMetric:
    metric_id: str
    technique: str
    metric_key: str
    value: float | int
    unit: str
    method: str
    source_locator: str
    evidence_id: str
    run_id: str
    raw_source_hashes: tuple[str, ...]
    status: str
    writing_eligibility: str
    reason_codes: tuple[str, ...] = ()
```

Build IDs from the complete stable public content.  DSC loops only documented
`parameters.segment_*` mappings and emits finite Avrami metrics.  IR emits
assigned peak position/FWHM records and transforms an uncalibrated `Xc_pct`
to a band-index metric name from `Xc_band`/`Xc_method`; it must not use `%`.

- [ ] **Step 4: Run Task 1 tests to verify GREEN**

Run: `python -m pytest -p no:cacheprovider -q tests/test_project_writing_metrics.py -k 'dsc or ir'`

Expected: PASS.

### Task 2: SAXS/WAXS gate-preserving extraction

**Files:**
- Modify: `polynexus/core/project_workflow/writing_metrics.py`
- Modify: `tests/test_project_writing_metrics.py`

- [ ] **Step 1: Write failing SAXS/WAXS tests**

```python
def test_saxs_nonapplicable_metric_is_diagnostic_with_provider_reasons():
    record = extract_writing_metrics(_saxs_item())[0]

    assert record.unit == "nm"
    assert record.method == "saxs_engine.lamellar"
    assert record.writing_eligibility == "diagnostic_only"
    assert record.reason_codes == ("lamellar_applicability_unresolved",)


def test_waxs_low_support_size_stays_diagnostic():
    records = extract_writing_metrics(_waxs_item())

    size = next(record for record in records if record.metric_key == "D_Scherrer_nm")
    assert size.unit == "nm"
    assert size.method == "scherrer"
    assert size.writing_eligibility == "diagnostic_only"
    assert "size_without_multi_peak_support" in size.reason_codes
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_project_writing_metrics.py -k 'saxs or waxs'`

Expected: FAIL because SAXS/WAXS metric evidence is not extracted.

- [ ] **Step 3: Implement only provider-declared metric mappings**

SAXS reads `parameters.metric_evidence.*` and requires finite `value`, string
`unit`, and string `source_ref`.  It uses `applicable` to decide eligibility
and preserves metric reason codes.  WAXS reads `analysis_evidence.feature_evidence`
for `phase_evidence` and constraint names; `crystallinity_method` becomes the
Xc method and low reliability/triggered constraints make the record diagnostic.
Unknown maps generate an omission reason, not a record.

- [ ] **Step 4: Run Task 2 tests to verify GREEN**

Run: `python -m pytest -p no:cacheprovider -q tests/test_project_writing_metrics.py`

Expected: PASS.

### Task 3: Package materialization and writing links

**Files:**
- Modify: `polynexus/core/project_workflow/package.py`
- Modify: `tests/test_project_workflow_package.py`

- [ ] **Step 1: Write the failing package regression**

```python
def test_package_writes_citation_metrics_with_writing_evidence_links(tmp_path):
    package = _package_with_dsc_evidence(tmp_path)

    metrics = json.loads((package.path / "citation-metrics.json").read_text())
    writing = json.loads((package.path / "writing-evidence.json").read_text())

    assert metrics["version"] == 1
    assert metrics["records"][0]["evidence_id"]
    assert writing["techniques"]["dsc"]["evidence"][0]["citation_metric_ids"]
```

- [ ] **Step 2: Run the test to verify RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_package.py -k citation_metrics`

Expected: FAIL because no citation-metrics file exists.

- [ ] **Step 3: Materialize and link the metric ledger**

Write a `citation-metrics.json` envelope with `version`, `records`, and
`omissions`; declare it in `manifest.json`.  Resolve figures/tables using the
existing package asset map, attach package-relative paths to records, and place
matching metric IDs and eligibility counts into each writing evidence item.
Add a concise `Citation metrics: citation-metrics.json` line to
`writing-input.md`.

- [ ] **Step 4: Run package tests to verify GREEN**

Run: `python -m pytest -p no:cacheprovider -q tests/test_project_writing_metrics.py tests/test_project_workflow_package.py tests/test_ai_native_project_entrypoint.py`

Expected: PASS.

### Task 4: PA6 acceptance and checkpoint

**Files:**
- Create: `docs/acceptance/2026-08-13-writing-metric-provenance.md`
- Modify: `docs/agent/tasks/2026-08-13-writing-metric-provenance.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run the complete focused matrix**

Run: `python -m pytest -p no:cacheprovider -q tests/test_project_writing_metrics.py tests/test_project_workflow_package.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py`

Expected: PASS.

- [ ] **Step 2: Run the external read-only PA6 four-technique replay**

Run:

```powershell
python -m polynexus project-workflow analyze-project `
  --project-root D:\PolyNexus-pa6-four-technique-smoke-20260814 `
  --paths raw/dsc/PA6-DWJJ.txt raw/ftir/PA6-JW-100.csv raw/ftir/PA6-JW-110.csv raw/ftir/PA6-JW-120.csv raw/saxs/PA6.edf raw/waxs/PA6.raw `
  --question "Prepare PA6 DSC FTIR SAXS WAXS evidence" `
  --package-id writing-metric-provenance-replay
```

Expected: one package with all four techniques, `citation-metrics.json`, and
no FTIR uncalibrated `Xc_pct` emitted as a `%` Results candidate.

- [ ] **Step 3: Record acceptance and complete task card criteria**

Record package path, metric counts by technique/eligibility, known scientific
limits, and exact verification output.  Do not state a publication conclusion.

- [ ] **Step 4: Structured verification and local checkpoint**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-13-writing-metric-provenance.md --changed --types
git diff --check
python scripts/auto_commit.py --message "feat(project): add writing metric provenance" --files polynexus/core/project_workflow/writing_metrics.py polynexus/core/project_workflow/package.py tests/test_project_writing_metrics.py tests/test_project_workflow_package.py docs/agent/tasks/2026-08-13-writing-metric-provenance.md docs/acceptance/2026-08-13-writing-metric-provenance.md docs/agent/memory/active-work.md docs/superpowers/plans/2026-08-13-writing-metric-provenance.md
```

Expected: all selected verification passes and one local checkpoint is created;
no push, merge, or raw-data modification occurs.

## Plan self-review

- Task 1 covers exact DSC and FTIR semantics, including the uncalibrated FTIR
  guard; Task 2 preserves SAXS/WAXS provider gates; Task 3 provides all
  package/ARS links; Task 4 provides real-data acceptance and checkpoint.
- `CitationMetric`, `metric_id`, `writing_eligibility`, and
  `citation_metric_ids` are used consistently.
- No step leaves an unknown unit or method to inference; unknown values become
  omissions with a reason instead of incomplete metric records.
