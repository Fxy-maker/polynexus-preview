# Joint Real-Data Current-HEAD Recheck Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. This is a verification-only task with no production-code change.

**Goal:** Re-run the existing Joint real-data transport and publication contract on the current HEAD.

**Architecture:** Reuse `tests/test_joint_real_data_lifecycle.py`; require complete pytest output and exit code `0`, then record that the result proves transport/provenance only and does not resolve scientific conflicts.

**Tech Stack:** Python, pytest, existing DSC/SAXS/WAXS fixtures, JointCoordinator, SampleDB, Figure Manifest/Gallery, and repository verification scripts.

---

### Task 1: Run the existing Joint real-data contract

**Files:**
- Read: `tests/test_joint_real_data_lifecycle.py`
- Read: `测试数据/`

- [x] Run `python -m pytest -p no:cacheprovider -q tests/test_joint_real_data_lifecycle.py -vv --basetemp=C:\PolyNexus-test-runs\joint-real-data-current-head-20260731`; it returned `1 passed in 15.55s`, exit `0`.
- [x] Require a complete summary and exit code `0`; a skip, timeout, or missing summary is not a pass.

### Task 2: Record and verify evidence

**Files:**
- Modify: the task card and acceptance record

- [x] Record source runs, SampleDB/Joint report transport, Figure Manifest, Gallery, and the exact pytest outcome.
- [ ] Run task verifier, boundary audit, and `git diff --check`.
- [ ] Create one explicit three-document allowlist checkpoint.
