# SAXS recovery ComputeRun migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route real-source SAXS condition recovery through the shared ComputeRun producer without removing compatibility fallbacks.

**Architecture:** Reuse the initial run's canonical template and controlled engine in `ComputeRunService.run_direct`. Hold the returned candidate run until scoring accepts it; synthetic/missing sessions keep the existing direct provider boundary.

**Tech Stack:** Python, pytest, immutable ComputeRun/CanonicalExperiment DTOs, existing SAXS orchestrator.

---

### Task 1: Define the regression contract

**Files:**
- Create: `tests/test_saxs_orchestrator_compute_run.py`

- [x] **Step 1: Write tests for real-source service reuse and synthetic fallback.**

```python
def test_recovery_reuses_shared_service_for_real_source(monkeypatch, tmp_path):
    source = tmp_path / "curve.csv"
    source.write_text("q,I\\n0.1,1\\n0.2,2\\n", encoding="utf-8")
    engine = _RecoveryEngine()
    initial = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="saxs", path=source, output_dir="", engine=engine
    )
    orchestrator = _recovery_orchestrator(source)
    orchestrator._compute_run = initial
    calls = []
    real_service = ComputeRunService(lambda *args, **kwargs: engine)

    class SpyService:
        def run_direct(self, **kwargs):
            calls.append(kwargs)
            return real_service.run_direct(**kwargs)

    monkeypatch.setattr("polynexus.orchestrator_session.ComputeRunService", SpyService)
    outcome = orchestrator._execute_candidate_trial(
        engine, 1, SimpleNamespace(r_squared=0.0, eval_score=0.0),
        _recovery_advice(), {}, "",
    )
    assert outcome["status"] == "accepted"
    assert calls[0]["canonical_template"].content_hash == initial.canonical_template.content_hash
    assert outcome["compute_run"].status == "completed"
    assert orchestrator._compute_run is initial

def test_recovery_keeps_provider_fallback_for_synthetic_source(monkeypatch):
    engine = _RecoveryEngine()
    orchestrator = _recovery_orchestrator(Path("dummy.dat"))
    orchestrator._compute_run = None
    outcome = orchestrator._execute_candidate_trial(
        engine, 1, SimpleNamespace(r_squared=0.0, eval_score=0.0),
        _recovery_advice(), {}, "",
    )
    assert outcome["status"] == "accepted"
    assert engine.pipeline_calls == 1
```

- [x] **Step 2: Run the focused tests and observe the expected RED failure.**

Run: `python -m pytest -q tests/test_saxs_orchestrator_compute_run.py`

Expected: FAIL because the real-source recovery path still invokes
`engine.run_pipeline` directly.

### Task 2: Migrate the real-source recovery branch

**Files:**
- Modify: `polynexus/orchestrator_session.py:104-215`

- [x] **Step 1: Call `ComputeRunService.run_direct` with the existing engine and canonical template when `_compute_run` is present.**
- [x] **Step 2: Convert service failure into the existing rejected-candidate payload.**
- [x] **Step 3: Replace `_compute_run` only after candidate scoring accepts; leave it unchanged on rollback.**
- [x] **Step 4: Reapply the winning recovery context after baseline restore before final replay.**

### Task 3: Verify and record the checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-08-27-saxs-recovery-compute-run-migration.md`
- Create: `docs/acceptance/2026-08-27-saxs-recovery-compute-run-migration.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run focused SAXS/orchestrator tests.**
- [x] **Step 2: Run `python scripts/verify.py --task docs/agent/tasks/2026-08-27-saxs-recovery-compute-run-migration.md --changed --types`.**
- [x] **Step 3: Run `git diff --check`.**
- [x] **Step 4: Create the explicit allowlisted checkpoint with `scripts/auto_commit.py`.**
