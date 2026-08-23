# Universal Canonical Templates Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add immutable, provenance-rich generic one-dimensional canonical conversion for CSV, TXT, and Excel files, so IR, SAXS, and WAXS exports can become validated `spectrum_1d.v1` or `scattering_1d.v1` measurements without material-specific templates.

**Architecture:** This phase extends the existing `polynexus.core.canonical_experiments` boundary, rather than replacing the direct-run façade or changing an analysis algorithm.  Typed mapping and measurement objects preserve the acquisition order, exact source locations, units, mapping source, warnings, and content hashes.  A new converter reads one-dimensional tables deterministically, optionally validates an AI/user proposal, and returns a canonical template or explicit `needs_input`; it does not run capabilities or migrate GUI, CLI, Batch, or Codex consumers yet.

**Tech Stack:** Python 3.12, frozen dataclasses, pandas/openpyxl/xlrd, NumPy, pytest, Ruff.

---

## Scope, non-goals, and protected boundaries

This is the first executable slice of
`docs/superpowers/specs/2026-08-24-universal-canonical-templates-design.md`.
It has four narrow responsibilities:

1. Provide JSON-safe, hashable mapping/measurement/item-result contracts.
2. Preserve the current `CanonicalExperiment` persistence contract while
   allowing it to carry ordered `Measurement` objects and mapping provenance.
3. Convert flat CSV/TXT and multi-sheet XLS/XLSX/XLSM one-dimensional tables
   into `spectrum_1d.v1` or `scattering_1d.v1` templates.
4. Return mapping ambiguity as `needs_input` rather than guessing, while
   allowing a validated `MappingProposal` to resolve the ambiguity.

It deliberately does **not** do any of the following:

- replace the temporary `polynexus.core.compute.CanonicalDataset` direct
  envelope or alter `ComputeRun` serialization;
- execute capabilities, calculate peaks, normalize curves, generate figures,
  or alter IR/SAXS/WAXS/DSC numerical algorithms;
- generalize DSC, modify the Mettler isothermal converter, or modify NMR;
- route Quick Analysis, CLI, Batch, Codex, Agent Workflow, Project Workflow,
  Evidence, RAG, ARS, Joint, or paper/review logic through the new converter;
- use polymer/material labels, filenames, or paper metadata to select columns,
  units, or numerical values; or
- remove a legacy converter, format reader, or workflow.

The old `CanonicalExperiment` name remains the stable public container in this
phase.  A later direct-run migration can replace the direct envelope with these
canonical experiments only after it moves every consumer together.  This avoids
having two incompatible objects named `CanonicalDataset` today.

## Planned file structure

| File | Responsibility |
| --- | --- |
| `docs/agent/tasks/2026-08-24-universal-canonical-templates-phase1.md` | Structured implementation task, boundaries, acceptance criteria, and verifier commands. |
| `polynexus/core/canonical_experiments/models.py` | Frozen `MappingSelection`, `MappingProposal`, `Measurement`, and `CapabilityItemResult` contracts; backwards-compatible experiment/outcome extensions. |
| `polynexus/core/canonical_experiments/one_dimensional.py` | Deterministic table inspection, column/unit inference, proposal validation, and canonical 1D conversion. |
| `polynexus/core/canonical_experiments/__init__.py` | Public exports for the new contracts and converter. |
| `tests/test_canonical_measurements.py` | Contract immutability, hashing, mapping-provenance, and item-status tests. |
| `tests/test_canonical_one_dimensional.py` | CSV/TXT/Excel conversion, source locator, unit, ambiguity, and proposal-validation tests. |
| `docs/agent/memory/active-work.md` | Concise durable checkpoint for the completed phase and the deliberate next boundary. |

`polynexus/core/canonical_experiments/registry.py`, direct compute contracts,
legacy readers, engines, and application entry points are intentionally
untouched.  The generic converter is exported as a public conversion API and
will be connected to the registry/direct run only in the next approved
consumer-migration task.

## Canonical representation decided for this phase

The implementation must use these exact public values and reason codes.

```python
MAPPING_SOURCES = frozenset({"observed", "user", "AI proposal", "default"})
CAPABILITY_ITEM_STATUSES = frozenset({"completed", "needs_input", "failed", "not_applicable"})

@dataclass(frozen=True)
class MappingSelection:
    measurement_id: str
    sheet_name: str | None
    sheet_index: int | None
    table_index: int
    header_row: int
    data_row_start: int
    data_row_end: int
    x_column: str
    intensity_column: str
    x_kind: str             # "wavenumber", "q", or "two_theta"
    x_unit: str             # e.g. "cm^-1", "nm^-1", "deg", or "unknown"
    intensity_unit: str     # e.g. "absorbance", "transmittance", "a.u.", or "unknown"
    source: str             # one member of MAPPING_SOURCES

@dataclass(frozen=True)
class MappingProposal:
    proposal_id: str
    source_artifact_id: str
    technique: str
    selections: tuple[MappingSelection, ...]
    source: str             # "user" or "AI proposal"; never "observed"/"default"
    warnings: tuple[str, ...] = ()
    alternatives: tuple[MappingSelection, ...] = ()

@dataclass(frozen=True)
class Measurement:
    measurement_id: str
    family: str             # "spectrum_1d" or "scattering_1d"
    role: str               # "raw_curve"
    channels: Mapping[str, tuple[float, ...]]
    units: Mapping[str, str]
    source_locator: Mapping[str, object]
    acquisition_metadata: Mapping[str, object] = field(default_factory=dict)
    mapping: MappingSelection | None = None
    warnings: tuple[str, ...] = ()

@dataclass(frozen=True)
class CapabilityItemResult:
    item_id: str
    measurement_id: str
    capability_id: str
    status: str
    result: Mapping[str, object] = field(default_factory=dict)
    figures: Mapping[str, str] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
```

`Measurement.channels` must contain exactly `x` and `intensity`, with equal
lengths of at least two finite points.  It must retain input acquisition order;
the converter must not sort, interpolate, normalize, deduplicate, baseline
correct, or transform the values.  `Measurement.units` must contain exactly
`x` and `intensity`.  Its source locator must include all of `source_path`,
`sheet_name`, `sheet_index`, `table_index`, `header_row`, `data_row_start`,
`data_row_end`, `point_start`, and `point_end`; `sheet_name` and `sheet_index`
are `None` for a flat file.

Extend `CanonicalExperiment` with immutable fields
`measurements: tuple[Measurement, ...] = ()` and
`mapping_proposal: MappingProposal | None = None`.  Include both in its hash
payload and `to_dict`; make `from_dict` accept old payloads where they are
absent.  Existing DSC template construction must therefore keep the same
content hash only when serializing/deserializing the old shape is intentionally
impossible; instead, compatibility is defined as successful old-payload read
and semantic equality of its existing template/payload/record.  The regression
test must verify that explicit empty/new fields round-trip and do not mutate
legacy DSC payload data.

`ConversionOutcome` gains `needs_input` as a valid status.  It has no
template for `blocked` or `needs_input`; its `ConversionRecord.reason_codes`
and outcome `reason_codes` must agree.  The converter uses exactly these
reason codes:

- `conversion_source_unreadable`
- `conversion_unsupported_format`
- `conversion_no_numeric_table`
- `conversion_mapping_ambiguous`
- `conversion_mapping_proposal_invalid`
- `conversion_coordinate_channel_invalid`

The finite `CapabilityItemResult` contract is added now but remains detached
from `ComputeRun` until capability routing exists.  It accepts a result and
figures only for `completed`; `needs_input`, `failed`, and `not_applicable`
require empty result/figures.  This guarantees that the next phase can record
independent sibling outcomes without changing their meanings ad hoc.

## Task 1: Record the implementation boundary

**Files:**
- Create: `docs/agent/tasks/2026-08-24-universal-canonical-templates-phase1.md`

- [ ] **Step 1: Create the structured task card before source changes**

Use this content, changing only the final verification evidence after it runs:

```markdown
---
task_id: 2026-08-24-universal-canonical-templates-phase1
kind: architecture
status: active
date: 2026-08-24
title: Add generic one-dimensional canonical conversion
---

# Add generic one-dimensional canonical conversion

## Goal

Convert valid generic IR/SAXS/WAXS one-dimensional CSV, TXT, and Excel tables
into immutable material-neutral canonical measurements with validated mapping
provenance and exact source locators.

## Non-goals

- No capability execution, direct-run/GUI/CLI/Batch/Codex migration, DSC
  generalization, numeric algorithm change, or legacy deletion.
- No material-name mapping, AI-generated values, real-data mutation, or paper
  workflow.

## Affected boundaries

- `core.canonical_experiments`: public immutable contract and public generic
  conversion function.
- Existing canonical persistence: new optional fields must read old template
  payloads and preserve DSC payload semantics.
- Consumers: none yet; registry and application routes remain compatibility
  consumers and are verified as untouched by scope.

## Acceptance criteria

- [ ] Measurement order, channel values, units, source locators, mapping
  source, and hashes are immutable and JSON-safe.
- [ ] Valid IR CSV/TXT becomes one `spectrum_1d.v1` raw-curve measurement.
- [ ] Valid SAXS/WAXS CSV/XLSX becomes ordered `scattering_1d.v1` raw-curve
  measurements, including one measurement per valid workbook sheet.
- [ ] Unknown units warn without invented conversion; missing/ambiguous
  coordinate mapping returns `needs_input`.
- [ ] A source-bound, table-bound user or AI proposal can resolve only an
  otherwise validated ambiguity; invalid proposals do not create a template.
- [ ] No material label affects output, and no legacy reader/engine/entrypoint
  is changed.

## Verification

```powershell
python -m pytest -q -p no:cacheprovider tests/test_canonical_measurements.py tests/test_canonical_one_dimensional.py tests/test_canonical_experiment_templates.py tests/test_dsc_canonical_isothermal_conversion.py
python scripts/verify.py --task docs/agent/tasks/2026-08-24-universal-canonical-templates-phase1.md --changed --types
git diff --check
```
```

- [ ] **Step 2: Validate the card before implementation**

Run:

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-08-24-universal-canonical-templates-phase1.md
```

Expected: exit code `0` and no missing required task-card sections.

- [ ] **Step 3: Commit the task boundary**

```powershell
python scripts/auto_commit.py `
  --message "docs(core): define canonical template phase one" `
  --files docs/agent/tasks/2026-08-24-universal-canonical-templates-phase1.md
```

Expected: one local commit containing only the new task card.

## Task 2: Add frozen mapping, measurement, and item-result contracts

**Files:**
- Modify: `polynexus/core/canonical_experiments/models.py`
- Modify: `polynexus/core/canonical_experiments/__init__.py`
- Create: `tests/test_canonical_measurements.py`
- Modify: `tests/test_canonical_experiment_templates.py`

- [ ] **Step 1: Write the failing contract tests**

Create `tests/test_canonical_measurements.py` with the following tests.  Keep
the imports and literal source values exactly so the planned public API cannot
silently drift.

```python
from __future__ import annotations

import json

import pytest

from polynexus.core.canonical_experiments import (
    CapabilityItemResult,
    MappingProposal,
    MappingSelection,
    Measurement,
)


def _selection(*, source: str = "observed") -> MappingSelection:
    return MappingSelection(
        measurement_id="sheet-0-table-0",
        sheet_name=None,
        sheet_index=None,
        table_index=0,
        header_row=0,
        data_row_start=1,
        data_row_end=3,
        x_column="Wavenumber (cm-1)",
        intensity_column="Absorbance",
        x_kind="wavenumber",
        x_unit="cm^-1",
        intensity_unit="absorbance",
        source=source,
    )


def test_measurement_is_immutable_ordered_and_json_safe() -> None:
    measurement = Measurement(
        measurement_id="sheet-0-table-0",
        family="spectrum_1d",
        role="raw_curve",
        channels={"x": (1700.0, 1600.0, 1500.0), "intensity": (0.2, 0.3, 0.1)},
        units={"x": "cm^-1", "intensity": "absorbance"},
        source_locator={
            "source_path": "sample.csv", "sheet_name": None, "sheet_index": None,
            "table_index": 0, "header_row": 0, "data_row_start": 1,
            "data_row_end": 3, "point_start": 0, "point_end": 2,
        },
        mapping=_selection(),
    )

    assert measurement.channels["x"] == (1700.0, 1600.0, 1500.0)
    assert json.loads(json.dumps(measurement.to_dict()))["units"]["x"] == "cm^-1"
    with pytest.raises(TypeError):
        measurement.channels["x"] = ()
    with pytest.raises(ValueError, match="finite"):
        Measurement(
            measurement_id="bad", family="spectrum_1d", role="raw_curve",
            channels={"x": (1.0, float("nan")), "intensity": (1.0, 2.0)},
            units={"x": "unknown", "intensity": "unknown"},
            source_locator={"source_path": "x", "sheet_name": None, "sheet_index": None,
                            "table_index": 0, "header_row": 0, "data_row_start": 1,
                            "data_row_end": 2, "point_start": 0, "point_end": 1},
        )


def test_mapping_proposal_rejects_unknown_source_and_freezes_alternatives() -> None:
    with pytest.raises(ValueError, match="mapping source"):
        _selection(source="filename")

    proposal = MappingProposal.create(
        source_artifact_id="raw-1", technique="ir", source="AI proposal",
        selections=(_selection(source="AI proposal"),), alternatives=(_selection(),),
    )

    assert proposal.source == "AI proposal"
    assert proposal.alternatives[0].source == "observed"
    with pytest.raises(TypeError):
        proposal.selections[0].source = "user"


@pytest.mark.parametrize("status", ("completed", "needs_input", "failed", "not_applicable"))
def test_capability_item_result_accepts_only_declared_statuses(status: str) -> None:
    result = CapabilityItemResult(
        item_id="item-1", measurement_id="sheet-0-table-0", capability_id="curve.preview.v1",
        status=status,
        result={"point_count": 3} if status == "completed" else {},
        figures={"curve": "curve.svg"} if status == "completed" else {},
        reason_codes=() if status == "completed" else ("prerequisite_missing",),
    )
    assert result.status == status
```

Append this regression test to `tests/test_canonical_experiment_templates.py`:

```python
def test_legacy_template_payload_reads_with_empty_measurements() -> None:
    record = ConversionRecord.create(conversion_id="legacy.v1", source_artifact_id="raw-sha256")
    template = CanonicalExperiment.create(
        template_id="dsc.isothermal.v1", source_artifact_id="raw-sha256",
        payload={"segments": []}, conversion_record=record,
    )
    payload = template.to_dict()
    payload.pop("measurements")
    payload.pop("mapping_proposal")

    restored = CanonicalExperiment.from_dict(payload)

    assert restored.payload == template.payload
    assert restored.measurements == ()
    assert restored.mapping_proposal is None
```

- [ ] **Step 2: Run the contract tests to prove they are red**

Run:

```powershell
python -m pytest -q -p no:cacheprovider tests/test_canonical_measurements.py tests/test_canonical_experiment_templates.py
```

Expected: collection fails because the four new public contracts are not
exported.  The pre-existing canonical-template tests may pass.

- [ ] **Step 3: Implement the minimal immutable contracts**

In `models.py`, reuse existing `_freeze`, `_public`, `_canonical_json`, and
`_hash`; do not copy a second JSON freezer.  Implement all four dataclasses
above plus `to_dict()` methods.  Enforce the following exact validation:

```python
def _require_mapping_source(value: str, *, proposal: bool = False) -> str:
    if value not in MAPPING_SOURCES:
        raise ValueError(f"Unsupported mapping source: {value}")
    if proposal and value not in {"user", "AI proposal"}:
        raise ValueError("A mapping proposal source must be user or AI proposal")
    return value

def _require_locator(value: Mapping[str, Any]) -> Mapping[str, Any]:
    required = {
        "source_path", "sheet_name", "sheet_index", "table_index", "header_row",
        "data_row_start", "data_row_end", "point_start", "point_end",
    }
    missing = required.difference(value)
    if missing:
        raise ValueError("Measurement source locator is missing: " + ", ".join(sorted(missing)))
    return _freeze(value)
```

`MappingProposal.create()` hashes exactly its source artifact, technique,
source, selections, warnings, and alternatives.  `Measurement.create()` is
not required; its caller supplies a deterministic `measurement_id`.  Its
`to_dict()` has no NumPy/Pandas types.  `CapabilityItemResult` rejects unknown
statuses and non-empty `result`/`figures` unless `status == "completed"`.

Extend `CanonicalExperiment.create()`, `_payload()`, `to_dict()`, and
`from_dict()` with optional `measurements=()` and `mapping_proposal=None`.
When loading old JSON, synthesize those defaults before computing the current
hash; accept a legacy stored hash only when it equals the old payload hash, and
then create the current instance with its new content hash.  This preserves
readability of existing persisted templates without falsely claiming they
already carried the new fields.  Add `needs_input` to the accepted
`ConversionOutcome.status` values and reject a template for that status.

Export exactly `CapabilityItemResult`, `MappingProposal`, `MappingSelection`,
`Measurement`, `CanonicalExperiment`, `ConversionOutcome`, and
`ConversionRecord` from `canonical_experiments.__init__`.

- [ ] **Step 4: Run the contract and DSC compatibility tests**

Run:

```powershell
python -m pytest -q -p no:cacheprovider tests/test_canonical_measurements.py tests/test_canonical_experiment_templates.py tests/test_dsc_canonical_isothermal_conversion.py
```

Expected: all tests pass.  The DSC fixture must retain its existing segment
roles, source ranges, and payload values.

- [ ] **Step 5: Commit the contracts**

```powershell
python scripts/auto_commit.py `
  --message "feat(core): add canonical measurement contracts" `
  --files polynexus/core/canonical_experiments/models.py polynexus/core/canonical_experiments/__init__.py tests/test_canonical_measurements.py tests/test_canonical_experiment_templates.py
```

Expected: one local commit containing only the public contract and test files.

## Task 3: Convert generic 1D tables with explicit mapping and locators

**Files:**
- Create: `polynexus/core/canonical_experiments/one_dimensional.py`
- Modify: `polynexus/core/canonical_experiments/__init__.py`
- Create: `tests/test_canonical_one_dimensional.py`

- [ ] **Step 1: Write the failing generic-conversion tests**

Create `tests/test_canonical_one_dimensional.py` with these cases:

```python
from __future__ import annotations

import pandas as pd

from polynexus.core.canonical_experiments import (
    MappingProposal,
    MappingSelection,
    convert_one_dimensional_table,
)


def test_ir_csv_preserves_curve_order_units_and_source_rows(tmp_path) -> None:
    source = tmp_path / "ir.csv"
    source.write_text("Wavenumber (cm-1),Absorbance\\n1700,0.2\\n1600,0.3\\n", encoding="utf-8")

    outcome = convert_one_dimensional_table(source, technique="ir", source_artifact_id="raw-ir")

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "spectrum_1d.v1"
    measurement = outcome.template.measurements[0]
    assert measurement.channels["x"] == (1700.0, 1600.0)
    assert measurement.units == {"x": "cm^-1", "intensity": "absorbance"}
    assert measurement.source_locator["data_row_start"] == 1
    assert measurement.source_locator["data_row_end"] == 2
    assert measurement.mapping is not None and measurement.mapping.source == "observed"


def test_scattering_txt_keeps_unknown_units_as_warning_not_invented_conversion(tmp_path) -> None:
    source = tmp_path / "profile.txt"
    source.write_text("q,Intensity\\n0.1,10\\n0.2,12\\n", encoding="utf-8")

    outcome = convert_one_dimensional_table(source, technique="saxs", source_artifact_id="raw-saxs")

    assert outcome.status == "ready"
    assert outcome.template is not None
    measurement = outcome.template.measurements[0]
    assert measurement.family == "scattering_1d"
    assert measurement.units["x"] == "unknown"
    assert "coordinate_unit_unknown" in measurement.warnings
    assert measurement.channels["x"] == (0.1, 0.2)


def test_excel_yields_one_ordered_measurement_per_valid_sheet(tmp_path) -> None:
    source = tmp_path / "curves.xlsx"
    with pd.ExcelWriter(source) as writer:
        pd.DataFrame({"2theta (deg)": [10.0, 20.0], "Intensity (a.u.)": [3.0, 5.0]}).to_excel(writer, sheet_name="first", index=False)
        pd.DataFrame({"q (nm-1)": [0.1, 0.2], "I (a.u.)": [7.0, 11.0]}).to_excel(writer, sheet_name="second", index=False)

    outcome = convert_one_dimensional_table(source, technique="waxs", source_artifact_id="raw-waxs")

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert [item.source_locator["sheet_name"] for item in outcome.template.measurements] == ["first", "second"]
    assert [item.mapping.x_kind for item in outcome.template.measurements] == ["two_theta", "q"]
    assert outcome.template.measurements[1].source_locator["sheet_index"] == 1


def test_ambiguous_table_needs_input_without_a_proposal(tmp_path) -> None:
    source = tmp_path / "ambiguous.csv"
    source.write_text("A,B,C\\n1,2,3\\n2,3,4\\n", encoding="utf-8")

    outcome = convert_one_dimensional_table(source, technique="ir", source_artifact_id="raw-ambiguous")

    assert outcome.status == "needs_input"
    assert outcome.template is None
    assert outcome.reason_codes == ("conversion_mapping_ambiguous",)


def test_valid_ai_proposal_resolves_only_the_declared_table(tmp_path) -> None:
    source = tmp_path / "ambiguous.csv"
    source.write_text("A,B,C\\n1700,0.2,9\\n1600,0.3,8\\n", encoding="utf-8")
    selection = MappingSelection(
        measurement_id="sheet-0-table-0", sheet_name=None, sheet_index=None,
        table_index=0, header_row=0, data_row_start=1, data_row_end=2,
        x_column="A", intensity_column="B", x_kind="wavenumber",
        x_unit="cm^-1", intensity_unit="absorbance", source="AI proposal",
    )
    proposal = MappingProposal.create(
        source_artifact_id="raw-ambiguous", technique="ir", source="AI proposal", selections=(selection,),
    )

    outcome = convert_one_dimensional_table(
        source, technique="ir", source_artifact_id="raw-ambiguous", mapping_proposal=proposal,
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.measurements[0].mapping == selection


def test_invalid_proposal_cannot_select_a_missing_column(tmp_path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("q,Intensity\\n0.1,10\\n0.2,12\\n", encoding="utf-8")
    proposal = MappingProposal.create(
        source_artifact_id="raw-q", technique="saxs", source="user",
        selections=(MappingSelection(
            measurement_id="sheet-0-table-0", sheet_name=None, sheet_index=None,
            table_index=0, header_row=0, data_row_start=1, data_row_end=2,
            x_column="missing", intensity_column="Intensity", x_kind="q",
            x_unit="nm^-1", intensity_unit="a.u.", source="user",
        ),),
    )

    outcome = convert_one_dimensional_table(
        source, technique="saxs", source_artifact_id="raw-q", mapping_proposal=proposal,
    )

    assert outcome.status == "needs_input"
    assert outcome.reason_codes == ("conversion_mapping_proposal_invalid",)
```

- [ ] **Step 2: Run the converter tests to prove they are red**

Run:

```powershell
python -m pytest -q -p no:cacheprovider tests/test_canonical_one_dimensional.py
```

Expected: collection fails because `convert_one_dimensional_table` is not
exported.

- [ ] **Step 3: Implement deterministic inspection and conversion**

Create `one_dimensional.py` with this public signature:

```python
def convert_one_dimensional_table(
    path: str | Path,
    *,
    technique: str,
    source_artifact_id: str,
    mapping_proposal: MappingProposal | None = None,
) -> ConversionOutcome:
    ...
```

Support these extensions only: `.csv`, `.tsv`, `.txt`, `.dat`, `.asc`, `.xy`,
`.chi`, `.xls`, `.xlsx`, and `.xlsm`.  Any other extension returns a blocked
outcome with `conversion_unsupported_format`; a reader exception returns a
blocked outcome with `conversion_source_unreadable`.

Read CSV/TXT-style files with `pandas.read_csv(..., sep=None, engine="python",
comment="#")`.  Read workbooks using `pandas.ExcelFile`, then
`pandas.read_excel(..., sheet_name=sheet_name)`, in `sheet_names` order.  Treat
each sheet as exactly one table in this phase.  Drop rows only when the chosen
`x` or `intensity` value is non-numeric/non-finite; preserve the remaining row
order and calculate `data_row_start`/`data_row_end` from the original
dataframe positions plus one header row.  If no sheet/table produces two
finite paired points, return `needs_input` with `conversion_no_numeric_table`.

Use the following deterministic header aliases after case-folding, removal of
spaces/underscores/hyphens, and conversion of Unicode theta to `theta`:

```python
X_ALIASES = {
    "ir": {"wavenumber": "wavenumber", "wavenumbercm1": "wavenumber", "cm1": "wavenumber"},
    "scattering": {"q": "q", "qnm1": "q", "qangstrom1": "q", "2theta": "two_theta", "twotheta": "two_theta", "theta2": "two_theta"},
}
INTENSITY_ALIASES = {"absorbance", "transmittance", "intensity", "i", "counts", "count", "cps"}
```

An IR source accepts only a resolved `wavenumber` x channel and produces
`template_id="spectrum_1d.v1"`, `family="spectrum_1d"`.  SAXS/WAXS accept a
resolved `q` or `two_theta` x channel and produce
`template_id="scattering_1d.v1"`, `family="scattering_1d"`.  Do not inspect a
material label or filepath name.  A table with exactly one eligible x header
and one eligible intensity header receives observed mapping.  More than one
eligible candidate (or no candidate) is ambiguous unless a valid proposal
selects exact existing headers for that table.

Infer units from selected header text only:

- `wavenumber`: `cm^-1` for `cm-1`, `cm^-1`, `1/cm`, or `cm⁻¹`;
- `q`: `nm^-1` for `nm-1`, `nm^-1`, or `nm⁻¹`; `angstrom^-1` for `a-1`,
  `å-1`, or `angstrom-1`;
- `two_theta`: `deg` for `deg`, `degree`, or `°`;
- intensity: `absorbance`, `transmittance`, `counts`, `cps`, or `a.u.` only
  when its header states that form.

Otherwise retain literal `"unknown"`; do not apply a conversion factor, and
append `coordinate_unit_unknown` or `intensity_unit_unknown` to the
measurement warnings.  Create the source locator with the exact path string
from `Path(path).resolve()`, the required flat-file/worksheet identifiers, and
zero-based point range.  Add `background_state="unknown"` and
`normalization_state="unknown"` to `acquisition_metadata` for scattering;
do not derive either state.

Validate proposals before extracting arrays: proposal artifact and normalized
technique must equal the function arguments; every selection must identify an
existing sheet/table and exact x/intensity headers; x kind must fit the
technique; and selection source must equal proposal source.  A failure returns
`needs_input` with `conversion_mapping_proposal_invalid`, with no template.
Do not partially apply a proposal.  A fully valid proposal becomes the
template's `mapping_proposal`, and each selected measurement's mapping is the
selection as supplied.

Build the `ConversionRecord` with `conversion_id="generic.one-dimensional.v1"`,
observed columns formatted as `"<sheet-or-flat>:<header>"`, each measurement's
locator in `extracted_segments`, and all measurement warning codes.  Use
`CanonicalExperiment.create(..., measurements=..., mapping_proposal=...)`.
Export the function in `__init__.py`.

- [ ] **Step 4: Run all 1D conversion and canonical compatibility tests**

Run:

```powershell
python -m pytest -q -p no:cacheprovider tests/test_canonical_one_dimensional.py tests/test_canonical_measurements.py tests/test_canonical_experiment_templates.py tests/test_dsc_canonical_isothermal_conversion.py
```

Expected: all tests pass.  The Excel test may use `openpyxl` already listed in
the project dependencies; it must not create a workbook inside the repository.

- [ ] **Step 5: Commit the generic converter**

```powershell
python scripts/auto_commit.py `
  --message "feat(core): convert generic one-dimensional tables" `
  --files polynexus/core/canonical_experiments/one_dimensional.py polynexus/core/canonical_experiments/__init__.py tests/test_canonical_one_dimensional.py
```

Expected: one local commit containing exactly the generic converter, its
public export, and its focused test.

## Task 4: Record the phase checkpoint and run structured verification

**Files:**
- Modify: `docs/agent/tasks/2026-08-24-universal-canonical-templates-phase1.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run the focused test matrix**

Run:

```powershell
python -m pytest -q -p no:cacheprovider tests/test_canonical_measurements.py tests/test_canonical_one_dimensional.py tests/test_canonical_experiment_templates.py tests/test_dsc_canonical_isothermal_conversion.py tests/test_canonical_converter_registry.py
```

Expected: all tests pass.  The registry test proves that the existing
compatibility registry was not changed by this phase.

- [ ] **Step 2: Run required structured verification**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-24-universal-canonical-templates-phase1.md --changed --types
git diff --check
```

Expected: both commands exit `0`.  Do not run a full repository matrix; this
is a structured architecture task but it does not integrate a release route.

- [ ] **Step 3: Update task state and durable memory**

Set the task-card status to `implementation_complete_review_required`.  Add
one dated `active-work.md` entry containing only these durable facts:

```markdown
## Universal canonical templates phase 1 - checkpointed 2026-08-24

- Generic one-dimensional CSV/TXT/Excel conversion now creates immutable
  `spectrum_1d.v1` and `scattering_1d.v1` measurements with source locators,
  declared/unknown units, and observed/user/AI-proposal mapping provenance.
- Ambiguous mappings become `needs_input`; validated source-bound proposals
  may resolve them.  No material label, numerical algorithm, engine, registry,
  GUI, CLI, Batch, Codex, DSC, or NMR path changed.
- Capability item contracts exist but are not attached to `ComputeRun` until
  the separate capability-routing task.  Next: general DSC template design or
  approved capability-routing migration, followed by consumer migration.
```

- [ ] **Step 4: Commit the verified checkpoint**

```powershell
python scripts/auto_commit.py `
  --message "docs(core): record canonical template phase one" `
  --files docs/agent/tasks/2026-08-24-universal-canonical-templates-phase1.md docs/agent/memory/active-work.md
```

Expected: one local commit containing only the task completion record and the
durable memory entry.  Architecture and scientific-semantics review remain
required before this branch is merged.

## Acceptance checklist

- [ ] Generic conversion makes no decision from PA6/PA11/PA12 or any material
  label, filename group, paper metadata, RAG result, or review state.
- [ ] Every canonical numeric channel is finite and retains acquisition order.
- [ ] Every successful measurement includes the required source locator and
  mapping source; unknown units stay unknown with a warning.
- [ ] Ambiguous or invalid mappings are explicit `needs_input`, not fabricated
  curves; a bad proposal cannot produce a partial template.
- [ ] A valid workbook preserves sheet order and produces independent curves.
- [ ] Existing DSC conversion and the existing registry retain their focused
  regression behavior.
- [ ] No capability executes and no public application entry point changes.

## Plan self-review

**Spec coverage:** Task 2 implements immutable measurements, provenance source
labels, and future capability-item statuses.  Task 3 implements generic
CSV/TXT/XLSX conversion, `spectrum_1d.v1`/`scattering_1d.v1`, units, source
locators, deterministic/AI-user mapping, ambiguity, and no material shortcut.
Task 4 preserves the DSC/registry boundary and records the later capability
and consumer work.  DSC generalization, capability execution, Batch/Codex
migration, replay, and deletion are explicitly excluded because they belong to
separate design-approved slices.

**Placeholder scan:** This plan contains no deferred-work markers, “implement later,”
or implicit “appropriate validation” instructions.  Every task names concrete
files, tests, status/reason values, commands, and expected outcomes.

**Type consistency:** `MappingSelection` is the only table-column selection
type; `MappingProposal.selections`, `Measurement.mapping`, and the converter
all use it.  `Measurement` uses `family`, `channels`, `units`, and
`source_locator` consistently.  `CapabilityItemResult` is intentionally a
standalone contract; `ComputeRun` remains unchanged in this phase.
