# AI-first Polymer Capability Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a versioned, AI-callable polymer computation foundation that represents multidimensional data, declares capability contracts, separates computation state from scientific promotion, and executes deterministic dependency graphs through shared PolyNexus objects.

**Architecture:** Add a small `polynexus.core.ai_platform` contract layer rather than another technique-specific model. It adapts to existing `CanonicalExperiment`, `ComputeRun`, `ResearchGraph`, metric manifests and evidence packages. The first implementation provides immutable JSON-safe contracts and a minimal planner/graph executor; provider migrations and new polymer algorithms remain explicit later tasks.

**Tech Stack:** Python 3.10 dataclasses, existing canonical JSON/hash helpers, pytest, existing ComputeRun and capability registries; no new runtime dependency.

---

## Task 1: Public multidimensional data and state contracts

**Files:**
- Create: `polynexus/core/ai_platform/contracts.py`
- Create: `polynexus/core/ai_platform/__init__.py`
- Create: `tests/test_ai_platform_contracts.py`
- Modify: `polynexus/core/__init__.py` only if public exports are required by existing import conventions

- [ ] **Step 1: Write the failing tests**

Add tests that construct and round-trip:

```python
def test_datablock_roundtrip_preserves_dims_units_mask_and_hash():
    block = DataBlock.create(
        kind="matrix",
        shape=(2, 3),
        dims=("temperature", "wavenumber"),
        coords={"temperature": (20.0, 40.0), "wavenumber": (1000.0, 1100.0, 1200.0)},
        coord_units={"temperature": "degC", "wavenumber": "1/cm"},
        array_ref={"uri": "artifact://array/abc", "sha256": "a" * 64},
        mask_ref={"uri": "artifact://mask/abc", "sha256": "b" * 64},
    )
    restored = DataBlock.from_dict(block.to_dict())
    assert restored == block
    assert restored.content_hash == block.content_hash


def test_axis_provenance_rejects_synthetic_axis_for_quantitative_gate():
    axis = AxisProvenance.create(name="temperature", source="synthetic", method="frame_index")
    assert axis.accepts_quantitative is False


def test_computation_state_roundtrip_keeps_four_independent_status_axes():
    state = ComputationState.create(
        data_availability="raw",
        computability="needs_input",
        validity="not_assessed",
        promotion="diagnostic_only",
        missing_inputs=("q_calibration",),
    )
    assert ComputationState.from_dict(state.to_dict()) == state
```

- [ ] **Step 2: Run the focused tests and verify the expected red failure**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_ai_platform_contracts.py
```

Expected: collection or import failure because `polynexus.core.ai_platform` and its public contracts do not yet exist.

- [ ] **Step 3: Implement the minimal immutable contracts**

Implement JSON-safe frozen dataclasses with deterministic hashes:

```python
@dataclass(frozen=True)
class DataBlock:
    block_id: str
    schema_version: str
    kind: str
    shape: tuple[int, ...]
    dims: tuple[str, ...]
    coords: Mapping[str, Any]
    coord_units: Mapping[str, str]
    array_ref: Mapping[str, Any]
    mask_ref: Mapping[str, Any] | None = None
    uncertainty_ref: Mapping[str, Any] | None = None
    axis_provenance: Mapping[str, AxisProvenance] = field(default_factory=dict)
    source_artifact_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, *, kind, shape, dims, coords, coord_units, array_ref, **kwargs):
        normalized_shape = tuple(int(value) for value in shape)
        normalized_dims = tuple(str(value) for value in dims)
        if len(normalized_shape) != len(normalized_dims):
            raise ValueError("DataBlock shape and dims must have equal lengths")
        payload = {
            "schema_version": "1",
            "kind": str(kind),
            "shape": list(normalized_shape),
            "dims": list(normalized_dims),
            "coords": dict(coords),
            "coord_units": dict(coord_units),
            "array_ref": dict(array_ref),
            **kwargs,
        }
        block_id = _canonical_hash(payload)
        return cls(block_id=block_id, **_validated_fields(payload))

    def to_dict(self) -> dict[str, Any]:
        return _public_dataclass(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DataBlock":
        restored = cls.create(**_creation_fields(value))
        if restored.block_id != value.get("block_id"):
            raise ValueError("DataBlock content hash does not match its content")
        return restored
```

The private helpers used above are part of the same module: `_canonical_hash` serializes sorted JSON with `allow_nan=False`, `_validated_fields` performs shape/reference validation, `_creation_fields` strips the stored identity before reconstruction, and `_public_dataclass` recursively emits JSON-safe dictionaries. They are not public contracts.

Also implement `AxisProvenance`, `CalibrationRef`, `UncertaintyRef`, `ComputationState`, and a `CapabilityResultStatus` enum/constants. Reject non-finite numbers, duplicate dimensions, invalid shapes, missing array hashes, unknown status values, and quantitative acceptance of synthetic axes. Keep large arrays as references; do not inline NumPy objects.

- [ ] **Step 4: Run the focused tests and verify green**

Run the same command. Expected: all contract tests pass with no warnings.

- [ ] **Step 5: Checkpoint the contract task**

Run `git diff --check`, then use the task-card allowlist to create one local checkpoint for the contract files and tests.

## Task 2: Versioned capability descriptors and planner

**Files:**
- Create: `polynexus/core/ai_platform/capabilities.py`
- Create: `polynexus/core/ai_platform/planner.py`
- Create: `tests/test_ai_capability_planner.py`
- Modify: `polynexus/core/canonical_experiments/capabilities.py` only through an adapter function; preserve existing calculators
- Modify: `polynexus/core/compute/capability_catalog.py` to expose descriptor-backed aliases without removing old entries

- [ ] **Step 1: Write the failing tests**

Cover descriptor validation, `ir`/`ftir` normalization, missing inputs, axis gates, and honest planned polymer families:

```python
def test_planner_returns_needs_input_for_missing_calibration_without_running_provider():
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.absolute_intensity.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix", "required_calibrations": ["q"]},
        output_schema={"absolute_intensity": {"unit": "1/cm"}},
        status="available",
    )
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(matrix_block(calibrations=()),),
        target_capabilities=(descriptor.capability_id,),
    )[0]
    assert item.state.computability == "needs_input"
    assert item.state.missing_inputs == ("calibration:q",)


def test_planner_rejects_synthetic_axis_for_absolute_capability():
    item = planner_for_absolute_q().inspect(
        data_blocks=(matrix_block(axis_source="synthetic"),),
        target_capabilities=("saxs.absolute_intensity.v1",),
    )[0]
    assert item.state.computability == "blocked"
    assert "axis_provenance_not_accepted:q" in item.state.reason_codes


def test_ir_and_ftir_resolve_to_one_descriptor_namespace():
    registry = default_descriptor_registry()
    assert registry.for_technique("ir") == registry.for_technique("ftir")


def test_common_polymer_family_descriptor_is_explicitly_unsupported_not_fabricated():
    descriptor = default_descriptor_registry().get("dma.master_curve.v1")
    assert descriptor.status == "unsupported"
    assert descriptor.executor_key is None
```

- [ ] **Step 2: Run tests to observe the expected red failure**

Run `python -m pytest -p no:cacheprovider -q tests/test_ai_capability_planner.py`; expected import/attribute failures.

- [ ] **Step 3: Implement descriptor and discovery APIs**

Implement:

```python
@dataclass(frozen=True)
class CapabilityDescriptor:
    capability_id: str
    version: str
    techniques: tuple[str, ...]
    input_contract: Mapping[str, Any]
    output_schema: Mapping[str, Any]
    preconditions: tuple[Mapping[str, Any], ...]
    dependencies: tuple[str, ...]
    alternatives: tuple[str, ...]
    uncertainty_policy: Mapping[str, Any]
    status: str
    executor_key: str | None = None
```

Add `CapabilityPlanner.inspect(data_blocks, target_capabilities)` that returns immutable plan items with `computability`, `missing_inputs`, `reason_codes`, and `next_actions`. Normalize `ir`, `ftir`, and provider aliases in one place. Register actual existing capabilities through adapters and register DMA/rheology/TGA/SEC/mechanics as explicit `unsupported` descriptors with schemas but no values.

- [ ] **Step 4: Run planner tests and existing capability tests**

Run the focused planner file plus `tests/test_capability_catalog.py tests/test_capability_execution.py`; expected all pass and existing execution values remain unchanged.

- [ ] **Step 5: Checkpoint the descriptor task**

Run `git diff --check` and the allowlisted auto-commit for descriptor/planner files and tests.

## Task 3: Minimal deterministic execution graph

**Files:**
- Create: `polynexus/core/ai_platform/execution.py`
- Create: `tests/test_execution_graph.py`
- Modify: `polynexus/core/compute/models.py` only to add optional graph/state projection fields with backward-compatible defaults
- Modify: `polynexus/core/compute/service.py` only to expose an adapter entry point; retain synchronous behavior

- [ ] **Step 1: Write the failing tests**

Cover dependency order, deterministic cache keys, invalidation, missing-input nodes, and serialization:

```python
def test_execution_graph_orders_dependencies_and_records_node_provenance():
    graph = ExecutionGraph.create(nodes=(
        ExecutionNode.create(node_id="normalize", capability_id="curve.normalize.v1"),
        ExecutionNode.create(
            node_id="summary",
            capability_id="curve.summary.v1",
            dependencies=("normalize",),
        ),
    ))
    result = graph.execute(
        context=ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="py-test"),
        executors={
            "curve.normalize.v1": lambda _: {"normalized": True},
            "curve.summary.v1": lambda _: {"point_count": 3},
        },
    )
    assert tuple(item.node_id for item in result.node_results) == ("normalize", "summary")
    assert all(item.provenance.get("cache_key") for item in result.node_results)


def test_execution_graph_reuses_same_cache_key_for_same_inputs_and_parameters():
    node = ExecutionNode.create(
        node_id="summary",
        capability_id="curve.summary.v1",
        parameters={"window": 3},
    )
    context = ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="py-test")
    assert node.cache_key(context) == node.cache_key(context)


def test_calibration_change_invalidates_only_downstream_nodes():
    source = ExecutionNode.create(node_id="source", capability_id="source.identity.v1")
    calibrated = ExecutionNode.create(
        node_id="calibrated",
        capability_id="saxs.calibrate.v1",
        dependencies=("source",),
    )
    old = ExecutionContext.create(
        input_hashes=("a" * 64,), calibration_hashes=("b" * 64,), runtime_fingerprint="py-test"
    )
    new = ExecutionContext.create(
        input_hashes=("a" * 64,), calibration_hashes=("c" * 64,), runtime_fingerprint="py-test"
    )
    assert source.cache_key(old) == source.cache_key(new)
    assert calibrated.cache_key(old) != calibrated.cache_key(new)


def test_needs_input_node_does_not_call_executor():
    calls = []
    node = ExecutionNode.create(
        node_id="absolute",
        capability_id="saxs.absolute_intensity.v1",
        state=ComputationState.create(
            data_availability="canonical",
            computability="needs_input",
            validity="not_assessed",
            promotion="diagnostic_only",
            missing_inputs=("calibration:q",),
        ),
    )
    result = ExecutionGraph.create(nodes=(node,)).execute(
        context=ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="py-test"),
        executors={"saxs.absolute_intensity.v1": lambda _: calls.append(True)},
    )
    assert calls == []
    assert result.node_results[0].state.computability == "needs_input"
```

- [ ] **Step 2: Run the tests and observe the expected red failure**

Run `python -m pytest -p no:cacheprovider -q tests/test_execution_graph.py`; expected missing-module failures.

- [ ] **Step 3: Implement graph primitives**

Implement frozen `ExecutionNode`, `ExecutionGraph`, `NodeResult`, and `ExecutionContext`. Validate acyclic dependencies, compute cache keys from input hashes/descriptor/version/parameters/calibration/runtime fingerprint, and expose a synchronous `execute()` that returns node states and provenance. A node with unmet preconditions returns `needs_input` and cannot invoke its executor. Do not add a background scheduler in this task.

- [ ] **Step 4: Run graph tests and compute regression tests**

Run the graph file plus `tests/test_analysis_run_service.py tests/test_agent_directory_compute_run.py tests/test_capability_execution.py`; expected existing ComputeRun behavior remains green.

- [ ] **Step 5: Checkpoint the graph task**

Run `git diff --check` and create the graph allowlisted checkpoint.

## Task 4: Shared ComputeRun and cross-entry projections

**Files:**
- Modify: `polynexus/core/compute/models.py`
- Modify: `polynexus/core/compute/capability_catalog.py`
- Modify: `polynexus/core/project_workflow/evidence.py`
- Modify: `polynexus/core/agent_workflow/` affected DTO adapter identified by focused search
- Modify: `polynexus/cli/` affected read-only projection
- Modify: `polynexus/core/joint/` consumer adapter
- Create: `tests/test_ai_platform_cross_entry.py`

- [ ] **Step 1: Write failing cross-entry tests**

Assert the same serialized `ComputationState`, descriptor ID, metric unit and provenance are visible through ComputeRun, Agent/Codex step summaries, CLI/evidence projection and the narrow GUI DTO adapter. Assert legacy `results_summary` is labeled compatibility-only.

- [ ] **Step 2: Run the matrix and observe red failures**

Run `python -m pytest -p no:cacheprovider -q tests/test_ai_platform_cross_entry.py`; expected missing projection fields or alias mismatch.

- [ ] **Step 3: Add backward-compatible projections**

Add optional fields and adapters; never duplicate scientific calculations. Ensure `default_capability_catalog().for_technique("ir")` and `("ftir")` expose the same descriptor-backed entries. Add explicit state/provenance to metric manifest rows without changing existing value keys.

- [ ] **Step 4: Run producer and consumer matrices**

Run the cross-entry test plus canonical, ComputeRun, Agent workflow, evidence, CLI and GUI DTO focused tests named by the failure output. Record exact pass counts.

- [ ] **Step 5: Checkpoint the cross-entry task**

Use an explicit six-file-or-less allowlist derived from the actual diff; do not include pre-existing untracked artifacts.

## Task 5: Canonical N-D adapters and high-priority polymer capability inventory

**Files:**
- Modify: `polynexus/core/canonical_experiments/` targeted converters for IR temperature series, detector images and NMR FID compatibility
- Create: focused tests for DataBlock references and route selection
- Modify: descriptor registry with honest DMA/rheology/TGA/SEC/mechanics schemas
- Do not add scientific placeholder values

- [ ] **Step 1: Write failing route tests**

Test that FTIR temperature files create one matrix DataBlock, EDF preserves pixel/mask references, and NMR complex input is represented without discarding the imaginary channel. Test that missing calibration returns `needs_input`.

- [ ] **Step 2: Observe the expected red failures**

Run only the new route tests; expected current one-dimensional/envelope behavior to fail the new assertions.

- [ ] **Step 3: Implement adapters using existing converters**

Wrap existing scientific outputs in `DataBlock` references, preserve raw hashes and masks, and keep the old `Measurement` compatibility view. Do not infer physical axes from defaults for quantitative capabilities.

- [ ] **Step 4: Run existing IR/SAXS/WAXS/NMR canonical matrices**

Run the focused files identified by `rg` and the new route tests. Any scientific value change is a blocker requiring a separate reviewed task.

- [ ] **Step 5: Checkpoint only the adapter files and tests**

Use `auto_commit.py` with an exact allowlist.

## Task 6: Documentation, acceptance, and final verification

**Files:**
- Modify: `docs/acceptance/2026-08-30-ai-polymer-capability-platform.md`
- Modify: `docs/agent/memory/active-work.md` and `current-state.md` with durable facts only
- Modify: task card status and completion evidence

- [ ] **Step 1: Run the complete focused architecture matrix**

Run all new AI platform tests and affected producer/consumer tests with `-q -p no:cacheprovider`.

- [ ] **Step 2: Run structured verification**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-30-ai-polymer-capability-platform.md --changed --types
```

For this broad cross-module change, also run:

```powershell
python scripts/verify.py --changed --types --full --boundary
```

If a full run is incomplete or times out, record that exact limitation rather than claiming success.

- [ ] **Step 3: Request spec and code-quality review**

Use fresh reviewer agents after the final diff. Architecture and scientific semantics remain human-review-required before merge.

- [ ] **Step 4: Update durable state and create the final allowlisted checkpoint**

Record exact commands, pass/fail counts, known limitations, and untouched pre-existing files. Use `scripts/auto_commit.py`; never push or merge automatically.
