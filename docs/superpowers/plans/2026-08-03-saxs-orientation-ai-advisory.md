# SAXS Orientation AI Advisory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a one-shot, read-only AI advisory that ranks only existing SAXS orientation candidates and renders deterministic evidence-backed review guidance.

**Architecture:** Core builds and digests a fixed sanitized context, the RAG layer invokes a separate advisory prompt/response namespace, and core validates IDs/codes before hydrating every number and sentence from source evidence. A dedicated GUI worker displays and persists the detached report but has no candidate, confirmation, rerun, config, or publication route.

**Tech Stack:** Python 3.12+, dataclasses, SHA-256, strict JSON, existing LLM/RAG client, PySide6 QThread, pytest.

---

## Dependency gate

Do not start until Tasks 1-4 are checkpointed and candidate, track,
reliability, correction-ledger, and review-context schemas are stable. If the
identities or digests change, stop and update this plan through scientific
review; do not make the parser accept arbitrary fields.

## File map

- Create `polynexus/core/saxs_engine/saxs_orientation_advisory.py`: fixed context projection, digest, strict model-response parser, deterministic hydration/fallback.
- Modify `polynexus/core/saxs_engine/saxs_2d_review_context.py`: expose bounded source DTOs to the advisory projector only.
- Modify `polynexus/core/saxs_engine/saxs_ai_rescue.py`: explicitly reject advisory payloads at rescue/confirmation boundaries.
- Modify `polynexus/core/saxs_engine/__init__.py`: exports.
- Modify `polynexus/core/saxs_batch_helpers.py`: detached report copy field.
- Modify `rag/prompt_builder.py`: separate advisory prompt with code-only output schema.
- Modify `rag/advisor.py`: separate `advise_saxs_orientation()` entry point.
- Create `polynexus/gui/saxs_orientation_advisory_service.py`: eligibility and persistence-safe presentation adapter.
- Modify `polynexus/gui/main_window_workers.py`: dedicated one-shot advisory worker.
- Modify `polynexus/gui/main_window_results_mixin.py`: review action and display only.
- Modify `polynexus/gui/saxs_results_table_service.py`: deterministic advisory display.
- Modify `polynexus/gui/analysis_history_service.py`: restore persisted detached report.
- Modify `polynexus/data/sample_db.py`: update one run's parameters JSON without schema change.
- Modify `polynexus/gui/i18n.py`: deterministic labels for allowlisted codes.
- Add and extend the focused safety tests in the task card and this plan.

### Task 1: Build the fixed sanitized advisory context

- [ ] **Step 1: Add RED exclusion and digest tests**

```python
def test_orientation_advisory_context_drops_raw_arrays_paths_and_unknown_fields() -> None:
    context = build_orientation_advisory_context(result_with_raw_and_unknown_fields())
    encoded = json.dumps(context, allow_nan=False, sort_keys=True)
    assert "detector_pixels" not in encoded
    assert "source_path" not in encoded
    assert "unknown_prompt" not in encoded
    assert context["schema_version"] == "saxs-orientation-advisory-context-v1"


def test_orientation_advisory_digest_is_stable_and_source_bound() -> None:
    first = build_orientation_advisory_context(two_candidate_result())
    second = build_orientation_advisory_context(two_candidate_result())
    assert first["source_evidence_digest"] == second["source_evidence_digest"]
    changed = build_orientation_advisory_context(two_candidate_result(delta=0.02))
    assert changed["source_evidence_digest"] != first["source_evidence_digest"]
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_orientation_ai_advisory.py tests/test_saxs_2d_ai_context_bridge.py -q`

- [ ] **Step 3: Define fixed source projections**

```python
_CANDIDATE_FIELDS = (
    "candidate_id", "track_id", "feature_kind", "q_min_nm1", "q_max_nm1",
    "f_reference", "f_principal_raw", "delta_f_from_zero",
    "stability_interval", "sensitivity_summary", "reference_axis_kind",
    "reference_axis_deg", "convention", "reliability_status", "reason_codes",
)
_LEDGER_FIELDS = ("operation", "status", "input_digest", "output_digest", "reason_codes")
```

Build a new wrapper schema rather than changing the meaning of
`saxs-2d-review-v1`:

```python
{
    "schema_version": "saxs-orientation-advisory-context-v1",
    "technique": "SAXS",
    "scope": "saxs.orientation.advisory",
    "review_context": sanitize_saxs_2d_review_context(existing_context),
    "candidates": sorted(projected_candidates, key=lambda x: x["candidate_id"]),
    "correction_ledger": projected_ledger,
    "gates": copied_gate_fields,
    "source_evidence_digest": canonical_digest(payload_without_digest),
}
```

Reject duplicate/unsafe IDs and exclude raw q arrays, pixels, paths,
calibration arrays, arbitrary parameters, and unknown nested fields.

- [ ] **Step 4: Add limitations-first context state**

When there are no eligible `usable` or `diagnostic` candidates, keep the fixed
review/gate evidence and emit `status="limited"` with source-derived reason
codes. Do not fabricate a candidate so the model has something to rank.

- [ ] **Step 5: Run context GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_orientation_ai_advisory.py tests/test_saxs_2d_ai_context_bridge.py -q`

### Task 2: Define a code-only model response and deterministic report

- [ ] **Step 1: Add RED parser tests**

```python
def test_model_response_accepts_only_existing_ids_and_allowlisted_codes() -> None:
    response = {
        "schema_version": "saxs-orientation-advisory-response-v1",
        "source_evidence_digest": "digest-1",
        "ranked_candidate_ids": ["band-b", "band-a"],
        "candidate_rationale_codes": {
            "band-b": ["stable_common_q_support"],
            "band-a": ["artifact_sensitivity_present"],
        },
        "review_action_codes": ["inspect_q_band", "verify_tensile_axis"],
    }
    parsed = parse_orientation_advisory_response(response, source_context())
    assert parsed.ranked_candidate_ids == ("band-b", "band-a")


@pytest.mark.parametrize("extra", [
    {"f_reference": 0.99},
    {"explanation": "This is a chain-axis feature"},
    {"changes": {"beam_center_x": 10}},
    {"saxs_candidate_references": ["temperature-rescue-1"]},
])
def test_model_response_rejects_numeric_free_text_mutation_and_rescue_fields(extra) -> None:
    payload = valid_response() | extra
    with pytest.raises(OrientationAdvisoryValidationError):
        parse_orientation_advisory_response(payload, source_context())
```

- [ ] **Step 2: Implement exact response allowlists**

Allowed rationale codes:

```python
RATIONALE_CODES = frozenset({
    "stable_common_q_support",
    "wide_stability_bound",
    "artifact_sensitivity_present",
    "reference_axis_missing",
    "calibration_unavailable",
    "systematic_harmonic_suspected",
    "local_evidence_diagnostic",
})
REVIEW_ACTION_CODES = frozenset({
    "inspect_q_band",
    "verify_tensile_axis",
    "acquire_background_standard",
    "inspect_beam_center",
    "compare_mask_sensitivity",
    "request_scientific_review",
})
```

The parser requires exact schema and digest, unique existing candidate IDs,
known top-level keys, and known codes. It accepts no number, free-text field,
candidate object, physical label, config, preprocess intent, or gate decision.

- [ ] **Step 3: Hydrate the final report locally**

```python
@dataclass(frozen=True)
class OrientationAdvisoryReport:
    schema_version: str
    ranked_candidate_ids: tuple[str, ...]
    candidate_observations: tuple[Mapping[str, Any], ...]
    comparison_summary_codes: tuple[str, ...]
    artifact_risk_codes: tuple[str, ...]
    recommended_review_action_codes: tuple[str, ...]
    limitation_codes: tuple[str, ...]
    source_evidence_digest: str
    status: str
    reason_codes: tuple[str, ...]
```

Copy every q/Herman/delta/stability/sensitivity value from the source context
by ID. Build summary and limitation codes deterministically from source gates
and response codes. UI translations render the sentences; model prose is never
stored or displayed.

- [ ] **Step 4: Implement deterministic fallback**

On model/network/parse/digest failure, preserve source candidate observations
in stable ID order, leave ranking empty, add `advisory_model_unavailable` or the
specific validation reason, and recommend only source-authorized review action
codes. Never retry through tuning or rescue.

- [ ] **Step 5: Run parser/hydration GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_orientation_ai_advisory.py -q`

### Task 3: Add a separate RAG invocation path

- [ ] **Step 1: Add RED Advisor and prompt tests**

```python
def test_orientation_advisory_prompt_has_no_tuning_or_apply_schema() -> None:
    prompt = PromptBuilder().build_saxs_orientation_advisory(source_context())
    assert '"ranked_candidate_ids"' in prompt
    assert '"changes"' not in prompt
    assert "PreprocessIntent" not in prompt
    assert "saxs_candidate_references" not in prompt


def test_orientation_advisor_never_calls_generic_tuning_normalizer(fake_llm) -> None:
    advisor = Advisor(llm_client=fake_llm)
    report = advisor.advise_saxs_orientation(source_context())
    assert "changes" not in report.to_dict()
    assert "preprocess_intent" not in report.to_dict()
```

- [ ] **Step 2: Add `PromptBuilder.build_saxs_orientation_advisory()`**

The prompt embeds only the already sanitized context and exact response schema.
It asks for candidate IDs and codes only. Do not include retrieved-case numeric
content, generic tuning fields, raw sample metadata, or a free-text reasoning
slot.

- [ ] **Step 3: Add `Advisor.advise_saxs_orientation()`**

This method does not call `advise()`, `_normalize_advice()`, preprocess intent
parsers, candidate-reference normalizers, or the tuning orchestrator. It calls
the LLM once in JSON mode, then delegates parsing/hydration to core. The method
returns `OrientationAdvisoryReport`, not a generic tuning dictionary.

- [ ] **Step 4: Add negative rescue/orchestrator assertions**

`validate_saxs_ai_intent()`, sequence rescue resolution, confirmation report
validation, and `PreprocessTransactionService.begin_confirmation()` must reject
or ignore `orientation_advisory_report`. Tests patch those functions and assert
zero calls during advisory execution.

- [ ] **Step 5: Run RAG safety GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_advisor.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_saxs_ai_orchestrator_handoff.py -q`

### Task 4: Add read-only GUI display and persistence

- [ ] **Step 1: Add RED GUI/service tests**

```python
def test_advisory_action_is_visible_only_for_stable_saxs_orientation_context() -> None:
    state = orientation_advisory_action_state(valid_strain_result())
    assert state.visible is True
    assert state.enabled is True
    assert orientation_advisory_action_state(waxs_result()).visible is False


def test_advisory_worker_has_no_apply_or_rerun_signal() -> None:
    worker = SAXSOrientationAdvisoryWorker(source_context(), advisor_factory=fake_advisor)
    assert not hasattr(worker, "apply")
    assert not hasattr(worker, "rerun")
```

- [ ] **Step 2: Add a dedicated one-shot worker**

`SAXSOrientationAdvisoryWorker` receives the detached sanitized context and an
Advisor factory. It emits only `finished(report)`, `error_msg(text)`, and
`cancelled`. It receives no engine, config, source path, mask, transaction
service, or output directory.

- [ ] **Step 3: Add the Results review action**

Add an icon+text secondary action to the existing Results review action row.
It is visible only for `saxs.strain` with advisory context, and disabled while
running. Completion attaches a detached report to current result parameters,
refreshes result presentation, and logs the report status. There is no Apply,
Accept, Rerun, Promote, or Use-axis control.

- [ ] **Step 4: Render deterministic text**

`saxs_results_table_service.py` maps report IDs/codes through i18n and displays
rank order, copied observations, limitations, artifact risks, and recommended
review actions. Unknown codes render as unavailable, never raw model text.

- [ ] **Step 5: Persist without schema migration**

Add `SampleDB.update_analysis_parameters(run_id, parameters)` that updates only
the existing JSON `parameters` column after verifying the run exists. Persist
`orientation_advisory_report` with its digest and schema. History restore
passes the detached report through the same result-table service. It never
marks the run AI-tuned, confirmed, reviewed, or publication-ready.

- [ ] **Step 6: Run GUI/persistence GREEN**

Run: `python -m pytest -p no:cacheprovider tests/test_saxs_results_table_service.py tests/test_saxs_ai_confirmation_gui_route.py tests/test_main_window_persistence.py tests/test_sample_db.py -q`

### Task 5: Verify and checkpoint

- [ ] **Step 1: Run required verification**

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_orientation_ai_advisory.py tests/test_saxs_2d_ai_context_bridge.py tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_advisor.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_orchestrator_handoff.py tests/test_saxs_ai_confirmation_gui_route.py tests/test_saxs_results_table_service.py tests/test_main_window_persistence.py tests/test_sample_db.py -q
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
$env:PYTHONUTF8='1'
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-orientation-ai-advisory.md --changed --types
git diff --check
```

- [ ] **Step 2: Run fault and prompt-injection acceptance**

Use fake model responses containing unknown IDs, duplicated IDs, stale digest,
numbers, physical labels, paths, config changes, preprocess intents, rescue
references, unsupported actions, truncated JSON, and prompt-injection strings.
Every case must return a deterministic limitations report and make zero calls
to apply/rerun/confirmation/publication APIs.

- [ ] **Step 3: Perform restarted-GUI review**

Open one qualifying SAXS strain result, run the advisory, inspect deterministic
ranking/limitations, restart, restore history, and verify the same report is
shown with no action control. Test model failure and confirm the analysis,
config, masks, axes, result values, review status, and publication status are
unchanged.

- [ ] **Step 4: Review and checkpoint the exact allowlist**

```powershell
python scripts/auto_commit.py --message "feat(saxs): add read-only orientation advisory" --files polynexus/core/saxs_engine/saxs_orientation_advisory.py polynexus/core/saxs_engine/saxs_2d_review_context.py polynexus/core/saxs_engine/saxs_ai_rescue.py polynexus/core/saxs_engine/__init__.py polynexus/core/saxs_batch_helpers.py rag/advisor.py rag/prompt_builder.py polynexus/gui/saxs_orientation_advisory_service.py polynexus/gui/main_window_workers.py polynexus/gui/main_window_results_mixin.py polynexus/gui/saxs_results_table_service.py polynexus/gui/analysis_history_service.py polynexus/gui/i18n.py polynexus/data/sample_db.py tests/test_saxs_orientation_ai_advisory.py tests/test_saxs_2d_ai_context_bridge.py tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_advisor.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_orchestrator_handoff.py tests/test_saxs_ai_confirmation_gui_route.py tests/test_saxs_results_table_service.py tests/test_main_window_persistence.py tests/test_sample_db.py docs/agent/tasks/2026-08-03-saxs-orientation-ai-advisory.md
```

Do not push. The finished program still requires human scientific review; AI
advisory evidence is not acceptance or publication authority.
