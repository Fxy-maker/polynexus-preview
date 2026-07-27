---
kind: state
status: active
date: 2026-07-22
title: Current PolyNexus repository state
---

## Mainline snapshot

- SAXS temperature condition-axis evidence is implemented in the working tree:
  existing temperature-series metric summaries now carry a strict-JSON,
  position-preserving `condition_axis` with condition name, finite values,
  invalid/duplicate/non-monotonic positions, and ordered/diagnostic/empty
  status. The existing sorted `temperature_C` values are passed through while
  original `source_index` mapping remains separate. No metric levels/counts,
  physical gates, interpolation, repair, AI, or publication behavior changed;
  strain-axis semantics remain out of scope. Focused consumer evidence is
  `41 passed`; the isolated SAXS matrix is `356 passed, 4 warnings`; and the
  isolated task-scoped verifier passed quality `282` and preprocessing `106`.
  Fresh isolated full/boundary verification exited `0` with selected checks
  and boundary audit passing, but its middle full-pytest count was truncated
  by tool output and is not reconstructed. Task card:
  `docs/agent/tasks/2026-07-27-saxs-temperature-condition-axis-evidence.md`.

- SAXS series metric position evidence is implemented and checkpointed at
  `bd7c3fd`: existing
  summaries now expose deterministic frame positions for evidence/missing/
  diagnostic/unusable/invalid-level states, and temperature summaries retain
  sorted-to-original `source_index` mapping. This is read-only provenance; no
  numerical algorithm, threshold, interpolation, repair, AI, or publication
  behavior changed. Focused evidence is `38 passed`; isolated SAXS is `353
  passed, 6 warnings`; direct quality/preprocessing equivalents are `282`/`106`.
  The task-scoped changed verifier is limited by pre-existing Ruff findings in
  unrelated shared-worktree files and the default quality child launch has the
  known Windows permission limitation. Task card:
  `docs/agent/tasks/2026-07-27-saxs-series-metric-position-evidence.md`.

- SAXS in-situ strain Herman orientation transport is implemented in the
  working tree: directory-loaded sector maps remain aligned to frames, the
  existing strain engine receives them, and finite per-frame `f_Herman` values
  now reach the existing structured result table. 1D or missing-sector frames
  remain unavailable; no orientation algorithm or scientific threshold changed.
  Focused core/table evidence is `66 passed`; the complete SAXS matrix is
  `341 passed, 4 warnings`; task-scoped quality/preprocessing gates are
  `282`/`106` using an external pytest basetemp. Task card:
  `docs/agent/tasks/2026-07-27-saxs-strain-herman-table.md`.

- The full-software release audit is in progress in
  `docs/agent/tasks/2026-07-27-full-software-release-audit.md`. Fresh WAXS
  publication/provider/workbench evidence is `30 passed`; the cross-technique
  AI-off/failure/fallback contract matrix is `25 passed`. A combined
  real/lifecycle attempt exceeded its 180-second tool window without a summary
  and is not treated as pass or failure; replacement per-technique shards
  passed all 15 single-technique real walkthrough cases and DSC `3`, WAXS `3`,
  IR `3`, NMR `4`, Joint `1` lifecycle closures. The canonical GUI default
  shell was visually captured, but restarted-GUI route coverage,
  while 58 focused shell/workbench/gallery/editor route tests pass,
  and a real-result route capture passes structurally,
  IR mapping/ROI structural tests add `11 passed`, and NMR/Joint provenance
  tests add `4 passed`; IR vendor mapping/ROI semantics, assignment-limited NMR/Joint review, and
  final human release approval remain open. Fresh full verification passed
  `2773` tests with `10` existing warnings in `1451.67s` and the boundary audit
  passed. The GUI responsive-shell checkpoint is `83083bc`; a fresh canonical
  launcher diagnose resolves `D:\PolyNexus` at that commit.
  Acceptance note:
  `docs/acceptance/2026-07-27-full-software-release-audit.md`.

- SAXS AI confirmed-rerun safety is implemented and checkpointed locally; this
  documentation-only amend records the final state. The core adapter validates the
  existing candidate identity/hard guards and projects only existing physical
  and quality evidence for static, temperature, and strain. The shared
  transaction service applies once, gates before persistence, rolls back on
  unavailable/weak/failed evidence or hash drift, and records strict audit
  provenance. GUI lifecycle resolution uses the existing temperature/strain
  DTOs behind the generic worker result; `quality_evidence.json` remains the
  authority. Focused evidence is `29 passed`; complete SAXS is `334 passed, 4
  warnings`; task-scoped quality/preprocessing gates are `282`/`106`. Fresh
  full verification reached `2763 passed, 1 failed, 10 warnings` after about
  25:42, stopped by the unrelated WAXS publication-cutover test before
  boundary audit; no full/boundary pass is claimed. Human scientific review
  remains open. Task
  card: `docs/agent/tasks/2026-07-27-saxs-ai-confirmed-rerun-safety.md`.

- SAXS Figure/Manifest evidence binding is implemented and locally checkpointed
  without push. Figure providers attach detached,
  strict JSON-safe references to existing frame/series quality evidence while
  preserving publication roles and the authoritative `quality_evidence.json`.
  Focused evidence is `33 passed`; the complete SAXS matrix is `317 passed, 4
  warnings`; task-scoped quality/preprocessing gates are `282`/`106`. Fresh
  full/boundary verification with an isolated basetemp timed out with exit
  `124` after about 1204 seconds without a test-failure summary; its verifier
  and pytest children were then terminated and no such process remained. It
  is not claimed as passed.
  Scientific role-gating review and real-data validation remain separate.
  Task card:
  `docs/agent/tasks/2026-07-27-saxs-figure-evidence-binding.md`.

- SAXS series metric evidence rollup is now documentation-closed against the
  current code: immutable summaries remain Trend-capped, missing/diagnostic
  frames remain explicit, and frame/series evidence stays read-only through
  Workbench and Export. Fresh focused verification is `14 passed`; the full
  SAXS matrix is `317 passed, 4 warnings`; task-scoped quality/preprocessing
  gates are `282`/`106`; and `git diff --check` passes. Full/boundary release
  verification and human scientific review remain open. Task card:
  `docs/agent/tasks/2026-07-27-saxs-series-metric-evidence-rollup.md`.

- SAXS temperature Guinier sequence evidence transport is checkpointed in
  `b7bad1c`: existing sequence evidence now retains optional original frame
  indices, survives temperature sorting, reaches parameters/History/Export,
  and is rendered in Workbench as advisory diagnostics. No new physical
  threshold, interpolation, frame repair, AI action, or publication behavior
  was added. Focused evidence is `56 passed`; the complete SAXS matrix is `311
  passed, 4 warnings`; task-scoped quality/preprocessing gates are `282`/`106`.
  The fresh full/boundary run timed out before a final count and is not claimed
  as passed. Task card:
  `docs/agent/tasks/2026-07-27-saxs-temperature-guinier-sequence-transport.md`.

- SAXS aligned-batch evidence resilience is implemented in the working tree:
  when a generic multi-frame payload has a non-static temperature/strain label
  but no dedicated series result, existing frame evidence is preserved and the
  scope is explicitly `aligned_batch`. Workbench wording calls this aligned
  batch quality, while missing-series state remains Diagnostic; no thresholds,
  frame ordering, scientific interpretation, or AI apply behavior changed.
  Task card: `docs/agent/tasks/2026-07-27-saxs-batch-evidence-mode-resilience.md`.

- SAXS static 1D evidence transport is implemented locally: static single
  parameters now carry existing frame quality DTOs, static multi-file rows
  preserve aligned frame evidence, and the batch payload exposes a conservative
  `metric_evidence` summary with `metric_evidence_scope=static_batch`. The
  Workbench labels this as batch quality rather than a condition trend, History
  round-trips the payload, and static `quality_evidence.json` includes aligned
  frame snapshots plus the summary. No SAXS physical calculation, threshold,
  figure role, or AI execution policy changed. Focused evidence/Workbench/
  History/Export verification is `77 passed`; the SAXS matrix is `290 passed,
  4 existing font warnings`; task verifier quality/preprocessing gates are
  `282`/`106`. Scientific review of batch interpretation remains required.
  See `docs/agent/tasks/2026-07-27-saxs-static-1d-evidence.md`.

- SAXS temperature Guinier closure is implemented locally: existing frame
  `guinier_evidence["metric"]` now contributes to the common series
  `metric_evidence["guinier"]` summary, while detailed sequence evidence stays
  separate. Workbench displays the common metric as `Rg`; no physical gates,
  frame values, figure roles, or Export semantics changed. Focused and full
  SAXS verification results are being finalized under
  `283 passed, 4 warnings` in the SAXS matrix; the task verifier passes with
  quality `282` and preprocessing `106` under an isolated basetemp. See
  `docs/agent/tasks/2026-07-27-saxs-temperature-guinier-metric-evidence.md`.

- SAXS Workbench series evidence visibility is checkpointed locally: temperature
  and strain parameter payloads now carry existing series `metric_evidence`,
  and the SAXS presentation surfaces coverage, Trend/Diagnostic/Unusable level,
  downgrade counts, and reason codes while Diagnostics retains the full JSON.
  History persistence, figure candidates, and Export provenance remain
  unchanged. Focused Workbench/History/Figure/Export evidence is `24 passed`;
  the full SAXS matrix is `282 passed, 4 existing warnings`; the task-scoped
  verifier passes quality `282` and preprocessing `106`. See
  `docs/agent/tasks/2026-07-27-saxs-workbench-series-evidence-visibility.md`.

- GUI responsive shell acceptance is checkpointed locally: compact policy now
  uses actual content width, header labels are compressible, optional shell
  actions collapse without removing menu routes, and the History toolbar has
  an internal horizontal scroll container. Focused GUI evidence is `18
  passed`; complete deferred-startup Qt grabs show content fitting its viewport
  at default and maximized sizes with the task card visible. Fresh task-scoped
  verification passed task/memory, Ruff, compile/type, quality `282`,
  preprocessing `106`, and whitespace. Fresh full/boundary verification passed
  `2773 passed, 10 warnings` in `1451.67s`, including the boundary audit. The
  older order-sensitive full-suite failure is historical evidence only. The
  explicit GUI allowlist checkpoint was created locally without push.
  See `docs/agent/tasks/2026-07-27-gui-responsive-shell.md` and
  `docs/acceptance/2026-07-27-gui-responsive-shell.md`.

- SAXS Stage 7e series metric evidence is implemented locally: temperature and
  strain results now carry conservative per-metric summaries with coverage,
  frame-level counts, explicit missing/diagnostic/unusable reasons, and a
  Trend cap. Export keeps both series and frame evidence as read-only quality
  provenance. Focused evidence is `11 passed`; the complete SAXS matrix is
  `274 passed, 4 existing warnings`; quality/preprocessing gates are
  `282`/`106`. The task-scoped changed-file verifier is blocked by the
  pre-existing GUI `E731` at
  `polynexus/gui/main_window_shell_mixin.py:154`, which remains untouched.
  See `docs/agent/tasks/2026-07-27-saxs-series-metric-evidence-rollup.md`.

- SAXS AI Stage 7d candidate replay/calibration is checkpointed: the shared
  orchestrator records JSON-safe static/temperature/strain candidate trials,
  preserves the control engine, and exports replay rows as audit-only quality
  provenance. Calibration blockers cover incomplete expert cases, coverage,
  hard-guard false accepts, and expert disagreement. Focused replay evidence
  is `31 passed`; current-HEAD full/boundary evidence is `2671 passed, 10
  warnings` with boundary audit passed. Real model calls, confirmed reruns,
  expert-labelled promotion, and human scientific/GUI release review remain
  open.

- SAXS AI Stage 7c now tells the model the full policy-protected feature list
  and explicitly requires all seven SAXS features before an intent can be
  accepted. Prompt regression evidence is `20 passed`; core validation still
  fails closed for incomplete output.

- SAXS AI Stage 7b is wired through the shared preprocessing orchestrator:
  SAXS protected-field validation runs before candidate generation, and valid
  reports/source engines retain JSON-safe candidate-only plan/decision audit
  fields consumed by export. Focused bridge/handoff tests pass (`8`); the
  combined SAXS/orchestrator/preprocess matrix passes (`383`, four existing
  font warnings). Model calls, confirmed real reruns, calibration, and human
  scientific publication review remain open.

- SAXS real static/temperature/strain replay and external export provenance
  acceptance is automated-green: lifecycle `3 passed`, Workbench `9 passed`,
  and three real bundles register `quality_evidence.json`. The temperature
  fixture's existing validation error remains preserved. Restarted-GUI visual
  review and human scientific sign-off are still open. Current-HEAD full /
  boundary verification also passed `2662` tests with `10` warnings. Rendered
  bundle figures were inspected for basic rendering; the strain heatmap is
  close to saturation, which is retained as a scientific-review signal rather
  than interpreted automatically.

- SAXS Stage 8 export provenance is implemented locally: successful bundles
  include `quality_evidence.json` in `bundle_manifest.files`, preserving
  existing quality/sequence/2D/AI audit fields without changing results or
  publication roles. Focused export/provider evidence is `27 passed` and the
  full SAXS matrix is `260 passed` with four existing font warnings. Checkpoint
  verification and final real/GUI/scientific release review remain open.

- SAXS AI rescue Stage 7 is implemented locally as a contract bridge over the
  existing preprocessing optimizer. It validates untrusted SAXS intents,
  protects core physical features, emits candidate-only plans, and preserves
  shadow/confirm/calibrated tiered-auto semantics. Focused evidence is `4`
  passed, preprocessing integration is `48 passed`, and the complete SAXS
  matrix is `259 passed` with four existing font warnings. Candidate execution,
  model calls, calibration, UI confirmation, and publication audit remain open.
  Code checkpoint: `2eb3c49`.

- SAXS sequence rescue Stage 6 is implemented locally: existing deterministic
  non-primary `lc` paths are exposed as candidate-only evidence, missing frames
  are never fabricated, and accepted decisions require explicit hard,
  physical, data-preservation, and sequence gates. Focused evidence is `8`
  passed, the complete SAXS matrix is `255 passed` with four existing font
  warnings, and the task verifier passes quality `282`/preprocessing `103`.
  Candidate reanalysis, AI shadow/confirm, publication propagation, and human
  scientific review remain open.

- A new full-software vertical-delivery goal is active. It explicitly treats
  Results Workbench customization as a first-class product phase and requires
  each SAXS/DSC/WAXS/IR/NMR/Joint mode to complete analysis, evidence,
  Workbench, Figure Pack, Manifest/Gallery/Editor, export and acceptance before
  release claims.

- SAXS other-modules polishing is an active goal on the current development
  worktree. The first temperature slice is contract-only: provider regressions
  lock evolution/Avrami/waterfall/selected-evidence ordering and fallback
  roles. The strain slice now also routes its existing review summary/risk/
  next-step text through the shared review hint. Static comparison/support/
  diagnostic ordering is also covered by a dedicated regression; all three
  SAXS sub-projects are complete on the current branch.

- The dedicated local `main` worktree is at merge commit `583709ad`, which
  includes the Origin editor menu, run-root source-path fixes, visible native
  Origin activation, object-document routing, native plot rescaling,
  one-Graph multi-series export, source axis-scale forwarding, user-registry
  capability probing, and the GUI startup boundary restoration. It is ahead of
  `origin/main` locally; it has not been pushed.
- The active development worktree is `D:\PolyNexus` on
  `codex/origin-editor-usable-controls`, at the same merged commit. Its
  pre-existing untracked `.superpowers/` and Origin Lite design drafts are left
  untouched.
- The 2026-07-20 Origin-like editor integration checkpoint is part of the
  canonical branch finish sequence. It preserves the current workflow/editor
  surface while adding the transplanted direct-canvas annotation interactions
  and stabilized preview/commit drag transactions.
- The desktop GUI launch boundary is now `D:\PolyNexus`. The repository-local
  `scripts/launch_gui.py` prepends that root to `PYTHONPATH`, probes the imported
  `polynexus.__file__`, and reports branch/commit identity before starting the
  GUI, so stale editable-install worktrees cannot be selected silently.

## Important boundaries

- The normal figure gallery is manifest-only. Legacy recursive discovery stays
  behind the explicit recovery path; see decision `0003`.
- Generated figure documents store data-source paths relative to the active run
  when `path_kind` is `run_relative`.
- Gallery entries carry `run_root` into ChartEditor. Origin export carries that
  context as `ExportRequest.source_root`, and all Origin adapters use the shared
  `polynexus/origin/path_resolution.py` resolver before falling back to the
  figure directory and process working directory.
- When native Origin automation is available, the ChartEditor action now uses
  the `originpro` adapter to show/activate Origin and leave the created graph
  visible; see decision `0011`.
- Origin capability probing checks `ORIGIN_EXE` in the current process first and
  then reads the Windows user environment registry, so a `setx ORIGIN_EXE ...`
  configuration is recognized without restarting the GUI process.
- Origin export is optional and Windows-only. Adapter order is high-level
  `originpro`, COM/LabTalk, then an Origin-compatible package fallback. The GUI
  must remain usable without Origin installed.
- Native OriginPro export now maps each plot's `data_ref` to its own worksheet,
  applies document colors/names and balanced display line widths, sets the
  four frame-axis thicknesses, and forwards first-panel axis labels in addition
  to axis scales. Mathtext labels are converted to readable Unicode at the
  native boundary, and all plots still reuse one Graph.

## Verification evidence

- SAXS sequence rescue candidate evidence is implemented and verified: focused
  tests `8 passed`, full SAXS matrix `255 passed, 4 warnings`, structured
  verifier quality `282` and preprocessing `103`. Candidates remain
  candidate-only and preserve original/missing frames; re-analysis, AI
  shadow/confirm-only, real-data, publication, and scientific review remain
  open.

- Current-HEAD full/boundary verification after the SAXS detector/orientation
  checkpoint passed `2647 tests, 10 warnings in 1389.67s (23:09)` with a
  passing boundary audit. Automated release evidence is green; restarted-GUI
  visual review, human scientific sign-off, IR mapping semantics, and final
  release policy remain open.

- SAXS 2D detector/orientation evidence is implemented and verified: focused
  tests `6 passed`, full SAXS matrix `250 passed, 4 warnings`, structured
  verifier quality `282` and preprocessing `103`. The new contracts preserve
  source/metadata limitations and cap orientation claims at `Trend`; real raw
  detector geometry/mask propagation, publication, and human scientific review
  remain open.

- SAXS 2D detector/orientation evidence mode propagation is now implemented and
  verified. Static, temperature, and strain frame/point DTOs deep-copy existing
  `detector_quality_report` and `orientation_evidence`; static batches and
  condition series retain missing-frame/source metadata and conservative
  summaries, with temperature alignment keyed by `source_index`. Workbench
  Diagnostics, History parameters, and `quality_evidence.json` preserve the
  fields without folding orientation into generic 1D metric review. Focused
  propagation tests pass (`11` new, `53` compatibility); the full SAXS matrix
  passes `301` with four existing font warnings; structured verification passes
  quality `282` and preprocessing `106`. No new 2D algorithm, raw-detector
  inference, AI call, or scientific sign-off was enabled.

- SAXS mode evidence propagation Stage 4 is implemented and verified:
  temperature/strain point results retain frame-local quality and 1D method
  evidence, failed frames remain absent, and both DataFrames expose compact
  metric-level summaries. Focused propagation evidence is `26 passed`; the
  exact 38-file SAXS matrix is `244 passed` with four existing font warnings;
  structured verification passes quality `282`/preprocessing `103`. The
  separate 2D detector/orientation transport closure is now complete; raw
  detector quality, orientation uncertainty calibration, AI rescue, publication
  and human science acceptance remain separate.

- SAXS 1D method evidence Stage 3 is implemented and verified: conservative
  Porod/Kratky/Q*/lamellar `MetricEvidence` builders are attached to
  `SAXSResult.metric_evidence` while legacy outputs remain unchanged. Builder
  focused tests pass (`5`), the combined SAXS evidence matrix passes (`34`),
  and the exact 37-file SAXS matrix passes (`242`, four existing Arial CJK font
  warnings). Structured verification passes quality `282` and preprocessing
  `103`. Method-specific quantitative cutoffs, sequence propagation to all
  modes, AI rescue, publication, and human scientific acceptance remain open.

- A fresh real published-run replay on 2026-07-27 passed `15` cases in
  `338.23s` using an external basetemp. It covers all current automated SAXS,
  DSC, WAXS, IR, and NMR mode rows through Manifest/Gallery, Editor revisions,
  export provenance, and History restore. The 11 warnings are existing DSC
  polyfit-conditioning and missing-CJK-glyph warnings. This is stronger
  lifecycle evidence, not a scientific sign-off; restarted-GUI visual review,
  IR mapping semantics, and final publication/release decisions remain open.

- SAXS temperature Guinier Stage 2 sequence evidence is now implemented and
  verified: focused Guinier/temperature tests `11 passed`, full SAXS file
  matrix `237 passed, 4 warnings`, quality gate `282 passed`, preprocessing
  gate `103 passed`, plus task-card/memory/Ruff/compile/whitespace checks.
  `GuinierSequenceEvidence` is capped at sequence-level `Trend`; it preserves
  missing/failed/invalid/duplicate positions and reports continuity breaks as
  diagnostic evidence without interpolation or `Rg` mutation. Real-data
  threshold calibration, AI shadow/rescue, publication, and human scientific
  or GUI acceptance remain open.

- SAXS temperature Guinier Stage 1 is checkpointed at `17dcb0b`. The new
  deterministic evidence path has focused propagation evidence (`24 passed`),
  complete SAXS matrix evidence (`227 passed`, four existing font warnings),
  quality gate evidence (`282 passed`), preprocessing gate evidence (`103
  passed`), and a passing structured verifier. Core/temperature legacy Ruff
  baseline findings remain a separate known limitation and are not evidence of
  a scientific regression. The next active slice is sequence-level Guinier
  trend/continuity grading without fabricating missing temperature frames.

- SAXS temperature Guinier evidence Stage 1 is implemented and freshly
  re-verified (main code checkpoint `17dcb0b`):
  existing per-frame Guinier fits now carry strict-JSON fit/uncertainty,
  applicability, qRg, and data-quality evidence into `SAXSResult` and
  `TemperaturePointResult`; failed frames remain missing rather than being
  interpolated. Focused evidence is 36 passed, the full SAXS file matrix is
  228 passed with an external basetemp, and the structured verifier passes
  quality 282/preprocessing 103. Sequence-level trend fusion, rescue/AI,
  publication, real-data, and human GUI/scientific acceptance remain open.

- SAXS quality-contract Stage 0 is now isolated as a typed, strict-JSON
  contract layer for data defects, metric evidence, and rescue validation.
  Focused tests pass (`7`), the SAXS regression matrix passes (`37`), and the
  implementation deliberately has no
  temperature/strain/static analysis or AI rescue side effects yet. Task card:
  `docs/agent/tasks/2026-07-27-saxs-quality-contracts-stage0.md`.

- The 2026-07-26 complete 2D publication performance slice is implemented:
  WAXS strain image-grid snapshots are vectorized and capped at 256×256 per
  frame, while IR temperature-2D correlation snapshots are capped at 420×420
  and duplicate generic per-frame figures are omitted when the temperature
  series is present. Raw analysis arrays and scientific roles are unchanged.
  Focused WAXS matrix: 23 passed; focused IR matrix: 20 passed.
- The complete real WAXS strain and IR temperature-2D shared lifecycle passed
  2 cases in 101.39s; the expanded real published-run matrix now covers 15
  cases
  in a historical 276.15s run through Manifest/Gallery, Editor revisions, export provenance,
  and History restore. DSC non-isothermal correctly remains SI/diagnostic-only
  where the fixture has one valid conversion curve. Task card:
  `docs/agent/tasks/2026-07-26-2d-publication-render-performance.md`.

- The 2026-07-20 editor interaction reliability slice adds stable static body
  drag/resize transactions, generated text/rectangle body dragging, visible
  distance-aware curve bends, line endpoint-preserving body movement, fixed
  context-bar layout, and selection viewport preservation. Focused interaction
  tests pass (`109`), remaining ChartEditor-related modules pass (`156`), and
  targeted legacy ChartEditor drag/undo/static checks pass (`7`). The task card
  is `docs/agent/tasks/2026-07-20-editor-interaction-reliability.md`.

- The 2026-07-20 editor workflow completion slice passed its focused regression
  matrix (`354 passed`), structured verifier, and default verifier. It adds
  document diagnostics, distribution/visibility/layers/context actions,
  templates/format painter, previewed batch editing, comparison/revision diff,
  and export presets; see task card
  `docs/agent/tasks/2026-07-20-editor-workflow-completion.md`.

- Unified GUI launcher tests: 6 passed; system and bundled Python diagnostic
  probes both resolved `D:\PolyNexus\polynexus\__init__.py` on the active
  development branch before the implementation checkpoint.
- Origin capability, adapter, contract, package, and ChartEditor Origin tests:
  44 passed.
- GUI-startup regression checks: 3 passed.
- ChartEditor regression suite: 238 passed.
- Origin-like editor integration matrix: 358 focused editor/layout/workflow
  tests passed in stable Qt batches, plus 66 generated drag/geometry/render/core
  tests.
- Native Origin source/style fidelity suite: 16 passed.
- Native Origin label-display follow-up: 18 passed in the combined focused
  Origin suite.
- Native Origin style-polish follow-up: 18 passed in the combined focused
  Origin suite; the live five-plot smoke read back 1.2-point plot lines and
  0.8-point `x/x2/y/y2` frame axes.
- Automatic-commit regression tests: 2 passed.
- Ruff checks and `compileall` passed for the changed Origin/editor modules.
- The repository verification tooling was restored in commit `6002221`,
  including `scripts/verify.py`, `scripts/agent_memory.py`,
  `scripts/task_check.py`, and `pyrightconfig.json`. The prescribed command
  `python scripts/verify.py --changed --types` now passes, including the
  memory check, changed-file checks, focused quality gate, and preprocessing
  optimization gate.
- Worktree lifecycle management is available through
  `scripts/worktree_manager.py`. It uses a user-level registry, structured WIP
  archives, Git state rechecks, and a one-hour cleanup cooldown; existing
  unregistered worktrees remain protected.

## Known limitations and next actions

- The workflow-convergence Goal is active on `codex/origin-editor-usable-controls`.
  Commits `6857f05`, `8f254d1`, `0cc03b5`, `03e9090`, `a4fa6e3`, and `8a6075f`
  add workspace context safety, editor capability labels, run stages/cancel/retry,
  split export intents, selection-activated gallery actions, a diagnostics drawer,
  and narrow-window shell reduction. Focused checks for these slices are green.
- The 2026-07-23 workflow hardening checkpoint removes the reproducible
  Windows Qt access violation in the legacy `LayerTreeItem` visibility path by
  deferring tree reconstruction until `itemChanged` returns. The full
  `tests/test_chart_editor.py` invocation now passes (`238`) with an external
  `--basetemp` directory.
- `scripts/verify.py --changed --types` currently reports the repository's
  pre-existing Ruff baseline in the monolithic `main_window.py`; changed behavior
  was validated with focused pytest and `py_compile` checks.

- The 2026-07-26 Qt lifecycle slice adds parent-owned preview timers, a
  collision-free MainWindow workspace summary label, and ChartEditor teardown
  isolation. Its focused evidence is viewer/lifecycle 23, ChartEditor + DSC
  lifecycle 251, workspace/AI context 11, and MainWindow persistence 197;
  the current combined lifecycle/editor recheck is `274 passed`. The
  MainWindow lint baseline is checkpointed separately at `cbb3077`, and the
  current full/boundary verifier passes `2671` tests with `10` known warnings.
  Lifecycle code checkpoint: `fbf22b6`; restarted-GUI and human release review
  remain open.

- On 2026-07-26 the MainWindow import baseline was repaired without broad
  file-level suppression: symbols consumed through `main_window_module.*`
  remain explicit compatibility exports, and dead imports were removed. The
  complete MainWindow persistence file passes (197); checkpoint `cbb3077`.
  Default changed/type verification passes with quality 282 and preprocessing
  103. The full/boundary variant timed out after 15 minutes without a summary.

- The final workflow-focused matrix passes (`118`, four known Matplotlib
  tight-layout warnings), along with the structured task verifier, quality
  gate (`282`), preprocessing optimization gate (`103`), and GUI launcher
  diagnostic. Copyable error diagnostics and the immutable GUI `RunState`
  service are now explicit boundaries; a human visual walkthrough remains
  pending for static/generated/log-axis interactions and narrow-window shell
  presentation.

- A live style smoke export using the configured `Origin64.exe` returned
  `success/originpro` for a synthetic five-plot document. In-process
  inspection found one Graph, five plots, five document colors, five 1.2-point
  display lines, 0.8-point `x/x2/y/y2` frame axes, five source worksheets,
  named Y columns, a `log10` Y axis, and clean Unicode axis labels. The
  temporary `.opju` remains locked until Origin closes; this is expected
  application ownership.
- The Origin-like editor integration is local-only and is advanced through the
  repository maintenance finish sequence; an explicit push decision remains
  pending.
- The 2026-07-24 LegendLayout refactor is complete on the active branch.
  Generated legend placement, selection, drag/resize, inspector, and export
  now share `polynexus/core/figures/legend_layout.py`; focused compatibility
  and editor coverage is `292 passed`. Corner resize also scales legend text
  continuously during preview and restores box/font together on undo. Manual
  GUI review of static, log-axis, and multi-series visuals remains pending
  because Chromium is unavailable.
- The 2026-07-24 LegendGeometry persistence follow-up is complete. Canonical
  `legend_geometry` now survives editor command/store/save boundaries, legacy
  placement keys are removed after an explicit geometry edit, and automatic
  legacy anchors remain readable through one importer. The focused
  legend/editor matrix passes `297`; structured and default changed/type
  verifiers both pass. Manual visual review after GUI restart remains pending.
- The same LegendGeometry slice now includes draw-time synchronization for
  display-space legend selection overlays, covering the real GUI's post-layout
  canvas resize path. The adapter and ChartEditor resize regressions pass.
- Reconcile the older active-work entries in `active-work.md` against the
  current branch/PR state before using them as authoritative.

## Latest full-software checkpoint

### Runtime/editor regression checkpoint (2026-07-26)

- The first Qt runtime shard exposed two ChartEditor regressions: mixin MRO
  ownership of `_sync_annotation_property_controls` and nested inspector
  controls retaining wide size hints. The fixes restore annotation-controls
  ownership and make nested responsive controls shrink without horizontal
  scrolling.
- `FigureRenderAdapter` now preserves legacy text persisted-geometry/data-space
  fallback while retaining display-space rendered extents for explicit axes
  text. Live text preview moves synchronize the existing frame and handles
  immediately. GUI-created `PolyNexusLogger` state is restored between tests so
  fallback warnings remain observable to `caplog`.
- Focused runtime evidence is recorded in
  `docs/agent/tasks/2026-07-26-full-suite-runtime-investigation.md`.
- The task-scoped verifier passed with quality gate 282 and preprocessing gate
  103. The full verifier passed: 2587 tests, 8 warnings, 1042.86 seconds, and
  the boundary audit passed. The 8 warnings are the existing tight-layout and
  Arial glyph warnings listed in the verifier output.
- Automated release gates are green, but restarted canonical GUI visual
  review, publication-role review, IR vendor mapping/ROI semantics, and
  assignment-limited NMR/Joint scientific sign-off remain human gates.

- A fresh real-fixture audit on 2026-07-26 completed DSC standard, WAXS
  static/temperature, IR standard, and SAXS temperature engine publication
  runs. SAXS temperature retained a validation error for contaminated Q* and
  diagnostic-only lamellar evidence; it is not a normal-science release pass.
  WAXS strain and IR temperature-2D exceeded the bounded real-run diagnostic
  timeout. Evidence is in
  `docs/acceptance/2026-07-26-real-published-run-audit.md`.
- Figure SCI audit now ignores only Matplotlib colorbar auxiliary axes after
  the real SAXS heatmap exposed false `missing_axis_label` and
  `non_standard_axis_label` errors. Focused coverage is in
  `docs/agent/tasks/2026-07-26-colorbar-audit-regression.md`.
- The real published-run walkthrough matrix now covers fifteen cases across
  SAXS static/temperature/strain, DSC standard/isothermal/non-isothermal,
  WAXS static/temperature/strain/2D, IR standard/temperature-2D, and NMR
  liquid/solid H/C, with non-isothermal and diagnostic-only roles preserved;
  the shared run ID survives Gallery, Editor revisions, export provenance, and
  History restore. Bounded real two-frame smoke evidence covers WAXS strain/2D
  and IR temperature-2D. Full-mode and visual/scientific acceptance remain
  open. Evidence is in
  `docs/acceptance/2026-07-26-real-published-run-audit.md`.

- The requirement-by-requirement baseline ledger is recorded in
  `docs/acceptance/2026-07-25-full-software-baseline.md`. Core matrices pass
  with external basetemps (SAXS 210, DSC 64, WAXS 46, IR 30, NMR 24, Joint
  18); this does not constitute full vertical or release acceptance.

- Results Workbench Phase 1 is implemented locally: typed profile registry,
  SAXS mode-specific narrative and Figure IDs, generic DSC/WAXS/IR/NMR/Joint
  registrations, profile-driven Qt shell states, and gallery/review routing.
- Acceptance evidence is recorded in
  `docs/acceptance/2026-07-25-results-workbench-phase1.md`.
- This does not mark any technique vertical slice complete; SAXS still needs
  end-to-end Figure Pack, Gallery/Editor/export, fallback, AI-off, and human
  visual/scientific acceptance.
- The SAXS code checkpoint is now implemented: real Manifest ID routing,
  fallback candidate selection, and figure/gallery regression evidence are
  recorded in `docs/acceptance/2026-07-25-saxs-full-vertical-slice.md`.
- DSC standard/isothermal/non-isothermal now have mode-specific Workbench tabs
  and publication-provider Manifest ID contracts; evidence is recorded in
  `docs/acceptance/2026-07-25-dsc-workbench-checkpoint.md`.
- WAXS static/temperature/strain now have mode-specific Workbench tabs and
  provider Manifest ID contracts, including 2D strain routing; evidence is in
  `docs/acceptance/2026-07-25-waxs-workbench-checkpoint.md`.
- IR temperature-2D now consumes its existing analysis result through the
  shared FigureDefinition/Manifest pipeline. The mode has real logical IDs for
  heatmap, band tracking, band indices, and 2D-COS diagnostics; mapping/ROI and
  the complete IR vertical acceptance remain open. Evidence is in
  `docs/acceptance/2026-07-25-ir-temperature-2d-workbench-checkpoint.md`.
- IR mapping/ROI now has a conservative typed handoff and shared lifecycle:
  explicit scalar map/coordinates/mask/ROI spectra/provenance, structural
  evidence, three publication-role FigureDefinitions, engine handoff, and
  Workbench links. It deliberately does not infer an instrument file format or
  band meaning. Evidence is in
  `docs/acceptance/2026-07-25-ir-mapping-roi-checkpoint.md`; real reader/fixture
  and visual/fallback acceptance remain open.
- NMR/Joint published-run provenance now has a focused synthetic matrix:
  NMR Main/diagnostic roles are explicit, both NMR and Joint active Gallery
  entries resolve run-relative documents/data, and failed diagnostic entries
  remain visible in the Manifest. Real-data, export-bundle, AI/fallback, and
  restarted-GUI release acceptance remain open.
- Joint hub rows now have a shared FigureDefinition provider and Coordinator
  publication entrypoint for crystallinity, multiscale, and evidence-coverage
  figures; `JointHubWorker` attaches Manifest context to real GUI run reports.
  Joint completion persists History, renders the custom Workbench profile, and
  export bundles preserve `metadata/runs/<run_id>/`. Active Gallery selection
  against a real run, scientific conflict provenance, fallback/AI-off paths,
  and visual/release acceptance remain open. Evidence is in
  `docs/acceptance/2026-07-25-joint-figure-provider-checkpoint.md`.
- Joint validation conflicts now carry source-run and evidence-weight
  provenance, and all Joint figure recipes preserve the same batch-level run
  provenance. This is recorded in
  `docs/acceptance/2026-07-25-joint-conflict-provenance.md`; it does not replace
  the remaining real-data, visual, export, or AI/fallback release gates.
- Joint's automated lifecycle is now independently closed by
  `tests/test_joint_lifecycle_closure.py`: one run ID survives publication,
  active Gallery selection, Editor working/published revision, export
  `metadata/runs/` and active pointer, and History restore. Evidence is in
  `docs/acceptance/2026-07-25-joint-lifecycle-closure.md`. This does not close
  real-data, restarted-GUI, or human scientific release review.
- NMR liquid/solid H/C profiles and shared FigureDefinition/export behavior are
  covered by a focused 29-test checkpoint; assignment-limited solid-state Xc
  remains provisional. Real partition visual and full provenance/release
  acceptance remain open. Evidence is in
  `docs/acceptance/2026-07-25-nmr-workbench-checkpoint.md`.
- Shared AI preprocessing now carries normalized fallback state/reason and
  rejects fallback-active candidates before scoring for DSC, IR, WAXS, SAXS,
  and NMR. The AI-off/failure/fallback contract matrix is covered by
  `tests/test_preprocess_cross_technique_matrix.py`,
  `tests/test_preprocess_ai_off_compat.py`, and
  `tests/test_preprocess_fault_injection.py`. Joint remains report-level AI
  review only; real/Golden and GUI/scientific acceptance remain open.
- IR standard now has explicit conservative Main/SI/diagnostic roles for
  spectra, fits, computed comparison, and crystallinity; temperature-2D and
  mapping/ROI role matrices plus sibling-safe Manifest failure visibility are
  regression-covered. The focused checkpoint is recorded in
  `docs/acceptance/2026-07-25-ir-three-mode-vertical-slice.md`; real reader,
  AI/fallback, export-bundle, and restarted-GUI release gates remain open.

## Latest audit (2026-07-25)

- `d0142d6` adds ordinary NMR `AnalysisResult` evidence persistence and a Joint
  publish-to-History-to-active-Gallery Qt regression; `4d5c14a` checkpoints the
  recent task cards; `1dee259` records the four-partition real NMR engine smoke.
- Focused NMR/evidence/persistence tests: 20 passed. Joint/Manifest/GUI restore
  slice: 8 passed. The default `python scripts/verify.py --changed --types`
  passed with quality gate 282 and preprocessing gate 103.
- The full `python scripts/verify.py --changed --types --full --boundary`
  command was run with an external basetemp and timed out after 364 seconds
  (exit 124) without a failure summary; this is a verification limitation,
  not a pass.
- The overall goal remains active. IR vendor mapping semantics, per-mode real
  export/Editor/restart walkthroughs, AI-off/failure/fallback scientific
  review, and human release approval remain open acceptance boundaries.

- Ordinary DSC, WAXS, and IR engine analysis now attach shared
  `AnalysisEvidence` through `analysis_evidence_handoff`, with a representative
  typed result plus scalar series metadata. Existing richer evidence remains
  authoritative; focused coverage is recorded in
  `docs/acceptance/2026-07-25-unified-engine-evidence-handoff.md`.
- DSC standard, isothermal, and non-isothermal now have one shared lifecycle
  regression covering publication, active Manifest/Gallery, editor working and
  published revisions, export figure-run provenance, and History restore. The
  lifecycle matrix is recorded in
  `docs/acceptance/2026-07-25-dsc-lifecycle-closure.md`; automated GUI restart,
  real-data scientific sign-off, and AI-off/failure/fallback release review
  remain open.
- WAXS static, temperature, and strain now have one shared lifecycle
  regression. Static/temperature use the ordinary project service; strain
  preserves its reactive V2 image-grid edit/save/publish route. Evidence is in
  `docs/acceptance/2026-07-25-waxs-lifecycle-closure.md`; restarted-GUI 2D
  review, scientific sign-off, and AI-off/failure/fallback release review
  remain open.
- IR standard, temperature-2D, and mapping/ROI now have one shared lifecycle
  regression over explicit typed DTOs. Mapping provenance and invalid-pixel
  diagnostics remain preserved without vendor or band semantics inference.
  Evidence is in `docs/acceptance/2026-07-25-ir-lifecycle-closure.md`;
  vendor-input, real/Golden, restarted-GUI, and AI/fallback review remain open.
- NMR liquid/solid H/C now have a real-fixture lifecycle regression over
  `NMREngine.run_pipeline`, evidence, Manifest/Gallery, editor revisions,
  export provenance, and History restore. Solid 13C assignment-limited Xc is
  still provisional. Evidence is in
  `docs/acceptance/2026-07-25-nmr-lifecycle-closure.md`; restarted-GUI,
  scientific sign-off, and AI/fallback review remain open.
