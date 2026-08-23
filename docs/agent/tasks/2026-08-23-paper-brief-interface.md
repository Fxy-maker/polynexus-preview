---
task_id: 2026-08-23-paper-brief-interface
kind: architecture
status: proposed
date: 2026-08-23
title: Add an ARS-to-PolyNexus paper-brief interface
---

# Add an ARS-to-PolyNexus paper-brief interface

## Goal

Introduce one versioned, AI/CLI-facing interface that lets ARS/Codex attach a
short paper brief to an immutable evidence-package snapshot and receive a
validated manuscript plan.  The plan selects only existing evidence, figures,
metrics, and limitations; it does not write paper prose or alter analysis.

## Non-goals

- No GUI manuscript editor or mandatory GUI research-question form.
- No provider rerun, data conversion, analysis-plan mutation, or raw-data copy.
- No automatic scientific conclusion, causal mechanism, or sample-identity
  inference.
- No RAG dependency or document-generation integration in this task.

## Shared objects and entry points

- Objects: immutable evidence package; new paper-brief/manuscript-plan export.
- AI/Codex/CLI: creates a brief and reads the validated plan.
- GUI: unchanged in this first interface; later may consume the same DTO.
- Cross-entry rule: the interface reads existing package artifacts through the
  evidence-package view/handoff contract and never introduces an AI-private
  representation of runs, figures, or metrics.

## Acceptance criteria

- [ ] A brief pins an exact package identity and hash before plan creation.
- [ ] A plan can select known techniques, evidence IDs, metric IDs, and logical
  figures only; unknown or non-eligible references fail closed.
- [ ] Results candidates, Discussion-only metrics, prohibited conclusions, and
  human-review requirements retain their package meanings.
- [ ] The interface exposes a compact plan for ARS/Codex without manuscript
  prose, reruns, or immutable-package mutation.
- [ ] Focused package/ARS and public CLI-orchestration coverage proves the
  producer and consumer boundary.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_manuscript_plan.py tests/test_project_ars_writing_handoff.py
python scripts/verify.py --task docs/agent/tasks/2026-08-23-paper-brief-interface.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(workflow): add paper brief interface" `
  --files polynexus/core/project_workflow/manuscript_plan.py polynexus/core/project_workflow/__init__.py polynexus/cli/parser.py polynexus/cli/run_project_workflow_service.py tests/test_manuscript_plan.py tests/test_project_workflow_cli.py docs/agent/tasks/2026-08-23-paper-brief-interface.md docs/superpowers/specs/2026-08-23-paper-brief-interface-design.md
```

## Completion evidence

- Exact commands and outcomes:
- Known limitations or follow-up: GUI plan display and ARS document generation
  are deliberately later tasks.
- Pre-existing changes left untouched: existing evidence-review, gallery, and
  temporary test artifacts in the working tree.
