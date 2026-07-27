# SAXS Parameter Quality-Evidence Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic, read-only links from SAXS bundle parameter artifacts to the authoritative quality evidence file.

**Architecture:** Keep `quality_evidence.json` as the sole AI/quality audit payload. Add its bundle-relative path to the parameter JSON metadata and add a CSV-relative pointer to each serialized parameter row at the export boundary.

**Tech Stack:** Python, CSV/JSON export helpers, pytest, `scripts/verify.py`, and `scripts/auto_commit.py`.

---

### Task 1: Establish the export reference contract

**Files:**
- Create: `docs/superpowers/specs/2026-07-28-saxs-parameter-quality-evidence-reference-design.md`
- Create: `docs/superpowers/plans/2026-07-28-saxs-parameter-quality-evidence-reference.md`
- Create: `docs/agent/tasks/2026-07-28-saxs-parameter-quality-evidence-reference.md`
- Test: `tests/test_saxs_export_bundle.py`

- [x] **Step 1: Write the failing regression.**

  Export a static bundle with an existing AI plan and assert that
  `parameters.json` exposes `quality_evidence_file`, every CSV row exposes
  `quality_evidence_ref`, and the CSV does not contain the AI candidate ID or
  full audit payload.

- [x] **Step 2: Run the focused test to verify RED.**

  ```powershell
  $env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_quality_ref_red'
  python -m pytest -q tests/test_saxs_export_bundle.py -k quality_evidence_reference
  ```

  Expected: the new test fails because the bundle currently emits neither
  parameter reference.

### Task 2: Add the minimal detached references

**Files:**
- Modify: `polynexus/core/saxs_export_bundle.py`
- Test: `tests/test_saxs_export_bundle.py`

- [x] **Step 1: Add bundle metadata.**

  Set `parameter_payload["quality_evidence_file"]` to the already-written
  `files["quality_evidence"]` path before writing `parameters.json`.

- [x] **Step 2: Add the CSV-relative reference.**

  Add `quality_evidence_ref` to each mapping row immediately before CSV field
  discovery, using `../` plus the bundle-relative quality-evidence path. Copy
  each row before adding the reference so caller-owned rows are not mutated.

- [x] **Step 3: Run the focused test to verify GREEN.**

  ```powershell
  $env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_quality_ref_green'
  python -m pytest -q tests/test_saxs_export_bundle.py -k quality_evidence_reference
  ```

  Expected: the new regression passes and the existing export tests remain
  green.

### Task 3: Verify and create one allowlist checkpoint

**Files:**
- `polynexus/core/saxs_export_bundle.py`
- `tests/test_saxs_export_bundle.py`
- `docs/agent/tasks/2026-07-28-saxs-parameter-quality-evidence-reference.md`
- `docs/superpowers/specs/2026-07-28-saxs-parameter-quality-evidence-reference-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-parameter-quality-evidence-reference.md`

- [x] **Step 1: Run the focused consumer matrix.**

  Run `tests/test_saxs_export_bundle.py` and the existing analysis-run
  persistence tests with a dedicated basetemp; record exact results.

- [x] **Step 2: Run the exact SAXS matrix and task verifier.**

  Run the PowerShell-expanded `tests/test_saxs_*.py` matrix,
  `python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-parameter-quality-evidence-reference.md --changed --types`,
  and `git diff --check`. Report full/boundary separately unless it completes.

- [x] **Step 3: Create an explicit allowlist checkpoint.**

  Use `python scripts/auto_commit.py` with only the five files listed above.
  Leave GUI/release/memory/scratch files untouched.
