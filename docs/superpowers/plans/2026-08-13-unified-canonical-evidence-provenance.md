# Unified Canonical Evidence Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require DSC, FTIR, SAXS, and WAXS project routes to carry replayable canonical conversion provenance, and prevent unrelated technique limitations from entering a technique's evidence section.

**Architecture:** A closed registry selects a deterministic converter for each supported artifact.  The recipe stores a `CanonicalExperiment`; before invoking an existing engine, the workflow recreates it from the indexed source and fails closed if its hash differs.  The package derives limitations from each matching evidence item and run rather than the package aggregate.

**Tech Stack:** Python dataclasses, existing `CanonicalExperiment`, project workflow recipes, pytest.

---

## File map

- `polynexus/core/canonical_experiments/registry.py`: closed converter lookup,
  generic source-envelope converter, and canonical replay API.
- `polynexus/core/canonical_experiments/__init__.py`: public registry exports.
- `polynexus/core/project_workflow/adapters.py`: create templates for IR/SAXS/
  WAXS steps before a recipe becomes valid.
- `polynexus/core/agent_workflow/service.py`: replay every registered template,
  preserving DSC's specialized materialization path.
- `polynexus/core/project_workflow/package.py`: project matching run/evidence
  limitations into technique-local sections.
- `tests/test_canonical_converter_registry.py`: converter selection, source
  identity, and replay mismatch contracts.
- `tests/test_project_workflow_adapters.py`: recipe provenance and direct-route
  blocking checks.
- `tests/test_project_workflow_package.py`: limitation isolation regression.
- `docs/acceptance/2026-08-13-unified-canonical-evidence-provenance.md`:
  verification and real PA6 replay record.
- `docs/agent/memory/active-work.md`: durable checkpoint summary.

### Task 1: Closed converter registry

**Files:**
- Create: `polynexus/core/canonical_experiments/registry.py`
- Modify: `polynexus/core/canonical_experiments/__init__.py`
- Test: `tests/test_canonical_converter_registry.py`

- [ ] **Step 1: Write the failing registry tests**

```python
def test_registry_converts_supported_static_artifact_to_replayable_template(tmp_path):
    source = tmp_path / "sample.csv"
    source.write_text("Wavenumber,Absorbance\n1700,0.4\n", encoding="utf-8")

    outcome = default_converter_registry().convert_path(
        source, technique="ir", source_artifact_id="source-sha256"
    )

    assert outcome.status == "ready"
    assert outcome.template.template_id == "ir.spectrum.v1"
    assert outcome.template.source_artifact_id == "source-sha256"
    assert outcome.template.conversion_record.conversion_id == "raw-file-envelope.ir.v1"


def test_registry_replay_rejects_template_from_different_source_content(tmp_path):
    source = tmp_path / "sample.csv"
    source.write_text("Wavenumber,Absorbance\n1700,0.4\n", encoding="utf-8")
    registry = default_converter_registry()
    original = registry.convert_path(source, technique="ir", source_artifact_id="source-sha256")
    source.write_text("Wavenumber,Absorbance\n1700,0.8\n", encoding="utf-8")

    replayed = registry.replay_path(source, technique="ir", source_artifact_id="source-sha256")

    assert original.template is not None
    assert replayed.template is not None
    assert replayed.template.content_hash != original.template.content_hash
```

- [ ] **Step 2: Run the new tests to verify RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_canonical_converter_registry.py`

Expected: FAIL because `default_converter_registry` does not exist.

- [ ] **Step 3: Implement the minimal registry and envelope converter**

```python
class CanonicalConverterRegistry:
    def convert_path(self, path: Path, *, technique: str, source_artifact_id: str) -> ConversionOutcome:
        converter = self._converters.get(str(technique).lower())
        if converter is None:
            return _blocked_outcome(technique, source_artifact_id, "canonical_converter_unregistered")
        return converter(path, source_artifact_id)


def convert_static_file_envelope(
    path: Path, *, technique: str, template_id: str, source_artifact_id: str
) -> ConversionOutcome:
    content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    record = ConversionRecord.create(
        conversion_id=f"raw-file-envelope.{technique}.v1",
        source_artifact_id=source_artifact_id,
        observed_columns=("source_bytes",),
        extracted_segments=({"role": "provider_input", "sha256": content_hash},),
    )
    return ConversionOutcome(
        status="ready",
        record=record,
        template=CanonicalExperiment.create(
            template_id=template_id,
            source_artifact_id=source_artifact_id,
            payload={"source_sha256": content_hash, "format": path.suffix.lower().lstrip(".")},
            conversion_record=record,
        ),
    )
```

Register `ir.spectrum.v1`, `saxs.profile.v1`, and `waxs.profile.v1`.  Keep
`dsc.isothermal.v1` delegated to `convert_mettler_isothermal_text`, so its
segment extraction behavior remains unchanged.

- [ ] **Step 4: Run registry tests to verify GREEN**

Run: `python -m pytest -p no:cacheprovider -q tests/test_canonical_converter_registry.py tests/test_canonical_experiment_templates.py tests/test_dsc_canonical_isothermal_conversion.py`

Expected: PASS.

### Task 2: Require canonical templates in technique recipes

**Files:**
- Modify: `polynexus/core/project_workflow/adapters.py`
- Modify: `polynexus/core/agent_workflow/service.py`
- Test: `tests/test_project_workflow_adapters.py`

- [ ] **Step 1: Write the failing project adapter tests**

```python
def test_single_ir_recipe_carries_a_replayable_canonical_template(tmp_path):
    source = tmp_path / "PA6-JW-100.csv"
    source.write_text("Wavenumber,Absorbance\n1700,0.4\n", encoding="utf-8")

    proposal = SingleInputTechniqueAdapter().propose_recipe(
        {"workflow_id": "project.technique.single.v1", "technique": "ir", "paths": [str(source)]}
    )

    assert proposal.recipe is not None
    assert proposal.recipe.steps[0].parameters["canonical_template"]["template_id"] == "ir.spectrum.v1"
    assert proposal.recipe.steps[0].parameters["canonical_converter"] == "raw-file-envelope.ir.v1"


def test_single_route_blocks_when_canonical_template_is_removed(tmp_path):
    recipe = _ir_recipe(tmp_path)
    invalid = replace(recipe, steps=(replace(recipe.steps[0], parameters={"submodule_id": "ir.standard"}),))

    assert AgentWorkflowService().run_recipe(invalid, tmp_path / "run").reason_codes == ("recipe_invalid",)
```

- [ ] **Step 2: Run adapter tests to verify RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_adapters.py -k canonical`

Expected: FAIL because IR/WAXS/SAXS adapters do not add canonical templates.

- [ ] **Step 3: Add template creation and strict validation**

In `SingleInputTechniqueAdapter.propose_recipe` and `TechniqueSeriesAdapter.propose_recipe`, convert each inspected artifact through the registry and add:

```python
parameters={
    "submodule_id": submodule_id,
    "canonical_converter": outcome.record.conversion_id,
    "canonical_template": outcome.template.to_dict(),
}
```

Make `is_valid_recipe` reconstruct `CanonicalExperiment` and require matching
template ID, source artifact ID, and converter ID.  In
`AgentWorkflowService._replay_canonical_template`, select the registry by
technique, reproduce the template, and compare its hash.  In
`_run_existing_pipeline`, only DSC calls `run_isothermal_template`; IR/SAXS/
WAXS retain their existing `run_pipeline(artifact.path, ...)` call after the
canonical replay has passed.

- [ ] **Step 4: Run adapter and workflow tests to verify GREEN**

Run: `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_adapters.py tests/test_agent_workflow_cli.py tests/test_tpae_golden_workflow.py`

Expected: PASS.

### Task 3: Isolate technique limitations in the package

**Files:**
- Modify: `polynexus/core/project_workflow/package.py`
- Test: `tests/test_project_workflow_package.py`

- [ ] **Step 1: Write the failing limitation-isolation regression**

```python
def test_technique_index_does_not_receive_other_technique_limitations(tmp_path):
    package = _create_mixed_technique_package(
        tmp_path,
        ir_limits=("ir_xc_uncalibrated",),
        saxs_limits=("background_unknown",),
    )

    techniques = json.loads((package.path / "techniques.json").read_text(encoding="utf-8"))["techniques"]

    assert techniques["ir"]["limitations"] == ["ir_xc_uncalibrated"]
    assert techniques["saxs"]["limitations"] == ["background_unknown"]
```

- [ ] **Step 2: Run the test to verify RED**

Run: `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_package.py -k limitation`

Expected: FAIL because package-level limitations are passed into every
technique-index entry.

- [ ] **Step 3: Implement matching-run limitation projection**

Remove the package-wide `limitations` parameter from `_technique_index`.  For
each matching evidence item, include its own `limitations`, the matching step
reason codes, and only the matching run reason codes.  Preserve the aggregate
package limitations in `manifest.json` and `limitations.json`.

- [ ] **Step 4: Run package tests to verify GREEN**

Run: `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_package.py tests/test_ai_native_project_entrypoint.py`

Expected: PASS.

### Task 4: External PA6 acceptance and checkpoint

**Files:**
- Create: `docs/acceptance/2026-08-13-unified-canonical-evidence-provenance.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/tasks/2026-08-13-unified-canonical-evidence-provenance.md`

- [ ] **Step 1: Run the complete focused regression matrix**

Run: `python -m pytest -p no:cacheprovider -q tests/test_canonical_converter_registry.py tests/test_canonical_experiment_templates.py tests/test_dsc_canonical_isothermal_conversion.py tests/test_project_workflow_adapters.py tests/test_project_workflow_package.py tests/test_ai_native_project_entrypoint.py`

Expected: PASS.

- [ ] **Step 2: Run the bounded PA6 four-technique read-only replay**

Run:

```powershell
python -m polynexus project-workflow analyze-project `
  --project-root D:\PolyNexus-pa6-four-technique-smoke-20260814 `
  --paths raw/dsc/PA6-DWJJ.txt raw/ftir/PA6-JW-100.csv raw/ftir/PA6-JW-110.csv raw/ftir/PA6-JW-120.csv raw/saxs/PA6.edf raw/waxs/PA6.raw `
  --question "Prepare PA6 DSC FTIR SAXS WAXS evidence" `
  --package-id canonical-provenance-replay
```

Expected: one review-required package with DSC, IR, SAXS, and WAXS technique
entries; each run manifest has at least one canonical template and conversion
hash.  Do not use the metrics as a publication claim.

- [ ] **Step 3: Record acceptance and durable state**

Write the source paths, package path, template IDs, test counts, and known
review limits.  Mark only completed task-card criteria as complete.

- [ ] **Step 4: Run structured verification and checkpoint**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-13-unified-canonical-evidence-provenance.md --changed --types
git diff --check
python scripts/auto_commit.py --message "feat(project): enforce canonical evidence provenance" --files polynexus/core/canonical_experiments/__init__.py polynexus/core/canonical_experiments/registry.py polynexus/core/project_workflow/adapters.py polynexus/core/agent_workflow/service.py polynexus/core/project_workflow/package.py tests/test_canonical_converter_registry.py tests/test_project_workflow_adapters.py tests/test_project_workflow_package.py docs/agent/tasks/2026-08-13-unified-canonical-evidence-provenance.md docs/acceptance/2026-08-13-unified-canonical-evidence-provenance.md docs/agent/memory/active-work.md docs/superpowers/plans/2026-08-13-unified-canonical-evidence-provenance.md
```

Expected: selected checks pass and one local commit is created with no push or
merge.

## Plan self-review

- Spec coverage: Task 1 covers the closed registry; Task 2 covers recipe and
  replay enforcement; Task 3 covers technique-local provenance; Task 4 covers
  the PA6 replay, documentation, verification, and checkpoint.
- No-placeholder check: every production modification has the target file,
  test, command, expected state, and concrete contract names.
- Type consistency: `CanonicalConverterRegistry`, `convert_path`,
  `replay_path`, `canonical_template`, and `canonical_converter` use the same
  names in all tasks.
