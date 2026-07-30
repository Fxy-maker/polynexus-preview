# Current-head Full/Boundary Release Re-audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline execution). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify the current checkout's complete automated release boundary without changing production behavior.

**Architecture:** Use the existing `scripts/verify.py` orchestration and its quality/boundary subcommands. Store only durable evidence and limitations in the task artifacts; do not create a repair shim or reinterpret incomplete process output.

**Tech Stack:** PowerShell, Python, pytest, PolyNexus verification scripts, Markdown task artifacts.

---

### Task 1: Establish the current process boundary

**Files:**
- Read: current Git status and process table

- [x] **Step 1: Confirm no active verifier process is being reused**

Run:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|pytest' } | Select-Object ProcessId,ParentProcessId,Name,CommandLine
git status --short --branch
```

Only the current checkout is in scope; no previous process output is reused.

### Task 2: Run the authoritative full/boundary command

**Files:**
- Read: `scripts/verify.py`, `scripts/quality_gate.py`, `scripts/boundary_audit.py`

- [x] **Step 1: Execute the full command**

Run:

```powershell
python scripts/verify.py --changed --types --full --boundary
```

Require a complete pytest summary, quality/preprocessing summaries, boundary
result, and wrapper exit code before classifying the run.

### Task 3: Record evidence and checkpoint

**Files:**
- Modify: this task card and plan
- Create: `docs/acceptance/2026-07-30-current-head-full-boundary-release-reaudit.md`

- [x] **Step 1: Record the actual result**

Write only the observed counts, warnings, exit code, process classification,
and known human/release limitations. If the run is incomplete, state that no
full/boundary pass is claimed.

- [x] **Step 2: Verify the documents**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-current-head-full-boundary-release-reaudit.md --changed --types
git diff --check
```

- [x] **Step 3: Create the explicit documentation checkpoint**

Run `scripts/auto_commit.py` with only the four files in the task card's
allowlist. Do not stage parallel source files, scratch directories, or memory
files.
