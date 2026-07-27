# SAXS 1D Method Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为现有 Porod、Kratky、不变量和层片结果建立统一的可解释证据映射。

**Architecture:** 在质量契约层提供四个只读方法 builder，输出现有 `MetricEvidence`。`analyze_single` 继续运行原有算法，只在结果已有后把四项字典挂载到 `SAXSResult.metric_evidence`；任何新证据失败都降级并保留原有数值结果。

**Tech Stack:** Python dataclasses, NumPy, pytest, existing SAXS core.

---

### Task 1: Write failing method-evidence tests

**Files:**
- Create: `tests/test_saxs_1d_method_evidence.py`

- [ ] Define synthetic `DataQualityReport` fixtures and minimal existing Porod/Kratky/Structure payloads.
- [ ] Write one clean and one missing/unknown-applicability test for each of `build_porod_evidence`, `build_kratky_evidence`, `build_invariant_evidence`, and `build_lamellar_evidence`.
- [ ] Assert every output is `MetricEvidence`, unknown applicability is `Diagnostic`, unusable quality is `Unusable`, and `contract_json` accepts the payload.
- [ ] Run `pytest tests/test_saxs_1d_method_evidence.py -q`; confirm RED because the builders do not exist.

### Task 2: Implement four conservative builders

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `polynexus/core/saxs_engine/__init__.py`

- [ ] Implement these signatures without mutating payloads:

```python
def build_porod_evidence(porod: Mapping[str, Any] | None, *, quality_report: DataQualityReport, applicability: str = "unknown", source_ref: str = "") -> MetricEvidence: ...
def build_kratky_evidence(kratky: Mapping[str, Any] | None, *, quality_report: DataQualityReport, applicability: str = "unknown", source_ref: str = "") -> MetricEvidence: ...
def build_invariant_evidence(q_star: Any, *, quality_report: DataQualityReport, valid: bool = True, beam_stop_contaminated: bool = False, applicability: str = "unknown", source_ref: str = "") -> MetricEvidence: ...
def build_lamellar_evidence(long_period: Any, structure: Any, *, quality_report: DataQualityReport, applicability: str = "unknown", source_ref: str = "") -> MetricEvidence: ...
```

- [ ] Use only finite/positive checks, existing payload point counts/ranges, and explicit applicability; cap every builder at `Trend` and emit method-specific reason codes rather than new physical cutoffs.
- [ ] Export the four builders and keep `MetricEvidence.from_dict/to_dict` round-trippable.
- [ ] Run focused tests and confirm GREEN.

### Task 3: Propagate evidence to `SAXSResult`

**Files:**
- Modify: `polynexus/core/saxs_engine/core.py`
- Modify: `tests/test_saxs_1d_method_evidence.py`
- Modify: `tests/test_saxs_result_contract.py`

- [ ] Add `metric_evidence: Dict[str, Any] = None` to `SAXSResult` without changing existing fields.
- [ ] After existing `result.porod`, `result.kratky`, and `result.structure` are populated, build the four evidence dictionaries using the current `quality_report` and `cfg.condition_context` applicability keys (`porod_applicability`, `kratky_applicability`, `invariant_applicability`, `lamellar_applicability`), defaulting to `unknown`.
- [ ] Catch builder exceptions per metric, emit a JSON-safe diagnostic payload with `metric_evidence_build_failed`, and leave the original analysis outputs untouched.
- [ ] Assert a synthetic `analyze_single` result retains legacy outputs and contains all four evidence keys.

### Task 4: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-27-saxs-1d-method-evidence.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/superpowers/plans/2026-07-27-saxs-1d-method-evidence.md`

- [ ] Run the task-scoped verifier with an external basetemp and `git diff --check`.
- [ ] Record exact focused/full/quality/preprocessing results and known limitations.
- [ ] Use `scripts/auto_commit.py` with the explicit allowlist and no push/merge/deploy.
