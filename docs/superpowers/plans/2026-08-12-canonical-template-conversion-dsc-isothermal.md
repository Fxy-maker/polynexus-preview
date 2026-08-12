# Canonical DSC Template Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the reusable canonical-template/conversion boundary and use it to run Mettler multi-program DSC isothermal segments through the existing kinetics provider.

**Architecture:** A small generic template contract holds immutable JSON-safe experiment payloads and conversion provenance. A DSC converter emits `dsc.isothermal.v1` from validated Mettler rows; a public DSCEngine adapter consumes only that template and reuses the existing kinetic calculation.

**Tech Stack:** Python 3.12, dataclasses, NumPy, existing `DSCScan`/`DSCEngine`, pytest.

---

### Task 1: Canonical contract

**Files:**
- Create: `polynexus/core/canonical_experiments/models.py`
- Create: `polynexus/core/canonical_experiments/__init__.py`
- Create: `tests/test_canonical_experiment_templates.py`

- [x] **Step 1: Write failing contract tests**

```python
def test_template_hash_and_nested_payload_are_immutable():
    template = CanonicalExperiment.create(template_id="dsc.isothermal.v1", payload={"segments": [{"setpoint_C": 180.0}]})
    assert CanonicalExperiment.from_dict(template.to_dict()).content_hash == template.content_hash
    with pytest.raises(TypeError):
        template.payload["segments"] = ()
```

- [x] **Step 2: Run the focused test to verify RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_canonical_experiment_templates.py`

Expected: import failure because canonical contract module does not exist.

- [x] **Step 3: Implement frozen canonical models**

```python
@dataclass(frozen=True)
class CanonicalExperiment:
    template_id: str
    contract_version: str
    source_artifact_id: str
    payload: Mapping[str, Any]
    conversion_record: ConversionRecord
    content_hash: str
```

Use the same canonical JSON / recursive freeze approach as agent workflow
contracts; `from_dict` must recompute and reject a mismatched hash.

- [x] **Step 4: Run GREEN**

Run: `python -m pytest -p no:cacheprovider -q tests/test_canonical_experiment_templates.py`

Expected: all canonical contract tests pass.

### Task 2: Mettler multi-program converter

**Files:**
- Create: `polynexus/core/canonical_experiments/dsc_isothermal.py`
- Create: `tests/test_dsc_canonical_isothermal_conversion.py`

- [x] **Step 1: Write failing conversion tests**

```python
def test_converter_selects_only_lower_temperature_crystallisation_holds():
    template = convert_mettler_isothermal_text(FIXTURE, source_artifact_id="source")
    assert [segment["setpoint_C"] for segment in template.payload["segments"]] == [180.0, 181.0]
    assert template.conversion_record.excluded_segments[0]["role"] == "melt_hold"
```

Include malformed time/temperature data and a short hold case that returns an
explicit blocked conversion result.

- [x] **Step 2: Run RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_dsc_canonical_isothermal_conversion.py`

Expected: import failure because converter does not exist.

- [x] **Step 3: Implement parser, classifier, and validator**

Parse numeric Mettler rows without modifying raw data. Group contiguous constant
setpoints, validate timing/finite values/stability, exclude preparation melt
holds only by explicit sequence rule, and create source row/time evidence for
every accepted/excluded group.

- [x] **Step 4: Run GREEN**

Run: `python -m pytest -p no:cacheprovider -q tests/test_dsc_canonical_isothermal_conversion.py`

Expected: all conversion and rejection tests pass.

### Task 3: Deterministic DSC provider adapter

**Files:**
- Modify: `polynexus/core/dsc.py`
- Modify: `tests/test_dsc_kinetics.py`

- [x] **Step 1: Write a failing canonical-template provider test**

```python
def test_dsc_engine_runs_existing_isothermal_kinetics_from_canonical_template():
    result = DSCEngine().run_isothermal_template(template)
    assert result["avrami_series"]
```

- [x] **Step 2: Run RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_dsc_kinetics.py -k canonical`

Expected: method missing.

- [x] **Step 3: Add public template boundary**

Validate template id/hash, materialize accepted segment arrays into existing
`DSCScan` instances, set `dsc.isothermal`, and call existing `run_kinetics`.
Attach template/conversion hashes to public provenance. Do not edit Avrami
calculation functions.

- [x] **Step 4: Run GREEN**

Run: `python -m pytest -p no:cacheprovider -q tests/test_dsc_kinetics.py -k canonical`

Expected: canonical adapter test passes.

### Task 4: Agent workflow conversion provenance

**Files:**
- Modify: `polynexus/core/agent_workflow/tpae.py`
- Modify: `polynexus/core/agent_workflow/service.py`
- Modify: `tests/test_tpae_golden_workflow.py`

- [x] **Step 1: Write failing workflow tests**

```python
def test_tpae_dsc_file_recipe_runs_only_after_canonical_conversion():
    run = service.run_recipe(recipe, output_dir)
    assert run.steps[0].result_summary["canonical_template_hash"]
```

- [x] **Step 2: Run RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_tpae_golden_workflow.py -k canonical`

Expected: current workflow blocks a DSC file or lacks template provenance.

- [x] **Step 3: Adapt TPAE DSC execution**

Permit a single DSC file only through a registered converter. Record canonical
template/conversion identity in the signed run payload before provider
execution. Preserve the current raw input hash, recipe validation, HMAC receipt,
and raw-directory write protection.

- [x] **Step 4: Run GREEN**

Run: `python -m pytest -p no:cacheprovider -q tests/test_tpae_golden_workflow.py -k canonical`

Expected: converted-file replay and failure gates pass.

### Task 5: Real PA6 smoke evidence and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-08-12-canonical-template-conversion-dsc-isothermal.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run focused regression matrix**

Run: `python -m pytest -p no:cacheprovider -q tests/test_canonical_experiment_templates.py tests/test_dsc_canonical_isothermal_conversion.py tests/test_dsc_kinetics.py tests/test_tpae_golden_workflow.py tests/test_agent_workflow_cli.py`

Expected: all tests pass.

- [x] **Step 2: Run PA6 external smoke replay**

Use only `C:\Users\Fan Xuyi\Desktop\文件夹\弹性体\弹性体中文\DSC-等温结晶\PA6-DWJJ.txt`; write the manifest/template/run bundle to an external sibling output directory, not under the raw-data root. Record recognized 180--185 C segments and status without publication claims.

- [x] **Step 3: Run structured verification**

Run: `python scripts/verify.py --task docs/agent/tasks/2026-08-12-canonical-template-conversion-dsc-isothermal.md --changed --types`

Expected: selected checks pass.

- [x] **Step 4: Commit explicit task allowlist**

Run: `python scripts/auto_commit.py --message "feat(canonical): convert multi-program DSC holds" --files <task allowlist>`

Expected: local checkpoint only, with no push or merge.
