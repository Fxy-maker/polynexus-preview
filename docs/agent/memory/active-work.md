# Active Work

> Last updated: 2026-07-18

## Current checkpoint

- OriginLab integration is implemented and locally merged into `main`. The
  ChartEditor top export menu exposes Origin, and run-relative generated-figure
  CSV sources resolve through the gallery `run_root`; native export now shows
  and activates the Origin graph when available; capability probing also reads
  the Windows user environment registry when the running GUI has a stale
  `os.environ`; see decisions `0010` and `0011`.
- The focused Origin/editor verification currently passes: 38 Origin-related
  tests and 238 ChartEditor regression tests. The prescribed verifier command
  cannot run because `scripts/verify.py` is absent; see lesson `0001`.
- A live smoke export through the configured OriginPro installation opened
  `Origin64` with a generated `.opju` graph visible; a real user-figure click
  remains the final manual check.
- The agent memory foundation is now present: `README.md`,
  `current-state.md`, this register, decision memory, and lesson memory.
- The older entries below were last reconciled on 2026-07-11. Treat their
  branch/PR status as historical context until each item is rechecked against
  the current mainline.

## Completed

- Added the root agent contract in `AGENTS.md`.
- Added the agent workflow, definition of done, task template, and testing matrix
  under `docs/agent/`.
- Added `scripts/verify.py` as the unified verification entry point.
- Added this external memory foundation under `docs/agent/memory/`.

## In progress

- AI preprocessing mainline is active on `codex/ai-preprocess-mainline-v2` from
  `main@4437bc90`. Foundation, semantic intents, DSC/IR/WAXS, and SAXS/NMR
  adapters are present; the current safety checkpoint adds scoped experience
  retrieval, decision audit records, original-config snapshots, hash rechecks,
  runtime negative-fraction evidence, and SAXS/NMR hard guards. Focused
  preprocessing/calibration tests pass (`79`); the broader orchestration subset
  passes (`244 passed, 1 skipped`). GUI confirmation, Golden/AI-off/fault gates,
  CI, and human scientific review remain pending. Focused Golden/synthetic,
  fault-injection, AI-off, and quality-gate checks now pass; local
  `quality_gate.py --all-tests` exceeded 304 seconds without reporting a
  failing test. The task card is
  `docs/agent/tasks/2026-07-13-ai-preprocessing-mainline.md`.
- Unified Tables results/export slice is merged in PR #12 at `3f050065`; the slice covers structured table templates/adapters, generic fallback, CSV/TSV/XLSX export, and clipboard extraction.
- Unified Tables GUI integration is active on `codex/unified-tables-gui-integration-v2` from main `3f050065`. The slice is limited to the structured result panel, MainWindow service/view-model consumption, workspace/history restore context, and persistence/retranslation regressions; editor/export reconciliation remains separate.
- DSC publication packs were reviewed and merged in PR #14 as `a5804d2a`, with the dedicated 600-DPI publication profile and standard/isothermal/non-isothermal evidence-gated providers. The dedicated main worktree is synchronized with `origin/main`.
- WAXS publication packs are in progress on `codex/waxs-publication-packs-v2` from `main@a5804d2a`. The slice is limited to static, temperature/time, and strain providers, editable 2D image-grid support, manifest-backed publication with a WAXS 600-DPI TIFF profile, and explicit legacy fallback isolation. Focused WAXS/shared regression and quality-gate evidence currently pass; scientific review, CI, push, and merge remain pending.
- Unified Tables contracts slice is implemented on `codex/unified-tables-contracts-v2`; PR #11 passed local and GitHub gates and received user data-contract review on 2026-07-13. Results service/export, GUI integration, DSC/WAXS packs, editor/export reconciliation, and AI preprocessing remain separate task cards.
- Mainline integration reconciliation completed the reviewed SAXS evidence-filtering slice in PR #10. Shared figure lifecycle compatibility, SAXS mode/evidence contract, cumulative review evidence, and temperature/strain filtering are recorded in the acceptance and memory documents; the squash merge is `70b299af`.
- GUI startup performance task completed on 2026-07-11. The application entry now uses deferred optional UI construction; focused startup and MainWindow persistence evidence is recorded in `docs/acceptance/2026-07-11-gui-startup-performance.md`.
- SAXS temperature/strain production cutover was rebased onto `origin/main` after PR conflict investigation. The current mainline already contains the strict shared-publisher route; the rebased PR adds entry-level regression coverage and keeps the design/task evidence without replacing newer provider code. Focused rebased tests pass; full repository pytest exceeded the five-minute runtime limit without a reported failing test. Human architecture/science review is pending before integration.
- Editor style-context hydration implementation completed on isolated branch `codex/editor-style-context`. Generated/document source switching now resets editor style controls, hydrates from the current document, and keeps static edit overlays on the static path. Focused style-context tests pass (5), focused generated/save/preset tests pass (12), and the editor regression matrix passes (267); task evidence is recorded in `docs/agent/tasks/2026-07-12-editor-style-context.md`, and human editor review is pending.
- Legacy gallery fallback strategy evaluation completed on isolated branch `codex/legacy-gallery-fallback-strategy`. The normal gallery remains manifest-only; historical recursive discovery stays behind the explicit recovery view and never silently changes the active run. Strategy evidence is recorded in `docs/superpowers/specs/2026-07-12-legacy-gallery-fallback-strategy.md` and decision memory `docs/agent/memory/decisions/0003-manifest-only-gallery-discovery.md`; no production code changed.
- GUI streamlining implementation completed on isolated branch `codex/gui-streamlining-interaction-plan`. The implementation adds explicit workspace modes, binds current results to persisted run IDs, makes the figure preview the canonical View route, fixes primary shortcuts and batch-manifest naming, removes verified duplicate top-bar routes, and preserves manifest-only gallery plus explicit legacy recovery. GUI focused regression matrix passes (452); evidence is recorded in `docs/superpowers/specs/2026-07-12-gui-streamlining-interaction-plan.md`, the implementation plan, and decision memory `docs/agent/memory/decisions/0004-gui-streamlining-last-wave.md`. Existing Ruff baseline findings remain in legacy GUI modules.

## Suggested next candidates

1. Add incremental Ruff checks for changed files, then ratchet toward full-repo
   cleanliness.
2. Add a small index or search adapter for memory entries only after the Markdown
   source of truth is being maintained consistently.
3. If the startup target must improve beyond the current approximately 2.7-second fresh-process probe, separately evaluate scientific-stack packaging and lazy technique-registry loading.

## Update protocol

Every active task should record its status, blocker, next action, and evidence
link here when that information will matter to a later agent.
