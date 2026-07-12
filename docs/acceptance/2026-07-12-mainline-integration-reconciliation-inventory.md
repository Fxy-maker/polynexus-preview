# Mainline Integration Reconciliation Inventory

日期：2026-07-12
任务：mainline-integration-reconciliation-2026-07-12
状态：基线盘点完成；代码冲突尚未处理

## 1. Immutable refs

    origin/main
    985724fdd18c70a126baff1ffc1397dbb3832487

    origin/codex/runtime-unified-tables
    f09b00b2ae4ba83197990e2d3f50b3470378d427

    common merge base
    b9dfe66f0c943134a1c4d5a209f30386e203e45b

The diagnostic worktree was created from origin/main at 985724fd:
C:\Users\Fan Xuyi\.config\superpowers\worktrees\PolyNexus\mainline-integration-reconciliation

The user worktree D:\PolyNexus remains on codex/runtime-unified-tables and was not used for edits or conflict resolution.

## 2. Divergence measurements

    git rev-list --left-right --count origin/main...origin/codex/runtime-unified-tables
    60    161

From the common ancestor, main has 60 commits and the integration branch has 161 commits.

The PR diff is:

    419 files changed
    85,081 insertions
    3,266 deletions

Patch-equivalence-aware history classification from git log --left-right --cherry-mark:

    main-only non-equivalent commits: 43
    patch-equivalent commits: 34
    integration-only non-equivalent commits: 144

The patch-equivalent count proves that part of the history was replayed or independently recreated. Equal patch content does not make the histories mergeable because the surrounding files and contracts continued to evolve independently.

## 3. Actual conflict surface

git merge-tree --write-tree origin/codex/runtime-unified-tables origin/main reports 92 unique conflict paths:

    docs       2
    polynexus 58
    tests     32

Representative conflict families:

- Shared figure contracts and lifecycle:
  polynexus/core/figure_objects.py
  polynexus/core/figures/contracts.py
  polynexus/core/figures/manifest.py
  polynexus/core/figures/pipeline.py
  polynexus/core/figures/renderer.py
- Technique providers:
  polynexus/core/dsc.py
  polynexus/core/dsc_engine/figure_provider.py
  polynexus/core/saxs.py
  polynexus/core/saxs_engine/figure_provider.py
  polynexus/core/waxs.py
  polynexus/core/waxs_engine/figure_provider.py
- GUI state and service boundaries:
  polynexus/gui/main_window.py
  polynexus/gui/main_window_*_mixin.py
  polynexus/gui/plot_gallery_service.py
  polynexus/gui/i18n.py
- Regression contracts:
  tests/test_saxs_*.py
  tests/test_figure_*.py
  tests/test_main_window_*.py
  tests/test_manifest_editor_shared_plan.py

This is a semantic integration surface, not whitespace or a single stale file.

## 4. Main-only change families

The main-only side contains the already merged mainline sequence:

- 3ecf609 feat: unify figure artifact lifecycle across all techniques (#4)
- 240336a3 test: lock mainline publication cutover boundary
- fed58525 feat(saxs): lock temperature strain publication boundary
- 4e0d31bc fix(editor): hydrate style context from current document (#6)
- 1c3464c4 docs: record manifest-only gallery fallback strategy (#7)
- 985724fd feat(gui): implement final streamlining interaction plan (#8)

These commits establish the current GUI, editor, gallery, and production publication authority.

## 5. Integration-only change families

The integration side contains the broader parallel stack:

- unified tables and structured result adapters
- DSC publication provider recipes and evidence gates
- WAXS static/temperature/strain publication packs
- additional SAXS publication provider and evidence changes
- GUI result/table service wiring and workspace compatibility fixes
- repeated figure lifecycle and editor/gallery changes from an earlier architectural state

Examples near the branch tip:

- 1eaaad30 feat(waxs): publish figure packs through shared lifecycle
- 1e556ffd merge: integrate DSC publication figure packs
- 627d6d5f merge: integrate GUI function streamlining
- added98a merge: integrate unified tables
- ebec70dc fix(waxs): close publication gate and fallback gaps
- 20d7b928 fix(saxs): ignore generated output assets during directory scan
- f09b00b2 docs: record SAXS cutover execution evidence

The presence of earlier GUI/figure integration commits on this side does not supersede the later mainline commits; it is evidence that the same boundaries were implemented in parallel.

## 6. PR state

PR: https://github.com/Fxy-maker/polynexus/pull/9

    state: OPEN
    base: main at 985724fd
    head: codex/runtime-unified-tables at f09b00b2
    mergeable: CONFLICTING
    merge state: DIRTY
    status checks: no rollup available while the PR is conflicting

No merge, force-push, conflict resolution, or PR closure was performed during this inventory step.

## 7. Verification baseline

The clean origin/main worktree ran:

    python -m pytest -q

Result: timed out after approximately 304 seconds without reporting a failing test.

This is a repository-runtime limitation, not evidence that the baseline passes. Subsequent slices must use focused test groups first and record any full-suite timeout separately.

The clean diagnostic worktree status after inventory collection was:

    ## codex/mainline-integration-reconciliation...origin/main

## 8. Decision gate

Before moving code, a human reviewer must approve:

1. origin/main as the canonical GUI/editor/gallery and shared lifecycle base.
2. The single canonical figure manifest/publisher/audit contract.
3. Whether SAXS/DSC/WAXS provider implementations are ported as separate slices.
4. Which unified-table/result adapters are still absent from main and therefore in scope.
5. The order and rollback boundary of the replacement PRs.
6. Keeping PR #9 open as a reference until replacement coverage exists.

## 9. Provisional canonical-source matrix

| Change family | Evidence on main | Evidence on integration branch | Provisional handling | Human decision |
|---|---|---|---|---|
| Shared figure lifecycle/contracts | main contains the shared publisher, manifest gallery/editor lifecycle, recovery view, and lifecycle tests | integration contains later image-grid, audit, publication-role, and TIFF changes on the same contract files | Keep main lifecycle as the base; port only behaviorally distinct contract/audit improvements | Confirm one manifest/publisher/audit contract |
| GUI streamlining/editor/gallery | main contains final streamlining PR #8, style-context fix, manifest-only gallery strategy, and streamlining tests | integration contains earlier workspace navigation, result review, and legacy gallery fallback implementations | Treat main as GUI authority; do not re-port duplicate navigation or legacy discovery | Confirm retained result/table entry points |
| SAXS temperature/strain | main contains the production publication boundary and provider baseline | integration contains mode precedence, evidence-label, reliability, and generated-asset fixes plus a later provider stack | Preserve main cutover boundary; evaluate each integration fix against current provider contracts | Confirm Main/SI/Diagnostics semantics and acceptance baseline |
| DSC publication providers | main contains the initial DSC figure-definition provider migration | integration contains publication recipes, curve/evidence gates, crystallinity handling, and real-data tests | Port as an independent DSC evidence/provider slice | Confirm scientific gate and baseline changes |
| WAXS publication providers | main contains the initial WAXS figure-definition provider migration | integration contains static/temperature/strain packs, audit closure, no-main reasons, and real-data tests | Port as an independent WAXS publication slice | Confirm role/fallback semantics |
| Unified tables/results | main does not contain the integration branch's structured result table service family | integration contains table contracts, management adapters, result panels, export, and GUI wiring | Treat as integration-only; port behind AnalysisResult and current GUI boundaries | Confirm table status/persistence contract |
| Agent docs/process assets | not part of the committed mainline baseline | current D:\PolyNexus worktree contains untracked AGENTS/docs/scripts and user edits | Exclude from source integration; add only through separately reviewed process commits | Confirm ownership before staging |

The matrix is provisional by design. It identifies the source of truth for slicing, but does not authorize a semantic merge. Any row involving publication roles, evidence gates, persistence, or GUI state requires human review before code movement.

## 10. First slice execution evidence

The first code slice was intentionally limited to backward-compatible panel identity metadata:

- Commit: 602a195b feat(figures): preserve panel identity metadata
- Production files: polynexus/core/figures/render_plan.py and polynexus/core/figures/renderer.py
- Regression file: tests/test_figure_render_plan_core.py
- New behavior: optional grid spans, optional panel labels, stable panel GIDs, and stable panel-label GIDs; existing payloads retain defaults of one cell and no label.
- TDD RED: both new tests failed on origin/main with missing RenderPanel.row_span and missing axis GID.
- TDD GREEN: the same tests passed after the minimal implementation.
- Focused regression result after commit: 28 passed in 3.14 seconds.
- compileall for the two production files: passed.
- git diff --check: passed.
- No source files outside this slice, no PR update, and no mainline merge were performed.

The following two contract slices were then completed on top of that metadata:

- Commit 016f145e feat(figures): add structured publication audit service
  - Added FigurePublicationAuditResult and FigurePublicationAuditService.
  - Added four tests covering structured issues, compliant plans, cleanup on audit failure, and payload copying.
  - TDD RED was the expected module import failure on origin/main; GREEN produced 4 passed.
- Commit 6606b0e6 feat(figures): carry publication audit through export
  - Added the audit result to FigureArtifactExportResult and injected the audit service into FigureArtifactExportService.
  - Existing export inspection and atomic staging behavior remain unchanged.
  - Focused shared figure/export regression result after commit: 39 passed in 5.11 seconds.

The capability/status, TIFF asset, persistence, and technique-provider consumers are deliberately not included in these slices.

The TIFF asset support was then integrated as an independent compatibility slice:

- Commit 0090aa9c feat(figures): read TIFF asset dimensions
- Production file: polynexus/core/figure_assets.py
- Regression file: tests/test_figure_assets.py
- TDD RED: the new TIFF dimension test returned (0, 0, 0) on origin/main.
- TDD GREEN: Pillow-backed width, height, and averaged DPI extraction passed.
- Focused regression result after commit: 36 passed in 4.46 seconds.
- compileall and git diff --check: passed.

Checkpoint boundary: the next candidate is capability/status and persistence propagation. It must be handled as a separate result-contract slice with explicit default/legacy-read tests; it is not included yet.

The capability/status and persistence propagation slice is now complete:

- Commit bb92e22a feat(figures): expose publication audit capability status
  - FigureCapabilityReport now carries audit_passed and structured audit_issues.
  - Explicit audit failure maps to quality_failed after artifact inspection succeeds.
  - Missing audit input keeps legacy callers compatible with a passing default.
  - FigurePipeline forwards export audit into the capability report.
- Commit cdf4eeba fix(figures): preserve audit status across revisions
  - Working saves reconstruct the prior audit result instead of clearing it.
  - Publish and recovery use the fresh export audit result.
  - Legacy manifests without audit fields remain compatible and are not downgraded to audit_not_run.
  - GUI editor, project, recovery, manifest, and gallery consumers were updated to expect quality_failed when the audit has errors.
- Focused result-contract/persistence regression result after commit: 49 passed in 6.59 seconds.
- compileall and git diff --check: passed.

The next boundary is technique-provider migration; no SAXS/DSC/WAXS provider code has been moved yet.

## 13. SAXS provider migration boundary

The first SAXS comparison was intentionally diagnostic only. The integration branch cannot be cherry-picked as a small fix:

- main has the existing SAXS provider with direct temperature definitions, static/strain frame construction, and current mainline cutover tests.
- integration replaces that provider with a mode-aware dispatcher and adds separate figure_selection, figure_eligibility, figure_temperature, and figure_strain modules.
- the integration history includes ffcd0ddb fix(saxs): resolve completed result mode precedence, but that commit is based on the rewritten provider and does not apply cleanly to main's provider API.
- the compared provider change is an architectural rewrite of roughly 856 changed lines in figure_provider.py plus new provider modules and 576/554-line temperature/strain test suites.

Conclusion: SAXS temperature/strain migration is a separate scientific/provider task, not the next mechanical cherry-pick. It requires an explicit mode/evidence contract comparison and focused red-green tests on the current main provider before any production cutover.

## 14. SAXS mode/evidence contract slice

The first implementation slice stayed on the current main provider API and did not import the integration branch's temperature/strain provider rewrite:

- Added a backward-compatible `publication_role` field to `FigureDefinition`, defaulting to `si`, plus the immutable `FigureEligibilityDecision` contract.
- Added immutable `SAXSFrameView` snapshots so provider role decisions consume emitted arrays/parameters without reanalysis or mutation.
- Added deterministic mode resolution: completed temperature/strain results take precedence over configuration hints; mixed completed series are unsupported; an incomplete declared temperature/strain series does not fall back to static.
- Wired current SAXS frame definitions to carry `main`, `si`, or `diagnostic` based on emitted `quality_flag`, `paper_figure_candidate`, and `lc_reliability_status` evidence.
- Added `tests/test_saxs_mode_evidence_contract.py`; RED observed missing mode/evidence modules and default `si` role, then GREEN passed after the minimal implementation.
- Focused SAXS regression result: `31 passed in 0.85 seconds` across the new contract test, existing temperature provider, publication cutover, and temperature status groups.
- `python -m compileall -q polynexus/core/figures polynexus/core/saxs_engine` and `git diff --check` passed.

This slice does not claim the full SAXS temperature/strain publication pack migration. Representative-frame selection, technique-specific Main/SI/Diagnostics panel composition, and scientific provider parity remain separate follow-up slices requiring human review.

## 15. Cumulative review checkpoint

A read-only cumulative review of `origin/main..HEAD` found no Critical issues and identified four Important contract gaps, all fixed in commit `a81af58`:

- `publication_role` is now written into generated figure documents and legacy document normalization defaults it to `si`.
- Mixed frame roles now aggregate conservatively: all-main is `main`, mixed main/SI is `si`, and any diagnostic evidence prevents main promotion.
- Configuration temperature/strain mode is no longer masked by a stale static `_condition_type` hint when no completed result exists.
- Evidence roles and stable joined reasons are propagated into each definition recipe for document/publisher consumers.

The review also identified two Minor follow-ups, now covered by the same slice: invalid publication roles are rejected by figure-definition validation, and the task card correctly keeps the unimplemented temperature/strain filtering items unchecked.

Review and verification evidence:

- Reviewer: read-only cumulative diff review, no Critical findings.
- Review-fix regression group: 4 passed.
- Cumulative shared/SAXS regression group: `81 passed in 4.82 seconds`.
- Changed-file Ruff and py_compile: passed.
- compileall and git diff checks: passed.
- `scripts/verify.py` remains unavailable in the isolated branch because it is not part of clean `origin/main`; the user-worktree copy was not executed.

## 16. SAXS temperature/strain evidence-filtering rollout

The approved incremental path A is implemented without importing the integration branch's provider rewrite:

- Temperature commits: `985f9c2` and `a4231f8`.
  - Main temperature parameters and heatmap sources use the same emitted-evidence selected indices.
  - Rejected frames are omitted from main summary sources without scientific-value repair.
  - Recipes preserve included/omitted indices and stable omission reasons.
  - Per-frame roles and mixed-series roles are propagated through the current shared figure contract.
- Strain commit: `c75888b`.
  - Current strain frame IDs, labels, ordering, and waterfall objects remain stable.
  - Mixed main/diagnostic evidence is conservatively diagnostic; evidence reasons and included/omitted indices are persisted in the recipe.
- Verification:
  - Temperature focused group: `27 passed`.
  - Strain/SAXS focused group: `21 passed`.
  - Cumulative shared/SAXS group: `89 passed in 4.91 seconds`.
  - Changed-file Ruff, py_compile, compileall, and `git diff --check`: passed.
- Temperature slice review: no Critical or Important findings; two Minor findings were fixed in `a4231f8`.
- Strain slice review: the review worker could not access workspace tools and returned no evidence-backed findings; subsequent human scientific review completed with no blocking concerns.

This completes the locally reviewed temperature/strain implementation checkpoint, not the overall mainline reconciliation. DSC/WAXS, Unified Tables, GUI wiring, replacement PRs, push, merge, and local-main synchronization remain pending.
