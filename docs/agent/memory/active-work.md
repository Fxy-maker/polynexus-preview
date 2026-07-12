# Active Work

> Last updated: 2026-07-11

## Completed

- Added the root agent contract in `AGENTS.md`.
- Added the agent workflow, definition of done, task template, and testing matrix
  under `docs/agent/`.
- Added `scripts/verify.py` as the unified verification entry point.
- Added this external memory foundation under `docs/agent/memory/`.

## In progress

- GUI startup performance task completed on 2026-07-11. The application entry now uses deferred optional UI construction; focused startup and MainWindow persistence evidence is recorded in `docs/acceptance/2026-07-11-gui-startup-performance.md`.
- SAXS temperature/strain production cutover was rebased onto `origin/main` after PR conflict investigation. The current mainline already contains the strict shared-publisher route; the rebased PR adds entry-level regression coverage and keeps the design/task evidence without replacing newer provider code. Focused rebased tests pass; full repository pytest exceeded the five-minute runtime limit without a reported failing test. Human architecture/science review is pending before integration.
- Editor style-context hydration implementation completed on isolated branch `codex/editor-style-context`. Generated/document source switching now resets editor style controls, hydrates from the current document, and keeps static edit overlays on the static path. Focused style-context tests pass (5), focused generated/save/preset tests pass (12), and the editor regression matrix passes (267); task evidence is recorded in `docs/agent/tasks/2026-07-12-editor-style-context.md`, and human editor review is pending.
- Legacy gallery fallback strategy evaluation completed on isolated branch `codex/legacy-gallery-fallback-strategy`. The normal gallery remains manifest-only; historical recursive discovery stays behind the explicit recovery view and never silently changes the active run. Strategy evidence is recorded in `docs/superpowers/specs/2026-07-12-legacy-gallery-fallback-strategy.md` and decision memory `docs/agent/memory/decisions/0003-manifest-only-gallery-discovery.md`; no production code changed.

## Suggested next candidates

1. Add incremental Ruff checks for changed files, then ratchet toward full-repo
   cleanliness.
2. Add a small index or search adapter for memory entries only after the Markdown
   source of truth is being maintained consistently.
3. If the startup target must improve beyond the current approximately 2.7-second fresh-process probe, separately evaluate scientific-stack packaging and lazy technique-registry loading.

## Update protocol

Every active task should record its status, blocker, next action, and evidence
link here when that information will matter to a later agent.
