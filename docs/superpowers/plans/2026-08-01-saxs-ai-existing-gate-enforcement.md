# SAXS AI Existing Gate Enforcement Implementation Plan

> **For agentic workers:** Execute this plan in order. Steps use checkbox syntax and preserve the existing SAXS gate as the scientific authority.

**Goal:** Make SAXS AI candidate decisions fail closed unless the existing SAXS physical and quality assessment accepts the candidate trial.

**Architecture:** Keep generic preprocessing scoring intact, then compose a SAXS-only post-trial guard in `orchestrator_preprocess.py`. The guard delegates to `assess_saxs_confirmed_rerun()`, records compact gate evidence in `PreprocessEvidence.technique_specific`, and downgrades failed trials to `keep_original` before ranking or applying them.

**Tech Stack:** Python, pytest, existing SAXS result contracts, and the repository structured verifier.

---

### Task 1: Lock the missing gate with a RED regression

**Files:**
- Modify: `tests/test_saxs_ai_orchestrator_handoff.py`

- [x] **Step 1: Make the fake trial expose existing gate evidence**

  Add explicit `data_quality_report`, `guinier_evidence`, `metric_evidence`,
  `quality_flag`, and `Q_star_valid` fields to the fake result. Parameterize
  the fake engine's quality level so a candidate can return `Diagnostic` while
  its generic preprocessing metrics remain unchanged.

- [x] **Step 2: Add the failing behavior assertion**

  Run a calibrated SAXS orchestrator with a candidate trial whose
  `data_quality_report.level` is `Diagnostic`. Assert:

  ```python
  assert report["saxs_ai_rescue_decision"]["decision"] == "keep_original"
  assert report["saxs_ai_rescue_decision"]["apply_allowed"] is False
  assert report["saxs_ai_rescue_replay"][0]["apply_performed"] is False
  ```

- [x] **Step 3: Run RED**

  ```powershell
  python -m pytest -q tests/test_saxs_ai_orchestrator_handoff.py -o addopts=
  ```

  Expected before production change: the new test fails because generic
  preprocessing scoring can still produce `auto_accept`.

### Task 2: Compose the existing SAXS gate

**Files:**
- Modify: `polynexus/orchestrator_preprocess.py`
- Read: `polynexus/core/saxs_engine/saxs_ai_rescue.py`

- [x] **Step 1: Add a SAXS-only decision guard**

  After `SAXSPreprocessAdapter.build_evidence()` and before the trial is
  ranked, call `assess_saxs_confirmed_rerun(trial_engine, mode=...)`. Add
  `saxs_existing_quality_gate` and `saxs_existing_physical_gate` to the
  decision hard guards. When either is false, return a copied decision with
  `decision="keep_original"`, `simulated_decision="keep_original"`,
  `confidence_band="low"`, score `0.0`, and deterministic reason codes from
  the existing assessment. Preserve the candidate and audit row.

- [x] **Step 2: Record detached gate evidence**

  Store only the existing status, accepted flag, and reason codes under a
  `technique_specific["saxs_existing_gate"]` mapping. Do not store raw q/I,
  detector arrays, or the full result object.

- [x] **Step 3: Run focused GREEN**

  ```powershell
  python -m pytest -q tests/test_saxs_ai_orchestrator_handoff.py tests/test_saxs_ai_confirmed_rerun_safety.py -o addopts=
  ```

  Expected: all focused orchestration and confirmed-rerun tests pass.

### Task 3: Verify all affected SAXS boundaries

**Files:**
- Read-only: existing SAXS matrix and verifier inputs

- [x] **Step 1: Run the SAXS AI and preprocessing regression set**

  ```powershell
  python -m pytest -q tests/test_saxs_ai_orchestrator_handoff.py tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_saxs_ai_rescue_bridge.py tests/test_orchestrator_preprocess_automation.py -o addopts=
  ```

- [x] **Step 2: Run complete SAXS and structured verification**

  ```powershell
  python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
  python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-existing-gate-enforcement.md --changed --types
  python scripts/test_storage.py report --json
  python scripts/test_storage.py clean --older-than-hours 24 --json
  git diff --check
  ```

  Each pytest command requires a complete summary and exit code `0`; storage
  commands remain dry-run only.

### Task 4: Record and checkpoint

**Files:**
- Create: `docs/acceptance/2026-08-01-saxs-ai-existing-gate-enforcement.md`
- Modify: the task/spec/plan files listed in the explicit allowlist

- [x] **Step 1: Record exact outcomes and limitation**

  Record the focused and complete SAXS results, verifier counts, dry-run
  inventory, and the unchanged human scientific gates.

- [x] **Step 2: Create the allowlist checkpoint**

  ```powershell
  python scripts/auto_commit.py --message "fix(saxs): enforce existing gates for ai candidates" --files polynexus/orchestrator_preprocess.py tests/test_saxs_ai_orchestrator_handoff.py docs/superpowers/specs/2026-08-01-saxs-ai-existing-gate-enforcement-design.md docs/superpowers/plans/2026-08-01-saxs-ai-existing-gate-enforcement.md docs/agent/tasks/2026-08-01-saxs-ai-existing-gate-enforcement.md docs/acceptance/2026-08-01-saxs-ai-existing-gate-enforcement.md
  ```

  Expected: one local checkpoint and no push.
