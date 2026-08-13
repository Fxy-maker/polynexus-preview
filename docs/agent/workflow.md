# PolyNexus Development Workflow

PolyNexus is a dual-entry polymer research workbench. Codex/AI and the user
interface operate on the same project, run, chart, evidence, and export
objects. A feature is not complete merely because one entry point works.

## Atomic task loop

1. State the goal, non-goals, affected objects, affected entry points, and
   acceptance criteria.
2. Read the relevant object contract and current project memory.
3. Add a focused regression test before changing behavior.
4. Implement the smallest change within one ownership boundary.
5. Run the focused verification matrix and inspect the result.
6. Confirm cross-entry consistency when a shared object or contract changed.
7. Record durable decisions or limitations, then create one allowlisted local
   checkpoint with `scripts/auto_commit.py`.

The loop never auto-pushes, auto-merges, deploys, deletes data, or promotes a
diagnostic value into a scientific conclusion.

## Shared-object rule

The following are shared first-class objects, not AI-only or GUI-only copies:

- Project: source artifacts, grouping context, and project metadata.
- Run: canonical input, configuration, result status, and provenance.
- Chart: source run, data bindings, edit history, and export assets.
- Evidence package: immutable results, limitations, review actions, and metric
  provenance.
- Export: package-relative asset references and source/provenance links.

AI may discover, organize, and request deterministic work. It must not bypass
canonical validation, fabricate scientific values, or mutate immutable evidence
snapshots. GUI code displays and edits public DTOs or view models; it must not
branch on technique-private algorithm state.

## Verification selection

Run only the smallest matrix that proves the changed behavior. Use
`POLYNEXUS_TEST_RETENTION=ephemeral` unless output must be reviewed or retained
as evidence. Read verbose test output only when a command fails.

| Change type | Default proof |
| --- | --- |
| Deterministic analysis or canonical conversion | Focused core/provider and canonical replay tests |
| AI/project orchestration | Focused discovery, workflow, package, and provenance tests |
| Shared run, chart, evidence, or export contract | Producer test plus the affected AI/CLI and GUI/DTO consumer tests |
| GUI-only presentation | Focused GUI/view-model test; no provider matrix unless the DTO changes |
| Release or cross-module integration | `verify.py --changed --types --full --boundary` plus explicit human review |

For shared objects, test the producing route and every changed consuming route.
The GUI consumer may remain a narrow DTO or smoke test; it does not require a
full GUI suite for each task.
