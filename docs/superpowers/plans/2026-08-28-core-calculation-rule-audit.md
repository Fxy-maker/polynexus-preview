# Core Calculation Rule-Tier Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a read-only, evidence-backed ledger that distinguishes structural calculation blocks from calculation warnings and manuscript-evidence restrictions across the five supported techniques.

**Architecture:** The audit consumes existing canonical conversion outcomes, provider/Core result contracts, `ComputeRun` projections, and writing metrics. It writes one acceptance ledger and does not alter any producer or consumer behavior. Each candidate rule is traced from its implementation condition to the public status and evidence outcome before a recommendation is made.

**Tech Stack:** Python source inspection, pytest existing focused matrices, `ComputeRun` contracts, Markdown acceptance records, Git verification helpers.

---

### Task 1: Establish the shared audit ledger and public-route map

**Files:**
- Create: `docs/acceptance/2026-08-28-core-calculation-rule-audit.md`
- Modify: `docs/agent/tasks/2026-08-28-core-calculation-rule-audit.md`

- [x] **Step 1: Create the ledger header and exact row schema**

Create a Markdown table with these columns:

```markdown
| Technique | Rule / owner | Trigger | Current computation outcome | Current evidence outcome | Observed tier | Recommended tier | Evidence | Follow-up |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

Add a short invariant directly above the table: a recommendation is invalid
unless it names both the producer condition and the public `ComputeRun` or
writing-metric outcome.

- [x] **Step 2: Map the shared public boundaries before inspecting technique rules**

Read only these producers and consumers:

```powershell
rg -n "class ComputeRunService|def run_direct|def extract_writing_metrics|def _dsc\(|def _ir\(|def _saxs\(|def _waxs\(|def _nmr\(" polynexus/core/compute polynexus/core/project_workflow/writing_metrics.py
rg -n "default_converter_registry|convert_|conversion_mapping_ambiguous|needs_input|blocked" polynexus/core/canonical_experiments polynexus/core/compute
```

Record the one shared path from converter to `ComputeRun` to writing metrics;
do not list GUI implementation details unless a consumer changes a public
status or hides a retained result.

- [x] **Step 3: Verify the documentation-only starting boundary**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-28-core-calculation-rule-audit.md --changed --types
```

Expected: task/memory checks and repository quality gates pass with no changed
Python files selected for linting.

### Task 2: Audit DSC and FTIR calculation-vs-evidence behavior

**Files:**
- Modify: `docs/acceptance/2026-08-28-core-calculation-rule-audit.md`
- Read: `polynexus/core/dsc.py`, `polynexus/core/dsc_engine/dsc_kinetics.py`, `polynexus/core/ir_engine/`, `polynexus/core/project_workflow/writing_metrics.py`
- Read tests: `tests/test_dsc_kinetics.py`, `tests/test_dsc_canonical_isothermal_conversion.py`, `tests/test_ftir_no_auto_material_identification.py`, `tests/test_project_writing_metrics.py`

- [x] **Step 1: Extract DSC conditions that stop an event, a regression, or only publication use**

Use this targeted search:

```powershell
rg -n -C 3 "return np\.array\(\[\]\)|quality_flags|too_few|no_positive|zero_|no_valid|endpoint_baseline|baseline_sensitive|too_few_rates" polynexus/core/dsc_engine/dsc_kinetics.py polynexus/core/dsc.py
```

For every candidate, record whether it removes a scalar calculation, retains a
row with a quality flag, or only changes `writing_eligibility`. Use the
existing adaptive-baseline acceptance as evidence for the retained-with-warning
path; do not reopen its numerical semantics.

- [x] **Step 2: Extract FTIR conversion, assignment, and material-context conditions**

Run:

```powershell
rg -n -C 3 "raise |blocked|needs_input|material|assignment|calibration|diagnostic_only|results_candidate" polynexus/core/ir_engine polynexus/core/canonical_experiments/one_dimensional.py polynexus/core/project_workflow/writing_metrics.py
```

Separate ambiguous axis/value mapping from absent material identity and absent
literature-backed peak assignment. The first may be structural; the latter two
must be checked for retained generic spectra and diagnostic metrics.

- [x] **Step 3: Run existing targeted proof**

```powershell
python -m pytest -p no:cacheprovider -q tests/test_dsc_kinetics.py tests/test_dsc_canonical_isothermal_conversion.py tests/test_ftir_no_auto_material_identification.py tests/test_project_writing_metrics.py
```

Expected: existing contracts pass; any failed test is recorded as a current
implementation issue, not reclassified by assertion alone.

### Task 3: Audit SAXS and WAXS structural inputs, metrics, and evidence gates

**Files:**
- Modify: `docs/acceptance/2026-08-28-core-calculation-rule-audit.md`
- Read: `polynexus/core/saxs_engine/`, `polynexus/core/waxs_engine/`, `polynexus/core/saxs.py`, `polynexus/core/waxs.py`, `polynexus/core/project_workflow/writing_metrics.py`
- Read tests: `tests/test_saxs_1d_method_evidence.py`, `tests/test_saxs_mode_evidence_contract.py`, `tests/test_waxs_publication_cutover.py`, `tests/test_project_writing_metrics.py`

- [x] **Step 1: Separate unreadable/uncalibrated arrays from interpretation gates**

Run:

```powershell
rg -n -C 3 "raise |blocked|nonfinite|shape_mismatch|q_|background|calibration|diagnostic_only|applicable|reliability" polynexus/core/saxs_engine polynexus/core/saxs.py polynexus/core/waxs_engine polynexus/core/waxs.py
```

Classify invalid q/intensity arrays, invalid detector geometry, and impossible
array shapes separately from background sufficiency, peak support, phase
assignment, and Scherrer/lamellar reliability.

- [x] **Step 2: Trace every candidate metric to its writing eligibility**

Use:

```powershell
Get-Content polynexus/core/project_workflow/writing_metrics.py | Select-Object -Skip 200 -First 170
rg -n -C 4 "metric_evidence|physical_support_pass|size_reliability_status|applicable" polynexus/core/saxs_engine polynexus/core/waxs_engine
```

For each finite metric that is diagnostic-only, record whether the Core still
returns it. A “yes” is an evidence restriction, not a calculation blocker.

- [x] **Step 3: Run existing focused proof**

```powershell
python -m pytest -p no:cacheprovider -q tests/test_saxs_1d_method_evidence.py tests/test_saxs_mode_evidence_contract.py tests/test_waxs_publication_cutover.py tests/test_project_writing_metrics.py
```

Expected: all selected tests pass or any failure is captured in the ledger with
its exact owner and no behavior change.

### Task 4: Audit NMR and cross-entry result visibility

**Files:**
- Modify: `docs/acceptance/2026-08-28-core-calculation-rule-audit.md`
- Read: `polynexus/core/nmr_engine/`, `polynexus/core/canonical_experiments/one_dimensional.py`, `polynexus/core/compute/service.py`, `polynexus/core/project_workflow/writing_metrics.py`
- Read tests: `tests/test_nmr_shared_entry.py`, `tests/test_nmr_engine.py`, `tests/test_compute_service.py`, `tests/test_evidence_package_view.py`

- [x] **Step 1: Separate generic spectral calculation from polymer/phase claims**

Run:

```powershell
rg -n -C 3 "raise |blocked|assignment|phase|Xc|material|diagnostic_only|quality_flags" polynexus/core/nmr_engine polynexus/core/canonical_experiments/one_dimensional.py
```

Record whether ppm-axis/spectral metrics remain available without a material
name and whether only solid-state phase/`Xc` promotion remains restricted.

- [x] **Step 2: Check shared consumers for status loss**

Run:

```powershell
rg -n -C 3 "warnings|metrics|diagnostic_only|results_candidate|quality_flags|ComputeRun" polynexus/core/compute/service.py polynexus/core/project_workflow/writing_metrics.py polynexus/gui tests/test_evidence_package_view.py
```

Only create a ledger row if a public warning or retained metric is dropped,
renamed into a stronger claim, or hidden by a consumer. Do not audit unrelated
GUI layout behavior.

- [x] **Step 3: Run existing cross-entry proof**

```powershell
python -m pytest -p no:cacheprovider -q tests/test_nmr_shared_entry.py tests/test_nmr_engine.py tests/test_compute_service.py tests/test_evidence_package_view.py
```

Expected: the shared route retains supported generic results and explicit
diagnostic limits without a technique-private consumer path.

### Task 5: Publish recommendations without changing rules

**Files:**
- Modify: `docs/acceptance/2026-08-28-core-calculation-rule-audit.md`
- Modify: `docs/agent/tasks/2026-08-28-core-calculation-rule-audit.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Add the prioritized recommendation section**

For every candidate proposed to move from `structural_block` to
`calculation_warning`, include this exact decision record:

```markdown
### Candidate: <stable rule name>

- Current behavior: <producer and public outcome>
- Why a finite result can or cannot exist: <mathematical/scientific basis>
- Proposed tier: <calculation_warning | retain structural_block>
- Evidence boundary after any future change: <diagnostic_only | existing policy>
- Required future regression: <test path and assertion>
```

List no code change under this task; each accepted candidate must become its
own task card and test-first implementation.

- [x] **Step 2: Record completion evidence and remaining decisions**

Update the task card with ledger count, exact test results, and any rules that
need the user's scientific decision. Update `active-work.md` only with durable
audit findings, not raw command output.

- [x] **Step 3: Verify and checkpoint the audit**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-28-core-calculation-rule-audit.md --changed --types
git diff --check
python scripts/auto_commit.py --message "docs(core): audit calculation rule tiers" --files docs/acceptance/2026-08-28-core-calculation-rule-audit.md docs/agent/tasks/2026-08-28-core-calculation-rule-audit.md docs/agent/memory/active-work.md docs/superpowers/plans/2026-08-28-core-calculation-rule-audit.md
```

Expected: the checkpoint contains only audit documents, is local-only, and
does not modify source data, Core behavior, or existing pre-existing files.

## Plan self-review

- Spec coverage: Tasks 1–4 cover the five techniques and all shared public
  boundaries; Task 5 publishes the evidence-backed, non-automatic follow-up.
- Scope: no production file appears in a Modify entry, so this is an audit and
  not an implicit gate-relaxation change.
- Type consistency: all classifications use the three terms defined by the
  specification: `structural_block`, `calculation_warning`, and
  `evidence_restriction`.
