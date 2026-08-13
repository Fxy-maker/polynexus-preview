task_id: 2026-08-13-workbench-surface-convergence
kind: architecture
status: implementation_complete_review_required
date: 2026-08-13
title: Converge flexible quick and AI analysis workbench

# Converge Flexible Quick and AI Analysis Workbench

## Goal

Define and stage one shared PolyNexus workbench in which Quick Analysis is the
human default path and Project/Evidence is the ARS/Codex multi-technique path,
with bounded AI planning and replayable provenance.

## Non-goals

- Do not change provider algorithms or real datasets in the design task.
- Do not delete RAG, Sample Hub, Joint, convergence, plan evaluation, NMR, or
  Origin before replacement evidence and a separate approved task.
- Do not make the GUI collect a mandatory research question.
- Do not allow AI to write arbitrary numeric parameters or scientific claims.

## Shared objects and entry points

- Objects: `Project`, `Run`, `Chart`, `EvidencePackage`, `Export`, and the new
  versioned `AnalysisPlan` contract.
- Producers: quick GUI, project workflow service/CLI, and ARS/Codex request
  adapter all create the same plan/run objects.
- Consumers: deterministic runners validate plans; history and evidence
  packaging persist them; GUI DTOs, CLI JSON, and ARS writing handoff read them.
- Cross-entry rule: every implementation task must test its producer and each
  affected GUI/CLI/ARS consumer; no entry point may create a private model.

## Affected boundaries

- Design: `docs/superpowers/specs/2026-08-13-flexible-ai-analysis-workbench-design.md`.
- Plan: `docs/superpowers/plans/2026-08-13-flexible-ai-analysis-workbench.md`.
- GUI navigation and quick/project routing under `polynexus/gui/main_window*.py`.
- Plan/run/provenance services under `polynexus/core`, `polynexus/cli`, and
  existing project workflow/package modules.
- AI compatibility and diagnostic surfaces under `polynexus/orchestrator*.py`,
  `polynexus/gui/main_window_ai_tuning_mixin.py`, and related DTO/services.
- Durable state: `docs/agent/memory/active-work.md`.

## Acceptance criteria

- [ ] Quick Analysis is the first human-facing entry and retains automatic
  detection, folder batch selection, NMR, chart editing, and Origin export.
- [ ] Project/Evidence supports explicit file/group selection and ARS/Codex
  intent without requiring a GUI research-question form.
- [ ] A versioned `AnalysisPlan` records sources, canonical conversion,
  algorithm/config versions, AI decision hashes, constraints, approval, and
  replay lineage.
- [ ] Frozen plans replay without an AI call; a new AI decision creates a new
  `replan` run and never overwrites an immutable result.
- [ ] Adaptive analysis uses finite deterministic candidates and protected
  scientific metrics, not one `r2`/appearance score.
- [ ] Joint, convergence, and plan evaluation are contextual AI tools with
  GUI summaries; Sample Hub is optional metadata/history; RAG remains deferred.
- [ ] A real PA6 DSC/FTIR/SAXS/WAXS replay produces evidence, citable metrics,
  figures, limitations, and ARS writing input.
- [ ] All architecture/schema/scientific changes remain review-required before
  merge, and no generated data or pre-existing untracked paths are modified.

## Implementation plan

1. Converge Quick Analysis navigation and entry labels without changing provider algorithms.
2. Add the versioned `AnalysisPlan` DTO, stable hashes, validation, and manifest persistence.
3. Implement frozen deterministic replay and immutable `replan_of` lineage.
4. Replace unconstrained AI tuning with symptom diagnosis and finite robustness candidate evaluation.
5. Expose identical plan/evaluation DTOs to GUI, CLI, and ARS/Codex consumers.
6. Simplify Sample Hub and support attaching a quick run to an existing project.
7. Move Joint, convergence details, and plan evaluation behind contextual run/project summaries.
8. Assess RAG as an optional dependency after the adaptive-plan replacement is tested.
9. Run the read-only PA6 DSC/FTIR/SAXS/WAXS replay and verify the ARS writing handoff.

## Verification

Design checkpoint:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-13-workbench-surface-convergence.md --changed --types
git diff --check
rg -n "TBD|TODO|Project Workbench: default|Quick Analysis: expert" docs/superpowers/specs/2026-08-13-flexible-ai-analysis-workbench-design.md docs/superpowers/plans/2026-08-13-flexible-ai-analysis-workbench.md
```

Implementation stages use focused tests named in the plan and finish with:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-13-workbench-surface-convergence.md --changed --types --full --boundary
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "docs(architecture): define flexible AI analysis workbench" `
  --files docs/superpowers/specs/2026-08-13-flexible-ai-analysis-workbench-design.md docs/superpowers/specs/2026-08-13-workbench-surface-convergence-design.md docs/agent/tasks/2026-08-13-workbench-surface-convergence.md docs/superpowers/plans/2026-08-13-flexible-ai-analysis-workbench.md docs/agent/memory/active-work.md
```

## Completion evidence

- Completed stages: Quick Analysis is the default entry; versioned frozen
  `AnalysisPlan`/`replan_of` contracts and bounded candidate evaluation are
  shared by GUI, CLI, and ARS; Sample Hub is optional metadata/history; Joint,
  convergence, and plan evaluation are context-bound; vector RAG is optional;
  and a completed current run can now be attached to a project by reference
  from the GUI without copying source data or rerunning analysis. The shared
  attachment API retains its historical compatibility name, while GUI text
  deliberately says “current run” because origin is not inferred.
- The GUI plan-evaluation action reads only the shared
  `AnalysisPlanEvaluation` projection, and only when its run binding matches
  the current completed run. Malformed or stale cached evaluations fail closed.
  Nested payload validation now also rejects non-mapping `replay` values,
  non-mapping candidate items, and non-string review-limit items before the
  contextual action can be enabled. A malformed report drops only this optional
  evaluation projection; it cannot interrupt the ordinary AI-tuning completion
  path.
  The attachment action calls the public project workflow service and writes
  only its project-local reference manifest.
- Read-only PA6 package loading on 2026-08-13 confirmed `dsc`, `ir`, `saxs`,
  and `waxs`; 96 metrics (42 Results candidates and 54 Discussion-only); six
  human-review actions; and no `raw` directory in
  `D:\PolyNexus-pa6-four-technique-smoke-20260814\.polynexus\evidence\final-pa6-e2e-audit-v001`.
- Focused outcomes: GUI contextual/plan/attachment matrix `27 passed`; quick
  navigation/run matrix `21 passed`; project evidence/package matrix
  `59 passed`. `python scripts/verify.py --task
  docs/agent/tasks/2026-08-13-workbench-surface-convergence.md --changed
  --types` passed on 2026-08-14 with quality/preprocess gates `303`/`157`;
  `boundary_audit.py --json` passed.
- Full integration evidence on 2026-08-14: `3942 passed, 33 failed, 21 skipped`
  in 2050.77 seconds. The run surfaced and then verified the batch token
  initialization regression introduced by stale-worker isolation. The remaining
  failures are chart gallery, historical GUI persistence/sample browser, and
  SAXS paths outside this task's changed boundaries; this task does not claim a
  release-green full suite.
- Known limitations: the PA6 package remains `review_required`; scientific
  interpretation and publication require human review. The historical full
  repository boundary suite has unrelated legacy failures and must not be
  described as release-green unless a fresh full/boundary run proves otherwise.
- Pre-existing changes left untouched: `.superpowers/` and `tests/_tmp_phase3/`.
