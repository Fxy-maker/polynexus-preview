# Joint Real-Data Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an acceptance slice proving that existing real DSC, SAXS, and WAXS engine outputs can be persisted into the existing SampleDB contract and consumed by Joint publication with source-run provenance.

**Architecture:** Keep `JointCoordinator` and the scientific formulas unchanged. The test will use the public engine and SampleDB contracts, normalize only the result fields already consumed by `JointBatchRow`, then exercise `collect_joint_dataset()`, `build_joint_hub_report()`, and `publish_hub_report()`. This proves real-data transport and Figure Manifest publication without claiming human scientific validity or adding a raw-file Joint reader.

**Tech Stack:** Python, pytest, existing real fixtures under `测试数据/`, `SampleDB`, registered analysis engines, Joint dataset/coordinator, FigureProductionPublisher.

---

### Task 1: Define the real-data Joint acceptance boundary

**Files:**
- Create: `docs/agent/tasks/2026-07-29-joint-real-data-lifecycle.md`
- Create: `docs/superpowers/plans/2026-07-29-joint-real-data-lifecycle.md`

- [x] State that the test covers engine → SampleDB → Joint report → Figure Manifest/provenance only.
- [x] State that raw-file Joint ingestion, scientific publication approval, and restarted-GUI visual review are non-goals.

### Task 2: Add the real-fixture lifecycle acceptance test

**Files:**
- Create: `tests/test_joint_real_data_lifecycle.py`

- [ ] Run the new test once before implementation and record any contract failure.
- [ ] Run the real DSC standard, SAXS static, and WAXS static fixtures into isolated output directories.
- [ ] Persist each result's existing parameters/evidence and a minimal Joint-consumer summary in one SampleDB sample/batch.
- [ ] Assert that `collect_joint_dataset()` returns one row with three real source run IDs and that `build_joint_hub_report()` contains cross-technique validations.
- [ ] Publish the real row through `JointCoordinator.publish_hub_report()` and assert the three Joint figure IDs, one run ID, manifest existence, and provenance source IDs.

### Task 3: Verify and checkpoint

- [ ] Run `python -m pytest -q tests/test_joint_real_data_lifecycle.py` with an external basetemp.
- [ ] Run the focused existing Joint lifecycle/provenance matrix.
- [ ] Run `python scripts/verify.py --task docs/agent/tasks/2026-07-29-joint-real-data-lifecycle.md --changed --types` and `git diff --check`.
- [ ] Create one allowlisted `scripts/auto_commit.py` checkpoint.

### Scope audit

- No production code or scientific threshold changes are planned.
- No vendor-native IR mapping semantics are inferred.
- No Joint report conflict is silently corrected; any warning/error remains in the report evidence.
