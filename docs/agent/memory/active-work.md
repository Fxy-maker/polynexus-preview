# Active Work

## Local GUI automation MCP bridge - ready for checkpoint (2026-08-09)

- `polynexus-mcp` now starts a separate visible GUI process and serves only
  launch/import/select/run/wait/result/capture/close through a stdio MCP
  server. The bridge is opt-in, uses a random session secret, binds only
  `127.0.0.1`, and never attaches to an existing user window.
- TDD bridge/MCP coverage passed `9`; focused startup/bridge/MCP coverage
  passed `15`; a real local lifecycle smoke launched, queried, and closed the
  dedicated session successfully. Structured verification passed changed-file
  Ruff/compile, quality `303`, preprocessing `157`, task/memory checks, and
  whitespace.
- The clean worktree full pytest baseline remains blocked at collection by
  three missing repository-external real-data fixtures. A real GUI scientific
  run was intentionally not performed without a user-provided disposable
  sample path because analysis creates output beside its input.
- Task card: `docs/agent/tasks/2026-08-09-gui-automation-mcp.md`.

## Canonical experiment templates and PA6 multi-program DSC - review required (2026-08-12)

- The agent-native workflow now consumes immutable, versioned canonical
  experiment templates rather than assuming a file or directory directly
  represents one experiment. The first implementation is a deterministic
  Mettler multi-program DSC converter with a reusable conversion record.
- Read-only inspection of external
  `C:\Users\Fan Xuyi\Desktop\文件夹\弹性体\弹性体中文\DSC-等温结晶\PA6-DWJJ.txt`
  confirmed multi-program holds at 180, 181, 182, 183, 184, and 185 C, preceded
  by 255 C preparation holds. The source is external and must remain unchanged.
- The converter records raw artifact identity, source row/time ranges, melt
  holds, and ramps. Only validated crystallisation holds reach the existing
  Avrami function; the template execution path maintains one template segment
  to one fit, rather than heuristically splitting it again.
- A read-only TPAE replay wrote only to
  `D:\PolyNexus-pa6-canonical-smoke-20260812-review-final\bundle`: six holds at 180--185 C,
  5.9500 mg sample mass, template hash
  `29659c6757fd98454e678cb4202739a2e2f95cb59c54e64592ab38f8a182331f`, and
  conversion hash `b80c477d93bddb76ff16b7be6bc06874b1a4ab3a9010160dfbc32f7bb6c5cb0f`.
  This remains scientific-review-required; no publication claim was made.
- AI may later propose the same template mapping DTO, but validation,
  provenance, and deterministic providers remain mandatory. No LLM call or
  AI-generated scientific numeric data is in this path.
- Design: `docs/superpowers/specs/2026-08-12-canonical-template-conversion-dsc-isothermal-design.md`.
  Task: `docs/agent/tasks/2026-08-12-canonical-template-conversion-dsc-isothermal.md`.

## Agent-native core and TPAE golden path - checkpoint pending review (2026-08-12)

- The approved product direction is a general agent-workflow architecture with
  one complete TPAE characterization workflow, rather than a simultaneous
  rewrite of all technique engines or the GUI.
- Public operations `inspect_data`, `propose_recipe`, `run_recipe`,
  `validate_run`, and `export_run` now adapt existing `AnalysisResult`, evidence,
  and figure recipe boundaries rather than replacing them. Contracts recursively
  freeze retained JSON data; the CLI persists a replayable run and emits exactly
  one JSON envelope per operation.
- Isothermal DSC is intentionally directory-sequence input. Inspection computes
  a deterministic directory-manifest hash, proposal validates manifest technique
  and format against its step, run/export prevent writes inside raw-data
  directories, and legacy pipeline error logs fail the public workflow step.
- A persisted recipe can be replayed without re-proposing from a manifest;
  exports keep figure references in `figures/manifest.json` and never copy raw
  or figure assets. The CLI requires an explicit output directory.
- Executed runs carry a local HMAC receipt across recipe, status, step results,
  evidence, and validation state; fabricated or evidence-tampered persisted
  runs cannot validate or export. Duplicate artifacts for a technique are
  rejected, so each workflow step has one deterministic raw input.
- Real TPAE data remains external and will be referenced through path/hash
  manifests; only synthetic fixtures and recipe contracts may enter Git.
- Design: `docs/superpowers/specs/2026-08-12-agent-native-core-tpae-golden-path-design.md`.
  Task: `docs/agent/tasks/2026-08-12-agent-native-core-tpae-golden-path.md`.
- Focused agent/TPAE/CLI/legacy-CLI suite passed `47`; structured verification
  passed Ruff, compile, quality `303`, preprocessing `157`, task/memory, and
  whitespace gates. The first implementation does not change scientific methods
  or GUI behavior; it requires an external, read-only TPAE manifest replay and
  scientific review before any manuscript or publication promotion.

## GUI performance recovery - checkpoint pending (2026-08-09)

- History now uses indexed header-only queries; full JSON hydrates only for a
  selected record, comparison baseline, or explicit export.
- MainWindow batches logs through a single-shot timer, escapes ordinary text,
  bounds the document at 500 blocks, and flushes/stops cleanly on close.
- Analysis completion persists immediately but schedules the non-critical
  History rebuild on the next event-loop turn. SAXS wraps its real
  load/preprocess/analyze/plot boundaries with diagnostic wall-clock logs.
- Focused history/startup/sample coverage passed `131`; completion scheduling
  passed `2`; SAXS timing passed `2`. Structured task verification passed Ruff,
  compile, type-baseline, quality `298`, preprocessing `157`, and whitespace.
- Task card: `docs/agent/tasks/2026-08-09-gui-performance-recovery.md`.
- Remaining: create the explicit local checkpoint commit; no push/merge.

## SAXS orientation evidence projection - completed (2026-08-08)

- Per-frame strain `_batch_data` now exposes the detector-plane evidence behind
  `f_Herman_raw`: axis degree/source, harmonic strength/significance, effective
  azimuthal bins, coverage, `orientation_cos2_avg`, and isotropic baseline.
- `orientation_cos2_avg` is preserved in the JSON orientation evidence contract;
  the GUI shows these scalar values in Diagnostics only. Effective tensile-axis
  Herman values and reliability gates are unchanged.
- Focused orientation/batch/result-table matrix passes `150`; task card:
  `docs/agent/tasks/2026-08-08-saxs-orientation-evidence-projection.md`.

## SAXS orientation frame provenance diagnostics - in progress (2026-08-08)

- Strain `_batch_data` rows now retain `frame_source_index`, the orientation
  `q_star_candidate`, and the selected orientation q lower/upper bounds from
  the consumed per-frame evidence. The diagnostic table classifies the source
  index and q target for direct frame-by-frame comparison.
- A synthetic regression confirms distinct 2D sector frames produce distinct
  `f_Herman_raw` values; the code does not collapse different sector maps into
  one orientation value. The user's 0%/5% discrepancy still needs a fresh
  rerun with these fields to distinguish frame input duplication from q-window
  selection differences.
- Focused provenance/orientation coverage passes `111`; structured verification
  passes quality `297`, preprocessing `157`, Ruff, compile, and whitespace.

## AI tuning report dialog usability - completed (2026-08-08)

- Long AI-tuning evidence no longer pushes Apply/Keep Current outside the
  viewport. Report content is hosted in a bounded, resizable `QScrollArea`,
  while the action button box remains fixed below it.
- The dialog initial/max height follows the primary screen's available height,
  preserving the existing confirmation and enable/disable behavior.
- Focused dialog coverage passes `14`; structured verification passes quality
  `297` and preprocessing `157`, including Ruff, compile, and whitespace.


## SAXS AI tuning and stability decision repair - completed (2026-08-08)

- The existing AI-tuning button now consumes the SAXS stability report through
  one confirmation-only decision path. Stability evidence includes active and
  excluded dimensions, connected plateau bounds, parameter-perturbation
  intervals, cross-frame continuity, and orientation coverage.
- Candidate application is fail-closed on config identity, exact booleans,
  canonical-mode agreement, physics/quality/continuity guards, rerun evidence,
  rollback, and Undo. No SAXS stability result is applied unattended.
- Only effective consumers enter the stability map. Manual background scale is
  excluded until real background q/I arrays are loaded; an empty detector mask
  cannot activate dilation; invalid numeric baselines cannot create clipped
  out-of-range domains.
- Continuity uses robust local increment support: smooth large or accelerating
  responses pass, while internal, endpoint, and endpoint-sign-reversal jumps
  fail. A plateau trial missing an orientation metric contributes zero to that
  metric's aggregate coverage.
- Fresh cumulative coverage is `257 passed, 7 warnings`; structured verification
  passed quality `297`, preprocessing `156`, Ruff, compile, and whitespace.
  Scientific semantics still require human review before merge. Bayesian
  optimization and background-file loading are separate future work.
- Task card:
  `docs/agent/tasks/2026-08-07-saxs-ai-stability-decision-repair.md`.

## SAXS results frame-row separation - completed (2026-08-07)

- The strain result table now presents one primary row per real analyzed frame;
  its detail and diagnostic sections no longer append flattened orientation
  observations as extra sample rows.
- Detached orientation tracking evidence remains available through the payload
  and serialized batch-summary diagnostics. Scientific analysis and tracking
  behavior did not change.
- TDD reproduced the five-frame `11`-row symptom before the repair. Result-table
  coverage passed `59`, workbench/transport coverage passed `29`, real EDF 8
  replay produced `5/6/6` primary/detail/diagnostic rows, and structured
  verification passed quality `297` plus preprocessing `107`.
- One unrelated broader GUI integration test still shows a history-language
  state defect (`Parameter` versus `歌方`); it remains a separate issue.
- Task card:
  `docs/agent/tasks/2026-08-07-saxs-results-frame-row-separation.md`.

## SAXS strain feature tracking closure - completed (2026-08-06)

- Total-profile q tracking, orientation annulus targeting, directional sector
  diagnostics, GUI rows, figures, and canonical invariant naming now share one
  strain-series result path.
- Core exceptions after seeding cause irreversible tracking loss and retain an
  explicit failed frame result. Unseeded/lost frames fail closed all dependent
  lamellar structure and evidence.
- Focused matrices pass: `131`, `245` (plus 2 skips and 4 existing font
  warnings), and `307`; read-only EDF 8 replay passes `1`. The follow-up
  history/result-table matrix passes `246`.
- Structured verification passed task/memory checks, Ruff, compile, quality
  `297`, preprocessing `107`, and whitespace checks. The cumulative diff was
  reviewed and the implementation is included in the task's local explicit-
  file checkpoint. Scientific semantics still require human review before
  merge.
- Task card:
  `docs/agent/tasks/2026-08-06-saxs-strain-feature-tracking-closure.md`.

## SAXS sparse sector orientation recovery - completed (2026-08-06)

- Real EDF strain frames were producing `strain_canonical_sector_payload_invalid`
  because the 36 x 1000 sector map contains legitimate NaN bins where
  `support_count == 0`.
- Canonical sector validation and anisotropy input validation now accept NaN
  only in zero-support bins; supported non-finite bins remain fail-closed.
  Azimuthal support-weighted extraction avoids `NaN * 0` contamination.
- Real directory reproduction now reaches `analyze_anisotropy` and publishes
  finite raw Herman evidence for 3/4 frames (`f_Herman_raw_mean=0.4729` in the
  local run). Effective Herman remains unavailable when tensile-axis or
  orientation reliability gates are not met; no scientific value is promoted.
- Focused matrix: `109 passed`; structured verifier passed task check, Ruff,
  compile, quality `297`, preprocessing `107`, and whitespace checks.
- Task card: `docs/agent/tasks/2026-08-06-saxs-sparse-sector-orientation.md`.

## SAXS stability map and scientific correctness - implementation complete (2026-08-05)

- The AI tuning SAXS entry point now requests strict seeded stability evidence
  across q/Porod/Guinier windows, background, beam center, mask dilation, and
  azimuthal width. Reports include plateau bounds, bootstrap intervals,
  per-trial frame continuity, physical/quality gates, and a deterministic
  `auto_accept` / `request_confirmation` / `keep_original` decision.
- Stability trials clone the typed `SAXSConfig`; candidate mappings no longer
  fall back to engine defaults. SAXS auto-accept enters the existing
  `PreprocessTransactionService` apply-pending state, reruns asynchronously,
  finalizes through the worker callback, and supports deferred Undo.
- Focused matrix passed `94 passed, 6 warnings`; structured verification passed
  quality `297` and preprocessing `107`. The complete `test_saxs*.py` run
  returned `916 passed, 2 skipped, 14 failed` in 235.91s. The failures are
  concentrated in real-data audit/EDF fixtures and legacy dirty-input tests
  that assert positive-only source channels, which conflicts with the signed
  source contract now under review.
- Human scientific review remains required for calibration/contrast, lamellar
  interpretation, threshold policy, publication promotion, and resolution of
  those fixture/contract expectations.

### Follow-up closure (2026-08-06)

- Sparse sector q bins remain unavailable (`NaN`) without poisoning
  Savitzky-Golay smoothing or dropping an otherwise valid EDF frame.
- A discovered directory with zero surviving frames records `no_valid_frames`,
  marks SAXS validation `ERROR`, and reports a diagnostic result instead of
  defaulting to validation success.
- SAXS stability studies force `request_confirmation`; generic stability
  auto-accept remains available only for explicit non-SAXS policies.
- Missing absolute intensity/contrast calibration is exposed in the scientific
  acceptance audit and gates publication eligibility to SI/diagnostic output;
  raw physical diagnostics remain inspectable.
- Follow-up evidence: `122 passed, 6 warnings`; task quality `297`,
  preprocessing `107`, Ruff, compile, and whitespace all pass. Full SAXS
  re-verification remains open after this follow-up.

## SAXS scientific correctness repair - completed (2026-08-05)

- Final repair implementation is complete under task card
  `docs/agent/tasks/2026-08-04-saxs-scientific-correctness-repair.md`.
- Full SAXS matrix passed `916 passed, 2 skipped, 15 warnings` in `575.81s`;
  warnings are existing EDF geometry and font warnings. Focused repair/closure
  passed `30`; changed-contract matrix passed `177`.
- Final acceptance evidence is recorded in
  `docs/acceptance/2026-08-04-saxs-scientific-correctness-repair.md`.
- Remaining limits are human scientific review of calibration/contrast,
  lamellar interpretation, and publication promotion; Ruland/Vonk remain
  unsupported by design.

## SAXS scientific correctness closure - implementation in progress (2026-08-04)

- Design/task/plan checkpoint: `0f7bf06f`.
- Implemented unit-safe Porod invariant crystallinity (`Q*/(Kp*L)` with
  explicit q/length units), corrected Cooling labels, signed residual
  preservation, positive-only fit masks, total-vs-sector strain routing,
  HDF5/Nexus typed dataset errors, unlimited/configurable batch limits, strict
  geometry/physical figure gates, and diagnostic GUI fields for relative Q-star
  and unavailable void fraction.
- Fresh focused closure coverage is `9 passed`; SAXS/GUI/strain compatibility
  coverage is `159 passed`; quality gate is `297` and preprocessing gate `106`.
- Task verifier is green. Fresh full/boundary verification reached the complete
  pytest stage but timed out after 3600 seconds (`124`) without a summary; it is
  explicitly incomplete. Next action is cumulative diff review and checkpoint.
- Task card: `docs/agent/tasks/2026-08-04-saxs-scientific-correctness-closure.md`.

## SAXS configured q-min semantics - completed (2026-08-04)

- `analyze_single()` now applies finite positive `SAXSConfig.q_min` to external
  1D profiles before smoothing and all downstream metrics, records
  `configured_q_min_applied`, and preserves original input counts in the data
  quality report.
- An auto-detected edge within the retained boundary transition is reconciled
  as configured truncation (`WARN:mask_truncated`); an independently higher edge
  still reports `ERROR:qstar_contaminated`.
- Focused regression passed `3`; compatibility matrix passed `22`. UTF-8 task
  verification passed quality `297` and preprocessing `106` with Ruff,
  compile, type-baseline, and whitespace checks passing.
- Task card: `docs/agent/tasks/2026-08-04-saxs-configured-qmin-semantics.md`.

## SAXS correlation/IDF axis-label regression - completed (2026-08-04)

- Shared and public SAXS publication label normalizers now recognize formatted
  distance labels such as `$r$ (nm)` and IDF labels instead of falling back to
  generic `q`/`I` labels. Raw intensity remains `I(q)` and Kratky remains
  `I(q)q^2`.
- Focused SAXS figure/document/evidence coverage passed (`86 passed`, 4
  pre-existing font warnings). UTF-8 task verification passed with quality
  `297 passed` and preprocessing `106 passed`.
- Task card: `docs/agent/tasks/2026-08-04-saxs-idf-axis-label-regression.md`.

## SAXS gallery clipping and Kratky discoverability - completed (2026-08-04)

- `ChartGallery` now reflows thumbnail rows to one, two, or three columns from
  the available viewport width and repeats the layout on resize. This removes
  the fixed-three-column right-edge clipping that hid the generated Kratky
  card.
- Focused ChartGallery/figure mixin/startup coverage passed (`29 passed`). Task
  card: `docs/agent/tasks/2026-08-04-saxs-gallery-responsive-layout.md`.

## AI tuning entry contrast - completed (2026-08-04)

- The Results-page AI parameter recommendation description now uses the
  existing secondary text token (`#8b92a8`) instead of the low-contrast muted
  token (`#555d7a`) on the dark card. Button availability and tuning behavior
  are unchanged.
- The GUI regression reproduces the old style in RED and passes in GREEN;
  focused Results/AI tuning coverage is `22 passed, 185 deselected`. Task card:
  `docs/agent/tasks/2026-08-04-ai-tuning-entry-contrast.md`.

## SAXS I(q)q^2 and Fourier figure coverage - completed (2026-08-04)

- Added editable complete `I(q)q^2` curves for modern temperature and strain
  series, selected-frame temperature evidence, and legacy static/temperature/
  strain fallback providers. Existing static `lorentz` curve remains intact.
- Figure providers consume emitted `analysis.kratky` arrays where available;
  invalid pairs are omitted and projection quality is retained in recipe
  metadata. Existing Fourier correlation remains `gamma(r)` on the distance
  axis.
- Focused figure coverage passed (`6`, `18`, and `59` tests); task verifier
  passed quality `297` and preprocessing `106`. Task card:
  `docs/agent/tasks/2026-08-04-saxs-iq2-fourier-figures.md`.

## PolyNexus HTML data-flow motion follow-up - ready for checkpoint (2026-08-01)

- Lecture slides now expose a shared `raw input -> decision -> model -> quality
  / output` ribbon. The active stage follows the slide visual role so formula,
  process, comparison, and quality pages read as one software workflow.
- Added staggered lecture entrances, curve drawing, process sweeps, active-stage
  pulses, and a reduced-motion reset. Focused presentation coverage is `3
  passed`; repository verification reports quality `297 passed` and
  preprocessing `106 passed`.
- Fresh Playwright evidence: 46-slide geometry scan at `1280x720` returned
  `issueCount: 0`, phone `390x844` had no overflow, and console messages were
  `0`. The flow ribbon was moved above the bottom navigation safe area after
  screenshot review.

## PolyNexus HTML presentation opening revision - ready for checkpoint (2026-08-01)

- The 46-slide SAXS-led master video now uses uniform five-chapter metadata.
  SAXS slides 17-27 are distinct method pages covering q-region mapping,
  Guinier, Porod, Bragg, Lorentz, IDF, invariant Q, cross-method review, and
  fail-closed quality state.
- The opening seven slides now introduce PolyNexus as a multi-technique
  materials-analysis workbench, show DSC/WAXS/SAXS/IR/NMR scope and the shared
  evidence path, then explain workflow fragmentation, model assumptions,
  review boundaries, and the transition into SAXS.
- Focused presentation coverage is `4 passed`; inline JavaScript parsing,
  `git diff --check`, and `python scripts/verify.py --changed --types` pass.
  The verifier reports quality gate `297 passed` and preprocessing gate
  `106 passed`.
- Fresh Playwright checks passed at `1280x720` and `390x844`: all 46 slides
  passed the viewport-boundary scan, no viewport overflow was detected, and the
  browser console reported zero errors, warnings, or messages.

## Full-goal release evidence refresh - checkpointed (2026-08-01)

- Acceptance ledger now records SAXS 2D context checkpoint `a9e0743`, fresh
  focused `58 passed`, and complete SAXS `700 passed, 6 warnings in 530.15s`,
  exit `0`.
- The 40-minute full/boundary run remains explicitly incomplete (`124`, no
  pytest summary; child manifest `exit_code=3` at timeout/reap). IR mapping,
  NMR solid-C, Joint, restarted-GUI, and owner approval remain conditional.
- Documentation-only checkpoint: `e295ad2` (`docs(release): refresh current
  evidence ledger`).

## SAXS 2D review context projection - checkpointed (2026-08-01)

- Checkpoint `a9e0743` projects existing SAXS 2D detector, geometry/mask,
  beam-center, orientation, gate, and scientific-review evidence into a
  detached JSON-safe Workbench DTO without recalculation or publication
  promotion.
- Independent focused compatibility coverage passed `58` tests; the complete
  SAXS file matrix passed `700 passed, 6 warnings in 530.15s`, exit `0`.
- The task preserves diagnostic/review-required states and does not close the
  separate SAXS scientific or final release gates.

## Historical test-storage name discovery - implementation complete

- The storage classifier now covers the observed `full_boundary`, native
  basetemp, gallery, SAXS matrix, and `Saxs*` legacy test families, with
  protected-name precedence for `测试数据`, archive, review, evidence, and
  baseline paths.
- Focused storage tests passed `39 passed, 1 skipped`; structured verification
  passed quality `297` and preprocessing `106`; task-check, Ruff, compile,
  type-baseline, whitespace, and diff checks passed.
- Reviewed dry-run: `241` artifacts, `56,658,056,745` bytes total,
  `117` eligible artifacts, `26,825,556,265` eligible bytes, `0` removed,
  `0` failures, and `0` protected-name candidates eligible. No `--apply` was
  run in this task. Explicit checkpoint: `a43e70e`.
- Separate authorized follow-up apply removed `98` historical test
  directories. The post-apply inventory has `143` artifacts and `19` remaining
  zero-byte ACL-locked candidates; D: has about `120.15 GB` free. The shared
  SAXS pytest matrix is currently active, so no further apply or ACL changes
  should be attempted until it exits.

## Formal full/boundary verifier - latest tool timeout (2026-07-31)

- A fresh run used `D:\PolyNexus-test-runs-full-goal-20260731-rerun` with
  `review` retention and reached the 40-minute tool bound.
- The wrapper returned exit `124` without a complete pytest summary. This is
  recorded as tool-level incomplete evidence, not pass or product failure.
- The verifier's own child processes were reaped after timeout; the independent
  shared SAXS pytest process was not touched. The formal task remains
  `in_progress`; the four complete canonical slices remain the authoritative
  available test evidence.
- The formal child manifest records `status=failed, exit_code=3` at the reap
  boundary, without a pytest summary; it is therefore still incomplete tool
  evidence rather than a product-test failure. A nested `status=running`
  manifest is from the storage test's mock configuration and has no live PID.

## Results evidence wrap readability - checkpointed (2026-07-31)

- Root cause was isolated in the shared `WrappedEvidenceLabel`: Results applied
  `QSizePolicy.Ignored/Preferred`, which disabled QLabel `heightForWidth` even
  though zero-width break opportunities were present in the rendered text.
- The shared widget now preserves the caller's policy values while restoring
  `heightForWidth=True`; source `text()` remains lossless and no evidence or
  scientific semantics changed.
- TDD RED was `1 failed`; focused GREEN and the Results/Workbench GUI matrix
  passed `52`. Ruff and compile passed. Structured verification passed with
  quality `297`, preprocessing `106`, task/memory/type-baseline/whitespace
  checks, and `git diff --check`.
- Native Windows NMR solid-H/solid-C recheck passed `2 passed, 15 deselected in
  71.69s`, exit code `0`; captures are under
  `D:\PolyNexus_native_restarted_gui_audit_wrap_recheck_20260731`.
- Task/spec/plan/acceptance:
  `docs/agent/tasks/2026-07-31-results-evidence-wrap-readability.md`,
  `docs/superpowers/specs/2026-07-31-results-evidence-wrap-readability-design.md`,
  `docs/superpowers/plans/2026-07-31-results-evidence-wrap-readability.md`,
  and `docs/acceptance/2026-07-31-results-evidence-wrap-readability.md`.
- The explicit six-file allowlist checkpoint is `5f737c2`
  (`fix(gui): preserve evidence label wrapping`); no push was performed. The
  full release remains conditional; IR mapping, NMR solid-C scientific
  assignment, Joint conflict review, and owner publication approval remain
  open.

## Results review explicit-language contract - checkpointed (2026-07-31)

- Results/NMR review summaries now honor their explicit `language` argument
  for assignment, source, axis, vendor-axis, and Xc-gate labels through
  `tr_for_language`; History table regressions explicitly isolate English
  expectations from the persisted GUI language.
- Focused matrix passed `87`; task verifier passed with quality `297` and
  preprocessing `106`, plus Ruff/compile/type/whitespace and diff checks.
- Atomic checkpoint: `6e632ad` (`fix(results): honor explicit review language`).

## Formal pytest temporary-directory collection boundary - wrapper timeout recorded (2026-07-31)

- The full verifier found one failure in the pre-existing untracked
  `tests/_tmp_phase3/test_visual_audit_capture.py`: it searched for an old
  repository-root output path while formal runs use external D: basetemps.
- Root-cause reproduction showed `3251` collected tests including `_tmp_phase3`.
  `pytest.ini` now sets `norecursedirs = _tmp*`; fresh collection returned exit
  `0`, excluded the temporary directory, and collected `3250` canonical tests.
- Task-scoped verifier passed with quality `297` and preprocessing `106`;
  boundary audit returned exit `0`; `git diff --check` passed.
- The single-process full/boundary verifier reached the 30-minute tool bound,
  returned exit `124` without a pytest summary, and is classified only as a
  tool-level timeout. No residual process remained from that attempt.
- Four explicit canonical pytest slices all returned complete summaries and
  exit `0`: `1006 passed, 4 warnings`; `709 passed`; `839 passed, 17 skipped,
  2 warnings`; `679 passed, 1 skipped, 6 warnings`. Combined: `3233 passed,
  18 skipped, 12 warnings`.
- The temporary file and all parallel SAXS/NMR/GUI workspace changes remain
  untouched; the explicit allowlist checkpoint for this boundary task is
  pending this limitation record.

## Current-head full/boundary post-cleanup recheck - tool-level timeout (2026-07-30)

- The current-head command `python scripts/verify.py --changed --types --full
  --boundary` was launched with an isolated `D:\PolyNexus-test-runs-full-current-20260730`
  root and `review` retention. Its pytest child exited, but the tool returned
  no pytest summary, stderr, or wrapper exit code; this is recorded as a
  tool-level timeout/incomplete result and is not a pass. The separate shared
  verifier was excluded.
- Fresh boundary audit returned exit code `0` with no failures. Storage report
  and dry-run clean each returned exit code `0`: `82` artifacts,
  `24,069,383,574` bytes total, `38` emergency-eligible artifacts,
  `14,710,294,260` eligible bytes, and `0` removed. No `--apply` was run.
- Acceptance evidence is in
  `docs/acceptance/2026-07-30-current-head-full-boundary-post-cleanup-recheck.md`.
  Task-scoped verification and the documentation-only allowlist checkpoint
  are complete; the full release and human scientific/restarted-GUI gates
  remain open.

## SAXS temperature method evidence production Figure - checkpointed (2026-07-30)

- Added `saxs.series.temperature.method_evidence` to the production
  temperature Figure provider. It projects only existing Porod, Kratky,
  invariant, and lamellar evidence from `TempSeriesResult.temp_points`, binds
  through unique `source_index`, preserves nullable audit provenance, and
  omits only non-finite pairs from renderer sources.
- The Figure is diagnostic-only and applies only to the temperature axis.
  Existing evolution Main Figure, quality levels, physical gates, rescue, AI,
  publication semantics, and time-axis behavior are unchanged.
- TDD RED was `2 failed, 8 deselected`; focused GREEN was `2 passed, 8
  deselected`; production/evidence/provenance was `48 passed`, and the
  production matrix with portable regression was `66 passed`.
- The latest exact SAXS matrix was `653 passed, 6 warnings` in `541.39s`, exit
  code `0`. Structured verification passed quality `296`, preprocessing `106`,
  Ruff, compile, type baseline, memory/task, and whitespace checks.
- Storage report/clean was dry-run only: `71` artifacts,
  `16,473,416,178` bytes, `eligible_bytes=0`, no emergency pressure, and
  `removed=0`; no `test_storage.py --apply` was run.
- Task/spec/plan/acceptance:
  `docs/agent/tasks/2026-07-30-saxs-temperature-method-evidence-production-figure.md`,
  `docs/superpowers/specs/2026-07-30-saxs-temperature-method-evidence-production-figure-design.md`,
  `docs/superpowers/plans/2026-07-30-saxs-temperature-method-evidence-production-figure.md`,
  and `docs/acceptance/2026-07-30-saxs-temperature-method-evidence-production-figure.md`.
- The explicit seven-file allowlist checkpoint is `929da91`; no push or merge
  was performed. Parallel GUI/NMR files, scratch, and test-storage
  directories were not included.

## SAXS temperature method evidence diagnostic Figure - checkpointed (2026-07-30)

- Added `saxs.series.temperature.method_evidence` to the portable temperature
  Figure provider. It projects only existing per-frame Porod, Kratky,
  invariant, and lamellar `MetricEvidence` into detached nullable audit sources
  plus finite renderer sources. The Figure is always diagnostic; it does not
  recalculate, interpolate, reclassify, or change quality/physical/publication
  gates.
- TDD RED was `1 failed, 1 passed, 16 deselected`; focused GREEN was `2
  passed, 16 deselected`; the complete temperature Figure provider passed `18`.
  Structured verification passed quality `296`, preprocessing `106`, Ruff,
  compile, type baseline, memory/task, and whitespace. The exact SAXS matrix
  passed `651 passed, 6 warnings` in `602.27s`, exit code `0`.
- Storage report/clean was dry-run only: `71` artifacts,
  `16,289,827,301` bytes total, `eligible_bytes=0`, no emergency pressure, and
  `removed=0`; two paths were protected by a running process and no apply was
  run.
- Task/spec/plan/acceptance:
  `docs/agent/tasks/2026-07-30-saxs-temperature-method-evidence-diagnostic-figure.md`,
  `docs/superpowers/specs/2026-07-30-saxs-temperature-method-evidence-diagnostic-figure-design.md`,
  `docs/superpowers/plans/2026-07-30-saxs-temperature-method-evidence-diagnostic-figure.md`,
  and `docs/acceptance/2026-07-30-saxs-temperature-method-evidence-diagnostic-figure.md`.
- The explicit allowlist checkpoint is `b994a91`; full/boundary release and
  human scientific / restarted-GUI review remain open.

## SAXS temperature Guinier diagnostic Figure - checkpointed (2026-07-30)

- Added `saxs.series.temperature.guinier` to the temperature Figure provider.
  The all-frame audit source preserves nullable `Rg_nm`, temperature, existing
  source index, frame level, and reason codes; a separate finite-pair source
  feeds the line renderer so V2 remains data-linked without interpolation.
- The definition is always `diagnostic`, records
  `missing_values_preserved=true` and `interpolation=false`, and consumes only
  existing `TempSeriesResult` evidence. Legacy results without `Rg_array` keep
  the previous figure set.
- TDD RED reproduced the missing definition (`StopIteration`); focused GREEN
  passed `6` selected tests and the full temperature provider passed `16`.
  Structured verification passed with quality `294`, preprocessing `106`,
  Ruff, compile, type baseline, memory/task, and whitespace checks. The fresh
  exact SAXS matrix passed `649 passed, 6 warnings in 543.62s`, exit code `0`.
- Storage `report --json` found `62` artifacts, `15,806,654,463` bytes total,
  `eligible_bytes=0`, and no emergency pressure. `clean --older-than-hours 24`
  was dry-run only; no directory was removed or migrated and no
  `test_storage.py --apply` was run.
- Task/spec/plan/acceptance:
  `docs/agent/tasks/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md`,
  `docs/superpowers/specs/2026-07-30-saxs-temperature-guinier-diagnostic-figure-design.md`,
  `docs/superpowers/plans/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md`,
  and `docs/acceptance/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md`.
- The explicit allowlist checkpoint is `ffc4a56`; full/boundary release and
  human scientific / restarted-GUI review remain open.

## SAXS GUI mask editor confirmed rerun - checkpointed (2026-07-30)

- Added a detached configured detector-mask baseline to static SAXS
  preprocessing and transported it through `SAXSEngine.result.raw_data`.
  The GUI exposes a fail-closed editor only for a single static 2D result;
  mask, unmask, reset, cancel, and explicit confirm are supported.
- Confirmed candidates reuse the existing digest/shape validation and are
  forwarded through one normal `AnalysisWorker`/`SAXSEngine` static rerun.
  Temperature, strain, directory, 1D, AI, automatic rescue, new thresholds,
  and publication semantics remain outside this task.
- Fresh focused GREEN passed `5` tests in `0.59s`. Structured verification
  passed with quality `292`, preprocessing `106`, Ruff, compile, type baseline,
  memory/task, and whitespace checks. The current exact SAXS matrix passed
  `647 passed, 6 warnings in 552.67s`, exit code `0`.
- Storage `report --json` found `57` artifacts, `15,802,080,308` bytes total,
  `eligible_bytes=0`, and no emergency pressure. The subsequent
  `clean --older-than-hours 24` was dry-run only: `removed=0`; no
  `test_storage.py --apply` was run and no directory was deleted or migrated.
- Task/spec/plan/acceptance:
  `docs/agent/tasks/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md`,
  `docs/superpowers/specs/2026-07-30-saxs-gui-mask-editor-confirmed-rerun-design.md`,
  `docs/superpowers/plans/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md`,
  and `docs/acceptance/2026-07-30-saxs-gui-mask-editor-confirmed-rerun.md`.
- Status: implementation, automated verification, and the explicit allowlist
  checkpoint are complete. Full/boundary release and human
  scientific / restarted-GUI review remain open.

## SAXS confirmed mask engine rerun (2026-07-30)

- The existing confirmed detector-mask candidate now travels through
  `SAXSEngine.run_pipeline()` and `AnalysisWorker` only for a single static 2D
  rerun. The transient state is restored in `finally`; 1D, directory,
  temperature/strain, and plot-only routes do not apply it. Existing
  preprocessing validation and detector/quality/physical/publication gates
  remain authoritative.
- Focused boundary coverage is `6 passed`; task verification passed with
  quality `292` and preprocessing `106`, plus Ruff/compile/type/memory/task/
  whitespace checks. The full current SAXS matrix passed `642 passed, 6
  warnings` in `559.53s` with exit code `0`.
- Storage `report --json` found `54` artifacts and `eligible_bytes=0` with no
  emergency pressure. `clean --older-than-hours 24` was dry-run only; no
  directory was removed or migrated. The first matrix command timed out at
  the 120-second tool limit without a summary; a longer independent retry is
  the authoritative evidence.
- Task/spec/plan/acceptance:
  `docs/agent/tasks/2026-07-30-saxs-engine-confirmed-mask-rerun.md`,
  `docs/superpowers/specs/2026-07-30-saxs-engine-confirmed-mask-rerun-design.md`,
  `docs/superpowers/plans/2026-07-30-saxs-engine-confirmed-mask-rerun.md`, and
  `docs/acceptance/2026-07-30-saxs-engine-confirmed-mask-rerun.md`.
- Status: implementation and automated verification complete; the explicit
  allowlist checkpoint is the commit created for this task. Full/boundary
  release and human scientific / restarted-GUI review remain open.

## SAXS manual mask confirmed rerun - checkpointed 2026-07-30

- Added a strict, detached JSON candidate contract for explicit 2D detector
  mask edits. Candidates carry shape-bound base/edited digests and explicit
  pixel operations; only confirmed candidates affect preprocessing.
- Pending, malformed, and unconfirmed candidates remain numerical no-ops while
  their status is preserved in existing detector mask provenance. Confirmed
  masks propagate through full, sector, and azimuthal integration without
  mutating the raw image or changing quality/physical/publication authority.
- Fresh exact SAXS evidence is `636 passed, 6 warnings` in `540.67s`, exit `0`.
  Task verification and diff checks passed. Storage report/dry-run found `54`
  artifacts, `0` eligible bytes, and removed `0`; no storage apply was run.
- The explicit allowlist checkpoint is committed locally; no push or merge was
  performed. Full / boundary release verification is not claimed by this
  slice.

## Current HEAD native non-SAXS walkthrough - verified, checkpoint pending - 2026-07-30

- Windows Qt native walkthrough passed `14 passed, 3 deselected in 353.49s`,
  exit `0`, covering DSC standard/isothermal/non-isothermal, WAXS
  static/temperature/strain, IR standard/temperature-2D/synthetic mapping,
  NMR liquid-H/liquid-C/solid-H/solid-C, and synthetic Joint.
- The run generated `56` PNG captures under
  `D:\PolyNexus_native_all_routes_current_nonsaxs_20260730`, four surfaces
  per selected route, including real Editor Export fallback checks.
- Visual inspection confirms IR mapping remains `Review required`, NMR
  solid-C remains `review_missing`, and the shared surfaces are populated.
  The synthetic Joint fixture displays an accepted review record alongside
  2 errors and 2 warnings; this is fixture provenance only and does not close
  Joint conflict interpretation or release approval.
- No SAXS route, production code, real dataset, or existing workspace change
  was modified. Evidence: `docs/agent/tasks/2026-07-30-current-head-native-nonsaxs-walkthrough.md`
  and `docs/acceptance/2026-07-30-current-head-native-nonsaxs-walkthrough.md`.

## Current DSC/WAXS focused lifecycle recheck - 2026-07-30

- Current-head DSC provider/lifecycle/Workbench/export/editor matrix passed
  `97 passed in 28.01s`, exit `0`, using
  `D:\PolyNexus-test-runs-current-dsc-20260730`.
- Current-head WAXS lifecycle/provider/Workbench/project/History matrix passed
  `21 passed in 46.36s`, exit `0`, using
  `D:\PolyNexus-test-runs-current-waxs-20260730`.
- Both runs excluded SAXS and changed no source or real dataset. They strengthen
  automated lifecycle evidence only; GUI visual/scientific review and final
  release authorization remain separate gates.

## Release decision packet - conditional scientific disposition recorded - 2026-07-30

- The project owner confirmed the conservative non-SAXS release boundaries in
  `docs/agent/tasks/2026-07-29-release-decision-packet.md`.
- IR uses the documented official Thermo/OMNIC Picta coordinate profile, but
  remains diagnostic-only because the supplied inputs have no native 2D map,
  sample ROI, or detector calibration payload.
- NMR solid-C remains `assignment_limited`; ambiguous peaks stay unassigned and
  Xc cannot be promoted without a source-linked assignment truth set and a
  confirmed ppm calibration.
- Joint grants no automatic scientific priority to a technique; operational
  `ERROR`/`WARN` classification remains fail-closed and unresolved conflicts
  stay diagnostic-only.
- The recorded non-SAXS release decision is `conditional`. Restarted-GUI
  all-mode review, source-specific evidence, and the separate SAXS release
  decision remain open. No source code, real dataset, or SAXS worktree was
  changed in this documentation checkpoint.

- The scientific confirmation and NMR readiness cards are now synchronized to
  their existing evidence: the confirmation card is completed, and NMR
  solid-C readiness is checkpointed at `fddb8c5`. These status changes record
  existing implementation evidence only; no SAXS code, source dataset, or
  scientific promotion was changed.

## SAXS post-cleanup release re-audit - domain green, full release open - 2026-07-30

- With the updated test-storage rules and explicit apply authorization, the
  cleanup removed eligible historical pytest/SAXS matrix artifacts. The first
  apply inventory had `127` artifacts and `116946589183` emergency-eligible
  bytes; it returned `11` Windows `PermissionError [WinError 5]` failures.
  A fresh report then showed `45` artifacts, `1091805727` total bytes, and
  `0` eligible bytes. No source files or real datasets were targeted.
- The fresh full verifier first hit the outer tool timeout after `604` seconds
  with no pytest summary. A background rerun completed its all-tests phase with
  `1 failed, 3184 passed, 18 skipped, 12 warnings in 2609.69s`, wrapper exit
  code `1`. The only failure was the pre-existing untracked GUI scratch test
  `tests/_tmp_phase3/test_visual_audit_capture.py::test_capture_real_result_gui_routes`,
  which found no `PolyNexusPolyNexus.pytest_tmp_release_real_dsc` output
  directory. The wrapper therefore did not run its boundary phase; this is
  not a full/boundary pass and no unrelated scratch file was changed.
- The current HEAD SAXS matrix independently passed `631` tests with `6`
  warnings in `588.82s`, exit code `0`, across the `99` repository
  `tests/test_saxs_*.py` files. The standalone read-only boundary audit also
  returned exit code `0`. After this matrix, storage reported `54` artifacts,
  `15802078628` total bytes, and `0` eligible bytes; D: had about `94.27 GB`
  free at the audit.
- SAXS production behavior was not changed in this re-audit. Remaining gates
  are the unrelated full-suite scratch-test failure, restarted-GUI review,
  real-detector calibration/mask/orientation review, scientific meaning review,
  and final release/publication authorization.


## Current HEAD non-SAXS recheck - verified, human gates remain open - 2026-07-30

- The current checkout was re-run without SAXS source/test selection:
  DSC/WAXS `118 passed in 63.02s`, IR `55 passed in 55.38s`, and NMR/Joint
  `70 passed in 561.47s`; all three exited `0`.
- Windows Qt native NMR route acceptance passed `4 passed, 13 deselected in
  137.74s`, exit `0`. The current run produced Results, Gallery, History, and
  Editor captures under
  `D:\PolyNexus-test-runs-current-native\pytest\run-20260730T105557316506Z-51536\test_native_windows_gui_real_r3\native_gui_captures`.
  The capture shows `Review required | reason=review_missing` for solid-C;
  it is route evidence, not scientific approval.
- Boundary audit emitted the current inventory with exit `0`; `git diff
  --check` exited `0`. This strengthens automated non-SAXS evidence only.
  SAXS, real data, and the pre-existing `current-state.md` modification were
  not changed.
- Evidence: `docs/agent/tasks/2026-07-30-current-head-nonsaxs-recheck.md` and
  `docs/acceptance/2026-07-30-current-head-nonsaxs-recheck.md`.

## NMR solid-C readiness projection - verified, checkpointed at fddb8c5 - 2026-07-30

- Existing `Xc_assignment_status` is now projected into JSON-safe
  `assignment_readiness` with `supported`, `assignment_limited`, and
  `missing_assignment` states. Non-solid-13C inputs are `not_applicable`.
  The same object is available under assignment and structure evidence.
- Results review now presents assignment readiness plus existing ppm-axis
  `source`, `units`, and `calibrated` fields. No peak assignment, Xc formula,
  JEOL conversion, or figure-promotion rule changed.
- Focused evidence passed `13`; Results review NMR passed `1`; changed-file
  Ruff passed. NMR engine passed `19` in `112.93s`; figure provider passed `6`,
  figure document passed `5`,
  and solid-C lifecycle passed `1 selected, 3 deselected` in `148.24s`, exit
  code `0`.
- The combined engine/figure/document/lifecycle command reached an outer
  tool timeout; the full lifecycle shard returned tool exit `124` without a
  pytest summary. This remains a tool-level timeout, not a full-suite pass.
  Task verifier passed with quality `292` and preprocessing `106`; boundary
  audit, Ruff, compile, memory/task, whitespace, and diff checks also exited
  `0`. The explicit checkpoint is `fddb8c5`.
- Evidence: `docs/agent/tasks/2026-07-30-nmr-solid-c-readiness.md`,
  `docs/acceptance/2026-07-30-nmr-solid-c-readiness.md`, and
  `docs/superpowers/plans/2026-07-30-nmr-solid-c-readiness.md`.

## Joint conclusion policy - verified, checkpoint ready - 2026-07-30

- Joint reports now expose a fail-closed `joint_conclusion` classification at
  report level and inside `ai_context`. It uses only existing review status
  and existing WARN/ERROR severity: missing/invalid is `review_required`, an
  ERROR is `blocked`, a WARN is `conditional`, and an accepted review with no
  issue is `accepted`.
- Reviewer-owned `conflict_precedence`, `minimum_evidence`, and
  `unresolved_conflict_policy` strings are copied exactly as provenance; the
  classifier does not interpret or invent scientific precedence. Existing
  formulas, thresholds, evidence weights, promotion snapshots, and figure
  roles are unchanged.
- Focused classification tests passed `6` selected tests; the broader
  Joint/NMR provenance/figure/lifecycle matrix passed `24`, both exit `0`.
  Task verifier passed with quality `291` and preprocessing `106`; boundary
  audit, Ruff, compile, type baseline, memory/task, whitespace, and diff
  checks exited `0`. The explicit allowlist checkpoint is this task's commit.
- This advances the software boundary only. IR sample mapping metadata, NMR
  peak assignments, scientific Joint conflict interpretation, and final human
  release approval remain open. SAXS remains out of scope.
- Evidence: `docs/agent/tasks/2026-07-30-joint-conclusion-policy.md` and
  `docs/acceptance/2026-07-30-joint-conclusion-policy.md`.

## Project release decision provenance - verified, checkpoint ready - 2026-07-30

- The non-SAXS Results Workbench now records an append-only, batch-scoped
  release decision using `ScientificReviewRecord(scope="release")`. The
  latest detached snapshot is hydrated into current Results, History, and
  Export contexts; absent records remain `release_missing` and saving does not
  alter numeric analysis values, Figure roles, or scientific conclusions.
- Fresh focused verification passed `61` tests in `1.53s`, exit 0. The task
  verifier passed with quality `291` and preprocessing `106`; task/memory,
  Ruff, compile, type baseline, whitespace, and boundary audit checks exited
  0. `git diff --check` also exited 0.
- This closes the software/provenance slice only. IR vendor mapping, NMR
  solid-C assignments, Joint conflict precedence, and reviewer-owned final
  `approve/conditional/reject` approval remain open scientific gates. SAXS,
  real datasets, and the pre-existing `current-state.md` modification remain
  outside this checkpoint.
- Evidence: `docs/agent/tasks/2026-07-30-project-release-decision.md` and
  `docs/acceptance/2026-07-30-project-release-decision.md`.

- Scientific review canonical source matching completed on 2026-07-30 for
  non-SAXS Workbench saves. When nested evidence and the current input path
  produce multiple refs, the saved decision snapshot now binds to the first
  canonical source ref instead of leaving `source_ref` empty. TDD RED was
  `1 failed`; GREEN and the Workbench/core matrix passed (`30 passed`).
  Task-scoped verification passed with quality `290` and preprocessing `106`,
  and the native IR route passed (`1 passed, 16 deselected`). SAXS remains out
  of scope.

- Scientific review source-reference hydration completed on 2026-07-30 for
  non-SAXS Results Workbench routes. Nested `analysis_evidence` identifiers
  such as IR mapping `source_id` now remain visible to the reviewer dialog;
  existing metadata/current-file refs remain preserved. Focused Workbench
  tests pass (`29 passed`), native IR mapping route passes (`1 passed, 16
  deselected`), and task-scoped verification passes with quality `290` and
  preprocessing `106`. Native dialog capture is at
  `D:\PolyNexus_review_entry_native_20260730\scientific_review_dialog.png`.
  The explicit allowlist checkpoint is this task's commit. SAXS remains out of
  scope.

## Scientific Review Workbench entry - verified, checkpoint ready - 2026-07-30

- Results Workbench now exposes a generic Scientific Review dialog for IR
  mapping, NMR solid-C, and Joint. The dialog uses the core public schema,
  validates `ScientificReviewRecord`, and saves one source-linked record to the
  selected analysis run through a transactional SampleDB update.
- Existing History presentation sees the same review snapshot. Saving does
  not republish figures or promote roles; scientific conclusions remain
  reviewer-owned and fail-closed.
- Focused non-SAXS review/IR/NMR/Joint matrix passed `62` tests in `33.01s`;
  `git diff --check` passed. Task verification passed with quality `290`,
  preprocessing `106`, Ruff, compile, memory, task, and whitespace checks;
  no phased type baseline target was selected. The explicit allowlist
  checkpoint is ready.
- Task, design, plan, and acceptance:
  `docs/agent/tasks/2026-07-30-scientific-review-workbench-entry.md`,
  `docs/superpowers/specs/2026-07-30-scientific-review-workbench-entry-design.md`,
  `docs/superpowers/plans/2026-07-30-scientific-review-workbench-entry.md`,
  and `docs/acceptance/2026-07-30-scientific-review-workbench-entry.md`.

## Current non-SAXS module recheck - verified - 2026-07-30

- The current checkout was re-run in D:-isolated recursive pytest shards with
  all SAXS test files excluded: DSC/WAXS `124 passed in 82.05s`, IR `55
  passed in 46.51s`, and NMR/Joint `65 passed in 412.97s`; each exited `0`.
- The corresponding acceptance evidence is in
  `docs/acceptance/2026-07-29-full-goal-requirements-audit.md` (checkpoint
  `7be0385`). This is module regression evidence, not final scientific or
  release approval.
- IR native mapping data, NMR assignment truth, source-matched reviewer
  records, all-mode human visual approval, and final release authorization
  remain open. SAXS was not executed or modified in this recheck.

## Joint AI boundary through GUI/history fallback - verified and checkpointed - 2026-07-30

- The legacy `joint_ai_context()` adapter now preserves the same JSON-safe
  `ai_boundary` as the current Joint report when it reconstructs clean or
  conflicted context from `rows` and `validations`. This keeps the AI-off,
  not-configured, rule-based fallback and source-evidence preservation policy
  visible through Workbench, History, and Export compatibility paths.
- TDD RED was `2 failed, 2 passed, 114 deselected` with the expected missing
  key. GREEN fallback tests passed `4`; the History/Export/Joint consumer and
  lifecycle matrix passed `143` in `20.97s`, both exit code `0`.
- No provider, prompt, formula, threshold, evidence weight, issue severity,
  or scientific promotion rule changed. Task-scoped verification passed with
  quality `290`, preprocessing `106`, task/memory, Ruff, compile, type
  baseline, and whitespace checks; exit code `0`. The explicit seven-file
  checkpoint is `c179c25` (local only; no push). IR/NMR/Joint scientific
  decisions and final release authorization remain human gates.
- Evidence: `docs/acceptance/2026-07-30-joint-ai-context-fallback-provenance.md`.

## Joint deterministic AI boundary - verified and checkpointed - 2026-07-30

- Joint `ai_context` now declares `mode=off`, `provider_status=not_configured`,
  `fallback=rule_based_report`, and the failure policy
  `preserve_source_evidence_and_diagnostic_status` on both clean and
  conflicted report branches.
- The change is status/provenance only. It does not call a provider, build a
  prompt, alter formulas or thresholds, change evidence weights, or promote a
  WARN/ERROR into an accepted conclusion.
- TDD RED was `2 failed` with the expected missing-key error. With
  `POLYNEXUS_TEST_RETENTION=review`, the focused Joint dataset/real lifecycle
  matrix passed `9` tests in `17.12s`, exit code `0`. An ephemeral rerun's
  SQLite cleanup hit `WinError 32` after `2 passed` bodies and is recorded as
  a tool-level failure rather than evidence of success.
- Task-scoped verification passed with quality `290`, preprocessing `106`,
  Ruff, compile, type baseline, memory/task, and whitespace checks; exit code
  `0`. The broader Joint conflict/lifecycle/provenance matrix passed `27`
  tests in `28.92s`. The explicit allowlist checkpoint is the only commit
  action for this slice; no push or merge is performed. Scientific Joint
  conflict interpretation and final release approval remain human gates.
- Evidence: `docs/acceptance/2026-07-30-joint-ai-boundary.md`.

## NMR JEOL axis provenance - verified and checkpointed - 2026-07-30

- Real JEOL solid 13C files now expose raw `SCANS`, `X_OFFSET`, `X_SWEEP`, and
  related record fields through the observed 64-byte layout.
- Frequency-like vendor values are not treated as ppm. The reader retains the
  safe default `240.0..-20.0` axis and records
  `jeol_metadata_units_unconfirmed`, `ppm_axis_calibrated=false`.
- The NMR run-level evidence projection and
  `AnalysisEvidence.feature_evidence.axis_evidence` carry the source, reason,
  units, calibration status, and range.
- TDD RED reproduced the missing raw field (`SCANS is None`); focused GREEN
  passed `2`, the full NMR engine suite passed `19`, and the real four-partition
  lifecycle passed `4`.
- No Xc, assignment, Joint, or review promotion rule changed. The explicit
  allowlist checkpoint is `0792518`; no real test data was modified.
- A current-checkout rerun of the engine and four-partition lifecycle was
  attempted with D:-isolated basetemps, but the tool window returned `124`
  without a pytest summary while child processes were still active. The
  processes later exited; this attempt is classified as tool-level timeout and
  is not counted as new pass/fail evidence. The checkpointed results above
  remain the authoritative evidence because no scoped NMR files changed after
  `0792518`.
- Evidence: `docs/acceptance/2026-07-30-nmr-jeol-axis-provenance.md`.

## IR Thermo/OMNIC mapping semantics - verified, checkpointed - 2026-07-30

- The IR mapping contract now publishes the official Thermo Scientific OMNIC
  Picta semantics profile: X is the column/stage-X axis, Y is the row/stage-Y
  axis, units are `um`, origin is stage home `(0, 0)`, and area-map ROI bounds
  may expand to fit the vendor step-size grid.
- The profile is explicitly marked `official_rule_sample_metadata_unverified`;
  native map absence leaves sample ROI bounds, detector calibration, and
  flattened scan order unknown. No vendor reader or scientific review
  promotion rule was added.
- Focused mapping/lifecycle tests passed (`18 passed`). Task verification
  passed with quality `290` and preprocessing `106`; storage reporting was
  read-only (`55` artifacts, `eligible_bytes=0`, no removal).
- Full IR regression passed (`55 passed in 41.70s`). The explicit allowlist
  checkpoint was created with no push performed.
- Evidence: `docs/acceptance/2026-07-30-ir-thermo-mapping-semantics.md`.

## SAXS series metric source-index integrity - verified, checkpointed - 2026-07-30

- `build_series_metric_evidence()` now validates supplied frame source indices
  without coercing invalid values into trusted mappings. Duplicate, negative,
  non-integral, boolean, non-finite, non-coercible, and length-mismatched
  mappings expose position facts, clear trusted indices, add reason codes, and
  cap usable metric summaries at `Diagnostic`. Valid reordered mappings remain
  Trend evidence and record `source_index_order_reordered=True`; omitted
  mappings are unchanged.
- No metric value, condition-axis rule, physical threshold, interpolation,
  rescue, AI, Figure role, Manifest, or Export decision changed.
- TDD RED was `8 failed, 2 warnings`; the non-finite boundary RED was `1
  failed, 6 passed, 4 deselected, 2 warnings`; focused GREEN was `21 passed,
  1 warning`. The consumer matrix passed `110 passed, 1 warning`.
- Fresh SAXS passed `605 passed, 8 warnings in 424.90s`, exit code `0`.
- Task verifier passed task-card, memory, Ruff, compile, and type baseline, but
  its focused quality gate returned `288 passed, 2 failed, 3 warnings`, exit
  code `1`, from pre-existing `tests/test_history_table_service.py` locale
  expectations (`Scientific review` vs current `科学复核`).
- `git diff --check` passed. Storage stayed dry-run only: `54` artifacts,
  `eligible_bytes=13390550`, `eligible=6`, `removed=0`; no `--apply`.
- Task/spec/plan/acceptance are recorded in the corresponding
  `2026-07-30-saxs-series-metric-source-index-integrity` files. The explicit
  allowlist checkpoint is `fb9fb42`; no push or merge was performed.
  `current-state.md` and parallel files remain untouched.

## SAXS series metric evidence Figure/Manifest/Export projection - verified, checkpointed - 2026-07-30

- The existing Figure metric allowlist now carries the source-index integrity
  fields `duplicate_source_index_indices`, `invalid_source_index_indices`, and
  `source_index_order_reordered`. The change is transport-only and keeps the
  existing detached JSON-safe projection; Export remains on its unchanged
  quality DTO path.
- TDD RED was `2 failed, 1 passed, 2 warnings`; focused GREEN was `47 passed,
  1 warning`; the Figure/Manifest/Export and related consumer matrix was `71
  passed, 1 warning`.
- Fresh SAXS matrix passed `608 passed, 8 warnings in 394.32s`, exit code `0`.
- Task verifier passed task-card, memory, Ruff, and compile checks. Its quality
  gate was `288 passed, 2 failed, 3 warnings`, exit code `1`, from the existing
  history locale assertions (`Scientific review` vs current `科学复核`).
- Storage report/clean remained dry-run only: `56` artifacts, `6` eligible,
  `eligible_bytes=13390550`, `removed=0`; no `test_storage.py --apply` ran.
- Task/spec/plan/acceptance are recorded in the corresponding
  `2026-07-30-saxs-series-metric-evidence-projection` files. Explicit
  allowlist checkpoint was created with no push; the final local commit hash is
  reported in the handoff. `current-state.md`, IR mapping changes, and all
  parallel scratch files remain untouched.

## Current-head SAXS verification recheck - SAXS matrix green, full boundary open - 2026-07-30

- Fresh current-head SAXS matrix using repository Python 3.14, offscreen Qt,
  and a writable workspace basetemp returned `594 passed, 8 warnings in
  524.50s`, exit code `0`. The warnings are existing locale, Arial glyph, EDF
  geometry-header, and pytest cache-permission warnings.
- The first fresh full/boundary attempt passed focused quality `290` and
  preprocessing `106`, then crashed around 27% with Windows access violation
  `0xC0000005` in `PySide6\\Qt6Widgets.dll`; it exited `1` without a final
  pytest summary or boundary result. An isolated ChartEditor probe passed
  `57` tests, and a later offscreen full attempt was tool-aborted with no
  final result. Neither is counted as a full/boundary pass.
- A first SAXS attempt with an external basetemp outside the writable
  workspace returned `514 passed, 80 errors` from setup `PermissionError
  [WinError 5]`; this is recorded as an environment limitation, not a
  production failure.
- Latest storage dry-run remains non-destructive: `54` artifacts,
  `eligible_bytes=13390550`, `eligible=6`, `removed=0`; no
  `test_storage.py --apply` was run.
- The task-scoped verifier completed task-card, memory, Ruff, compile, and
  type-baseline checks. Its focused quality gate returned `288 passed, 2
  failed, 3 warnings` and exit code `1`; both failures are pre-existing locale
  expectation mismatches in `tests/test_history_table_service.py` where tests
  expect English `Scientific review` but the current locale emits `科学复核`.
  The standard invocation also hit runner PATH and external-basetemp permission
  limitations; a process-local executable PATH and workspace test root reached
  the actual focused tests. This does not change the green SAXS matrix result.
- Task/acceptance/plan:
  `docs/agent/tasks/2026-07-30-current-head-saxs-verification-recheck.md`,
  `docs/acceptance/2026-07-30-current-head-saxs-verification-recheck.md`, and
  `docs/superpowers/plans/2026-07-30-current-head-saxs-verification-recheck.md`.
- Remaining gates are native Qt full-suite stability, restarted-GUI visual
  review, reviewer-owned scientific decisions, and final release approval.

## SAXS representative selection dirty-profile projection - checkpointed - 2026-07-30

- `figure_selection._intensity_features()` now projects q and intensity tokens
  elementwise through the existing numeric coercion boundary. Valid finite
  pairs continue through the existing aligned-prefix, area, maximum, sorting,
  and transition-feature logic; malformed tokens no longer erase the whole
  frame's selection features.
- No selection limits, condition ordering, manual override, frame index,
  quality, physical, publication, AI, or rescue semantics changed.
- TDD RED was `1 failed`; focused GREEN passed `9`. The fresh SAXS matrix passed
  `594` tests with `6` existing warnings and exit code `0`.
- Structured verification passed with quality `290` and preprocessing `106`;
  task/memory, Ruff, compile, type baseline, whitespace, and `git diff --check`
  also passed. Storage remained dry-run only (`54` artifacts,
  `eligible_bytes=0`, `0` eligible clean bytes, `0` cleanup failures, `0`
  removed); `test_storage.py --apply` was not run.
- Task/acceptance/spec/plan:
  `docs/agent/tasks/2026-07-30-saxs-representative-selection-dirty-profile.md`,
  `docs/acceptance/2026-07-30-saxs-representative-selection-dirty-profile.md`,
  `docs/superpowers/specs/2026-07-30-saxs-representative-selection-dirty-profile-design.md`,
  and `docs/superpowers/plans/2026-07-30-saxs-representative-selection-dirty-profile.md`.
- The prior full/boundary attempt after `765bda3` remains a timeout without a
  final summary and is not attributed to this task.
- The explicit allowlist implementation checkpoint is `b5cbc92`; no push or
  merge was performed.

## SAXS 2D Figure malformed-token projection - checkpointed - 2026-07-30

- Shared detector Figure projection and strain detector/azimuthal projections
  now use the existing elementwise numeric coercion boundary. A malformed
  pixel, chi, or intensity token becomes an explicit non-finite projection
  entry; existing finite filtering retains all other pixels/pairs and keeps
  their coordinates/order.
- No raw analysis, anisotropy/orientation, quality level, physical metric,
  publication role, AI/rescue, interpolation, sorting, or frame semantics
  changed.
- TDD RED was `3 failed, 5 passed, 33 deselected`; focused GREEN passed `41`.
  The fresh SAXS matrix passed `593` tests with `6` existing warnings and exit
  code `0`.
- Structured verification passed with quality `290` and preprocessing `106`;
  task/memory, Ruff, compile, type baseline, whitespace, and `git diff --check`
  also passed. Storage remained dry-run only (`54` artifacts,
  `eligible_bytes=0`, `0` eligible clean bytes, `0` cleanup failures, `0`
  removed); `test_storage.py --apply` was not run.
- Task/acceptance/spec/plan:
  `docs/agent/tasks/2026-07-30-saxs-2d-figure-dirty-token-projection.md`,
  `docs/acceptance/2026-07-30-saxs-2d-figure-dirty-token-projection.md`,
  `docs/superpowers/specs/2026-07-30-saxs-2d-figure-dirty-token-projection-design.md`,
  and `docs/superpowers/plans/2026-07-30-saxs-2d-figure-dirty-token-projection.md`.
- The latest post-`765bda3` full/boundary attempt remains a `1504.1s` timeout
  without a final summary and is not attributed to this task.
- The explicit allowlist implementation checkpoint is `d480ac3`; no push or
  merge was performed.

## SAXS modern temperature Figure derived-array dirty-input guard - verified, checkpointed - 2026-07-30

- `_series_values()` now projects `L_array`, `lc_array`,
  `lc_effective_array`, `Q_star_array`, and `Xc_array` elementwise through
  the existing numeric coercion boundary. Malformed or non-finite tokens stay
  at their frame positions as explicit `NaN`; existing required/optional and
  length-mismatch behavior remains unchanged.
- TDD RED was `1 failed, 13 deselected`; focused GREEN passed `1`, the related
  Figure/provider/evidence matrix passed `51`, and the exact SAXS matrix passed
  `590` with `6` existing warnings and exit code `0`.
- Structured verification passed with quality `290` and preprocessing `106`;
  Ruff, compile, type baseline, memory, whitespace, and `git diff --check`
  passed. Storage report/clean remained dry-run only (`54` artifacts,
  `6` eligible, `0` removed); `test_storage.py --apply` was not run.
- The explicit allowlist implementation checkpoint is `bb0048c`; no push or
  merge was performed.
- Task/acceptance/spec/plan:
  `docs/agent/tasks/2026-07-30-saxs-modern-temperature-figure-derived-arrays-dirty-input.md`,
  `docs/acceptance/2026-07-30-saxs-modern-temperature-figure-derived-arrays-dirty-input.md`,
  `docs/superpowers/specs/2026-07-30-saxs-modern-temperature-figure-derived-arrays-dirty-input-design.md`,
  and `docs/superpowers/plans/2026-07-30-saxs-modern-temperature-figure-derived-arrays-dirty-input.md`.
- A fresh full/boundary pass is not attributed to this task; the latest
  post-`765bda3` full/boundary attempt is recorded as timeout `124`.

## SAXS modern temperature Figure axis dirty-input guard - verified, checkpointed - 2026-07-29

- Modern temperature Figure construction now projects each temperature token
  independently through the existing numeric coercion boundary. A malformed
  value remains at its original frame position as an explicit missing
  condition; the frame is displayed as `Frame N`, while the recipe records
  `None`. The same projected axis is reused by per-frame, waterfall,
  parameter, and heatmap definitions.
- No q/I sanitization, quality level, physical threshold, publication role,
  AI/rescue behavior, interpolation, sorting, deletion, or frame inference
  changed.
- TDD RED was `1 failed, 12 deselected`; focused GREEN passed `1`, the related
  Figure/provider/evidence matrix passed `50`, and the exact SAXS matrix passed
  `589` with `6` existing warnings and exit code `0`.
- Structured verification passed with quality `290` and preprocessing `106`;
  Ruff, compile, type baseline, memory, whitespace, and `git diff --check`
  passed. Storage report/clean remained dry-run only (`54` artifacts,
  `6` eligible, `0` removed); `test_storage.py --apply` was not run.
- Task/acceptance/spec/plan:
  `docs/agent/tasks/2026-07-29-saxs-modern-temperature-figure-axis-dirty-input.md`,
  `docs/acceptance/2026-07-29-saxs-modern-temperature-figure-axis-dirty-input.md`,
  `docs/superpowers/specs/2026-07-29-saxs-modern-temperature-figure-axis-dirty-input-design.md`,
  and `docs/superpowers/plans/2026-07-29-saxs-modern-temperature-figure-axis-dirty-input.md`.
- An explicit allowlist checkpoint is created after this evidence. Existing
  `current-state.md`, GUI/editor drafts, scratch, and test-storage paths are
  intentionally outside the checkpoint.

## Fresh current-HEAD full/boundary recheck - automated gates green, human gates open - 2026-07-29

- After checkpoint `863b8fb`, the fresh
  `python scripts/verify.py --changed --types --full --boundary` rerun with
  external D: basetemp and the pre-existing untracked
  `tests/_tmp_phase3/test_visual_audit_capture.py` explicitly excluded
  returned `3100 passed, 18 skipped, 12 warnings in 2280.40s`, wrapper exit
  `0`, quality `290`, preprocessing `106`, and boundary audit exit `0`.
- The default collection was also run and returned one failure in that
  pre-existing scratch test because its historical capture directory was
  absent. It is recorded as a scratch limitation, not a production failure
  and not silently counted as a pass.
- This closes the current automated full/boundary gate only. Restarted-GUI
  visual review, real detector geometry/orientation meaning, IR vendor/ROI
  semantics, NMR solid-C assignment, Joint conflict interpretation, and final
  scientific/release approval remain open. No `test_storage.py --apply` or
  data cleanup was performed.
- Evidence: `docs/agent/tasks/2026-07-30-full-boundary-latest-evidence.md` and
  `docs/acceptance/2026-07-30-full-boundary-latest-evidence.md`.

## Post-`765bda3` full/boundary recheck - timeout, not a pass - 2026-07-30

- A fresh `python scripts/verify.py --changed --types --full --boundary` was
  run with `tests/_tmp_phase3/test_visual_audit_capture.py` explicitly
  excluded and an external D: basetemp.
- The tool timed out after `1504.1s` with exit code `124` and no final pytest,
  quality, preprocessing, or boundary summary. The exact child process tree
  was reaped afterward; the GUI Python process was not touched.
- The earlier `3100 passed, 18 skipped, 12 warnings` current-HEAD evidence is
  not attributed to `765bda3`. Focused/related SAXS and exact SAXS evidence for
  `765bda3` remains valid; a fresh complete full/boundary pass is still open.

## Full native visual reacceptance - automated acceptance complete, human gates open - 2026-07-30

- Fresh current-checkout native Windows Qt selector returned `17 passed, 15
  warnings in 443.92s (0:07:23)`, explicit exit code `0`.
- Coverage was DSC standard/isothermal/non-isothermal; SAXS
  static/temperature/strain; WAXS static/temperature/strain; IR
  standard/temperature-2D; NMR liquid-H/liquid-C/solid-H/solid-C; synthetic
  Joint; and synthetic IR mapping. Every selected route reached Results,
  Gallery, History, Editor, and the no-Origin PackageExporter fallback.
- Representative captures were inspected under
  `D:\PolyNexus_full_native_visual_reacceptance_20260730_rerun`. The
  assetless SAXS strain `generation_failed` diagnostic remains visible but is
  skipped for initial Editor selection; IR mapping reports
  `Review required | reason=review_missing`; NMR solid-C peak labels are dense;
  synthetic Joint shows two errors and two warnings.
- This is route/display evidence only. IR vendor semantics, NMR solid-C
  assignment/Xc policy, Joint conflict policy, and final release authorization
  remain human gates. Evidence: `docs/agent/tasks/2026-07-30-full-native-visual-reacceptance.md`
  and `docs/acceptance/2026-07-30-full-native-visual-reacceptance.md`.

## Scientific Review native route recheck - verified, scientific gates open - 2026-07-30

- Fresh current-checkout native Windows Qt selector passed `3 passed, 14
  deselected in 35.98s`, exit code `0`, covering NMR solid-C, synthetic Joint,
  and synthetic IR mapping.
- Results, Gallery, History, Editor, and PackageExporter fallback remained
  constructible. Captures are under
  `D:\PolyNexus_native_recheck_current_20260730`.
- This recheck is route/display evidence only and does not approve IR vendor
  semantics, NMR assignment/Xc policy, Joint conflict interpretation, or final
  release authorization.
- Evidence: `docs/agent/tasks/2026-07-30-scientific-review-native-reacceptance.md`
  and `docs/acceptance/2026-07-30-scientific-review-native-reacceptance.md`.

## SAXS 2D reviewer consumer propagation - verified, checkpointed - 2026-07-30

- The configured detached `saxs.2d` review projection now reaches result
  parameters and authoritative `quality_evidence.json`; Figure document and
  V2 sidecar carry the same snapshot. Empty optional review config remains
  absent from generic non-gated result consumers, while attached Figure
  evidence stays explicitly fail-closed with `review_missing`.
- Focused GREEN passed `4`; adjacent 2D/1D/Figure/bundle/Workbench matrix
  passed `70`, while the independent broader consumer recheck passed `160`.
  Exact SAXS passed `588` with `6` warnings, exit code `0` in this session
  (`591.42s`) and the independent shared recheck (`594.35s`).
- Storage report/clean dry-run recorded `46` artifacts, `0` eligible bytes,
  and `0` removed; no `--apply` was run for this task.
- Task-scoped verifier passed quality `290` and preprocessing `106`, plus
  Ruff, compile, memory, type baseline, and whitespace checks.
- Task/acceptance/plan:
  `docs/agent/tasks/2026-07-29-saxs-2d-review-consumer-propagation.md`,
  `docs/acceptance/2026-07-29-saxs-2d-review-consumer-propagation.md`, and
  `docs/superpowers/plans/2026-07-29-saxs-2d-review-consumer-propagation.md`.
- An explicit allowlist checkpoint is recorded in the task commit.

## User-authorized test-storage cleanup - partially applied - 2026-07-30

- Ran `python scripts/test_storage.py clean --older-than-hours 24 --apply`
  only after confirming no pytest command-line process was active.
- Six old C: legacy test roots were removed successfully, releasing about
  `13.94 GB`. The apply command returned exit code `1` because six old
  zero-byte D:\PolyNexus legacy directories returned `WinError 5` access
  denied. No ACL bypass or broad manual deletion was attempted.
- Post-apply report: `41` artifacts remain, `35` are protected, and `0`
  eligible bytes remain; the six remaining eligible paths are zero-byte
  directories. C: reports `182.27 GB` free and D: reports `125.60 GB` free.
- Evidence: `docs/agent/tasks/2026-07-30-test-storage-apply-attempt.md` and
  `docs/acceptance/2026-07-30-test-storage-apply-attempt.md`.

## Current full-verifier regression repair - verified, checkpointed - 2026-07-30

- Repaired four current-HEAD regressions without changing scientific policy:
  the IR review snapshot expectation now includes the JSON-safe empty
  `policy_version`, the two SAXS Results Workbench expectations include the
  intentional non-applicable review suffix, and the real SAXS strain lifecycle
  chooses a `ready` figure for Editor persistence while retaining visible
  error-status diagnostic entries.
- Focused regressions passed: IR mapping `13 passed`, affected MainWindow
  tests `2 passed`, and SAXS strain lifecycle `1 passed, 12 deselected`.
- Task-scoped verification passed with quality `290`, preprocessing `106`,
  Ruff, compile, type baseline, memory, task, and whitespace checks.
- Full pytest summary with the pre-existing untracked scratch test excluded:
  `3091 passed, 18 skipped, 12 warnings in 1986.68s (0:33:06)`. The launcher
  did not persist its wrapper exit code; this is recorded as a pytest summary,
  not as an observed exit-code claim.
- Task card and acceptance note:
  `docs/agent/tasks/2026-07-30-full-verifier-regressions.md` and
  `docs/acceptance/2026-07-30-full-verifier-regressions.md`.
- The unrelated `current-state.md`, scratch/test directories, and external
  test-storage artifacts remain intentionally untouched.

## SAXS 2D reviewer evidence binding - verified, checkpointed - 2026-07-30

- The shared SAXS Figure evidence attachment now applies the existing
  reviewer record against the correct boundary: ordinary Figures expect
  `saxs.1d`, while existing detector/2D/orientation Figure recipes expect
  `saxs.2d`. The projection remains detached and strict-JSON-safe.
- Source matching still uses only emitted `source_path`,
  `data_quality_report.raw_data_ref`, and `data_quality_report.source_id`.
  Missing, malformed, pending, wrong-scope, and partial-source records remain
  fail-closed. No detector/orientation value, quality gate, role, AI/rescue,
  Workbench, Manifest, or Export behavior changed.
- TDD RED was `2 failed, 7 passed`; GREEN was `38 passed in 8.96s`. The
  adjacent detector/2D/static/strain matrix passed `55 passed, 2 warnings in
  24.83s`.
- Fresh task-scoped verification exited `0` with quality `290`, preprocessing
  `106`, Ruff, compile, type baseline, memory/task, and whitespace checks
  passing. Fresh exact SAXS exited `0`: `584 passed, 6 warnings in 421.73s`.
- Storage report/clean remained dry-run: `45` artifacts, `0` eligible bytes,
  `0` removed. No `test_storage.py --apply` was run.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-30-saxs-2d-review-evidence-binding.md`,
  `docs/superpowers/specs/2026-07-30-saxs-2d-review-evidence-binding-design.md`,
  and `docs/superpowers/plans/2026-07-30-saxs-2d-review-evidence-binding.md`.
- An explicit changed-file allowlist checkpoint is recorded in this task
  commit.

## SAXS 1D reviewer evidence binding for static and strain - verified, checkpointed - 2026-07-29

- Static and strain Figure providers now pass the existing configured
  `saxs.1d` reviewer payload through `configured_saxs_1d_review()` into the
  shared detached evidence projection. The generic provider path consumes the
  review only for static/strain modes; temperature keeps its specialized path
  and 2D is not changed.
- No analysis, quality level, physical gate, AI/rescue, publication role,
  Workbench, Manifest, Export, source ordering, interpolation, frame repair,
  or source inference behavior changed. Missing, invalid, pending,
  wrong-scope, and partial-source records remain fail-closed.
- TDD RED was `2 failed, 5 passed`; GREEN was `7 passed`. The focused matrix
  passed `60 passed in 7.30s`.
- Fresh task-scoped verification exited `0` with quality `290`, preprocessing
  `106`, Ruff, compile, type baseline, memory/task, whitespace, and diff
  checks passing. Fresh exact SAXS exited `0`: `582 passed, 6 warnings in
  392.47s`.
- Storage report/clean remained dry-run: `45` artifacts, `0` eligible bytes,
  `0` removed. No `test_storage.py --apply` was run; old shared full/boundary
  processes and all unrelated scratch/test paths remain untouched.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-29-saxs-1d-review-static-strain-binding.md`,
  `docs/superpowers/specs/2026-07-29-saxs-1d-review-static-strain-binding-design.md`,
  and `docs/superpowers/plans/2026-07-29-saxs-1d-review-static-strain-binding.md`.
- An explicit changed-file allowlist checkpoint is recorded in this task
  commit.


## SAXS 1D reviewer evidence binding - checkpointed - 2026-07-29

- Temperature SAXS Figure evidence now consumes only an explicit
  `SAXSConfig.scientific_review` payload for the reviewer-owned `saxs.1d`
  scope. It matches every existing frame using `source_path`,
  `raw_data_ref`, or `source_id` and emits detached fail-closed reasons; it
  does not change analysis, quality levels, physical gates, AI/rescue, or
  publication roles.
- TDD RED was `5 failed`; focused GREEN was `5 passed`, evidence/audit
  regression was `38 passed`, and the broader review/temperature/Workbench
  matrix was `82 passed`.
- Fresh exact SAXS matrix passed `580 tests` with `6` known warnings in
  `561.51s`; task verifier passed quality `290`, preprocessing `106`, Ruff,
  compile, type baseline, memory/task, and whitespace checks.
- Storage report/clean remained dry-run: `41` artifacts, `0` eligible bytes,
  `0` removed. The unrelated shared full/boundary process was not used as
  evidence and remains outside this task.
- Task card: `docs/agent/tasks/2026-07-29-saxs-1d-review-evidence-binding.md`.
  Static/strain/2D reviewer binding and human scientific sign-off remain
  separate follow-up boundaries.

## Release packet evidence recheck - awaiting human decision - 2026-07-30

- Current-checkout Joint real-data plus synthetic lifecycle recheck passed
  `2 passed in 26.08s`; cross-technique AI-off/failure/fallback recheck passed
  `25 passed in 0.42s`, both with exit code `0` and external D: basetemps.
- A live Qt capture showed Results, manifest-only Plots/Gallery, and History;
  the OS screenshot helper returned wallpaper, so this remains supplementary
  visual evidence rather than a complete restarted-GUI release pass.
- The release packet was refreshed without changing scientific review records,
  publication roles, or final release status. IR mapping, NMR solid-C, Joint
  conflict policy, and final authorization remain reviewer-owned.

## Scientific review policy provenance - checkpointed - 2026-07-30

- `review_decision_snapshot()` now preserves the existing record's exact
  `policy_version`; the shared GUI adapter displays it as `policy=...` when
  available. No promotion rule, scientific result, or publication role changed.
- Focused Results/History/Export consumer matrix passed `61` tests.
- Task: `docs/agent/tasks/2026-07-30-scientific-review-policy-provenance.md`.
  Acceptance: `docs/acceptance/2026-07-30-scientific-review-policy-provenance.md`.
- Task-scoped verification passed with quality `290`, preprocessing `106`,
  Ruff, compile, type-baseline, memory/task, whitespace, and diff checks green;
  explicit checkpoint is pending while preserving pre-existing SAXS scope edits.
- Scientific values, restarted-GUI human review, and final release approval
  remain open.

## SAXS scientific review scopes - checkpointed - 2026-07-29

- User selected the two independent reviewer-owned scopes. The design, task
  card, acceptance note, and implementation plan are recorded in
  `docs/superpowers/specs/2026-07-29-saxs-scientific-review-scopes-design.md`,
  `docs/agent/tasks/2026-07-29-saxs-scientific-review-scopes.md`, and
  `docs/superpowers/plans/2026-07-29-saxs-scientific-review-scopes.md`.
- `ScientificReviewRecord` now recognizes `saxs.1d` and `saxs.2d` with only
  reviewer-owned required-key validation. No SAXS engine, quality gate,
  publication role, GUI, AI, or rescue behavior consumes these scopes yet.
- TDD RED was `5 failed, 10 passed`; GREEN is `15 passed in 0.13s`.
- Task-scoped verifier exited `0` with quality `290`, preprocessing `106`,
  Ruff, compile, memory/task checks, and whitespace green. Exact SAXS matrix
  exited `0`: `575 passed, 6 warnings in 518.52s`; `git diff --check` exited
  `0`.
- Storage report/clean remained dry-run: `40` artifacts, `0` eligible bytes,
  `6` eligible zero-byte legacy entries, `34` younger-than-retention entries,
  and `0` removed. `test_storage.py --apply` was not run.
- The explicit SAXS allowlist was selectively staged because same-file
  policy/provenance edits remain in the worktree; existing `current-state.md`,
  GUI changes, and test-storage/scratch paths remain outside this task.

## Scientific Review native reacceptance - checkpointed - 2026-07-30

- After `e7209ee`, a fresh exact selector passed all three current native
  Windows routes: `3 passed, 14 deselected in 31.78s`, exit code `0`.
  NMR solid-C, synthetic Joint, and synthetic IR mapping each produced
  Results/Gallery/History/Editor captures and PackageExporter fallback output.
- The new Scientific Review status is visible in current Results captures:
  gated missing records show `review_missing`; the accepted Joint fixture is
  explicitly fixture-only and does not close conflict interpretation.
- Capture root:
  `D:\PolyNexus_scientific_review_native_reacceptance_20260730`. Scientific
  semantics, restarted-GUI all-mode human review, and final release approval
  remain open.
- Task: `docs/agent/tasks/2026-07-30-scientific-review-native-reacceptance.md`.

## Scientific review visibility - checkpointed - 2026-07-29

- The existing fail-closed scientific-review decision snapshot is now rendered
  through one GUI adapter in Results Workbench, History, and Export. Accepted,
  pending/missing, conditional, rejected, stale, invalid, and blocked reasons
  retain audit fields; missing review is required only for IR mapping, NMR
  solid-C, and Joint.
- Focused presentation/history/export/results tests passed `46`; the Qt
  Results Workbench + History/export regression slice passed `28` with `216`
  deselected. No scientific promotion rule or analysis output changed.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-29-scientific-review-visibility.md`,
  `docs/superpowers/specs/2026-07-29-scientific-review-visibility-design.md`,
  `docs/superpowers/plans/2026-07-29-scientific-review-visibility.md`.
- Checkpoint: `56c2693`.


## Shared scientific review record contract - verified, checkpoint pending - 2026-07-29

- The approved scientific-release design now has an implementation plan and a
  separate schema task for a technique-neutral, JSON-safe review record.
- The first slice is intentionally shared-only: `ScientificReviewRecord`
  validates scope/status/source references, serializes JSON-safe detached
  payloads, and exposes a fail-closed promotion decision without choosing IR,
  NMR solid-C, Joint, or final release values.
- TDD RED was the expected missing-module collection error; GREEN was `7
  passed` in `tests/test_scientific_review.py`.
- Plan: `docs/superpowers/plans/2026-07-29-scientific-review-record-contract.md`.
  Task: `docs/agent/tasks/2026-07-29-scientific-review-record-contract.md`.


## Scientific release confirmation boundaries - design recorded - 2026-07-29

- User approved the high-level confirmation-table approach. The design records
  reviewer-owned IR coordinate/ROI semantics, NMR solid-C assignment/Xc policy,
  Joint conflict precedence, and final release authorization without inventing
  values.
- Conservative behavior is retained when the record is absent, malformed,
  stale, or source-mismatched: diagnostic/assignment-limited/conditional roles
  remain unchanged and AI/fallback paths cannot bypass review.
- Design: `docs/superpowers/specs/2026-07-29-scientific-release-confirmation-boundaries-design.md`.
  Task: `docs/agent/tasks/2026-07-29-scientific-release-confirmation-boundaries.md`.
- Next action is reviewer entry of scientific values; implementation must then
  be split into value-specific task cards with focused regression and lifecycle
  verification.

## Scientific review promotion gates - bounded verification complete - 2026-07-29

- Shared JSON-safe review restoration/snapshots now gate the three remaining
  scientific promotion boundaries. IR mapping preserves supplied coordinates,
  explicit ROIs, and invalid masks; accepted source-matching review promotes
  map Main and ROI SI, while the default is diagnostic-only. NMR solid-C
  carries review state through result evidence and recipes; Joint requires an
  accepted source-matching record for every selected batch row and persists the
  aggregate decision in report/recipe provenance.
- Focused IR/shared/NMR/Joint matrix passed `46`; real NMR solid-C lifecycle
  passed `1 selected, 3 deselected` and asserted `review_missing` with no Main
  entry. Task-scoped verification passed with quality `287` and preprocessing
  `106`; boundary-only verification and boundary audit passed.
- The requested full/boundary verifier reached the 364-second tool limit with
  exit `124` and no complete pytest summary; it is explicitly not treated as a
  pass. Human IR/NMR/Joint scientific records, all-mode visual/restarted-GUI
  review, AI-off/failure/fallback release gates, and final release approval
  remain open. Evidence:
  `docs/acceptance/2026-07-29-scientific-review-promotion-gates.md`.

## Release decision packet - unlocked GUI slice rechecked - 2026-07-29

- The prior locked-desktop observation is superseded for this review: the
  canonical `D:\PolyNexus` GUI was live and responsive in the user's already
  unlocked session.
- Real GUI inspection covered DSC Results/Result Review, Plots, and History.
  Plots showed the manifest-only gallery's empty state plus explicit
  historical recovery; History showed the populated records table and
  Restore/Rerun/Confirm/Compare actions.
- This closes only the observed GUI shell/workbench slice. IR vendor
  coordinate/ROI semantics, NMR solid-C assignment/Xc policy, Joint conflict
  precedence, all-mode human visual review, and final release authorization
  remain open. Evidence: `docs/acceptance/2026-07-29-release-decision-packet.md`.

## SAXS partial detector V2 binding - verified, checkpointed - 2026-07-29

- Static and temperature diagnostic detector Figures now opt into their
  existing reviewed V2 adapters.  Their sparse source rows still contain only
  retained finite pixels; the reactive scene and V2 publication leave missing
  pixels absent/blank.  Detector values, projection counts, quality/physical
  gates, orientation, AI/rescue, and publication role did not change.
- TDD RED was `2 failed, 7 deselected` at the expected `not_configured`
  capability.  GREEN was `2 passed, 7 deselected`; detector/reactive matrix
  passed `17`.  Structured verification passed with quality `287` and
  preprocessing `106`; fresh SAXS matrix passed `567` with 6 existing
  warnings in 416.22s, exit code 0.
- Storage report/clean stayed dry-run: 18 artifacts, 0 eligible bytes, and 0
  removed.  The one literal wildcard SAXS command was a PowerShell expansion
  error and did not run tests; the recorded 567-pass matrix used an explicit
  PowerShell file enumeration.  Evidence:
  `docs/agent/tasks/2026-07-29-saxs-partial-detector-v2-binding.md`.

## User-authorized test-storage apply follow-up - partial cleanup - 2026-07-29

- The explicit `python scripts/test_storage.py clean --older-than-hours 24
  --apply` command removed two eligible C-drive legacy directories (`15,746`
  bytes). It returned exit code `1` because six eligible repository-local
  legacy directories were denied by Windows ACLs; no ACL bypass or manual
  broad deletion was performed.
- The post-apply report shows `16` discovered artifacts and `0` eligible
  bytes. Ten external/managed entries remain protected by retention; the six
  ACL-denied D-drive entries are zero-byte legacy directories and remain
  present for a later authorized maintenance attempt.

## SAXS partial detector FigurePipeline rendering - verified, checkpointed - 2026-07-29

- Static and temperature diagnostic detector heatmaps now opt into a narrowly
  scoped partial-grid renderer path. Missing coordinate cells stay NaN/masked
  and render blank; duplicate cells, empty data, and ordinary heatmaps retain
  their existing strict errors. No detector values, frames, analysis, quality
  levels, physical gates, orientation, publication role, AI, or rescue behavior
  changed.
- TDD RED was renderer 1 failed, 1 passed and pipeline 2 failed, with the
  expected incomplete-grid error. GREEN focused Figure/Manifest/Export matrix
  passed 68; structured verification passed with quality 287 and
  preprocessing 106. Fresh exact SAXS matrix passed 565 with 6 existing
  warnings in 332.26s, exit code 0.
- Storage report and clean were dry-run only: 16 artifacts, 15,746 eligible
  bytes, 0 removed. test_storage.py --apply was not run.
- Evidence: docs/agent/tasks/2026-07-29-saxs-partial-detector-heatmap.md.
  Checkpoint: `2a6933b`. Existing current-state and unrelated
  scratch/untracked files remain untouched.

## SAXS static/temperature detector Figure projection - verified, checkpointed - 2026-07-29

- Static and temperature Figure providers now expose a diagnostic-only 2D
  detector Figure when existing supported source paths yield finite sampled
  pixels. A shared read-only projection records sampled/retained/non-finite
  counts and `complete`/`partial_nonfinite` status; unreadable, malformed, or
  all-invalid images remain omitted. No analysis, geometry/orientation,
  quality, physical, publication, AI, or rescue semantics changed.
- TDD RED was `2 failed, 2 passed`; the focused Figure/2D/publication matrix
  passed `81`; structured verification passed with quality `287` and
  preprocessing `106`; the fresh exact SAXS matrix passed `563` with `6`
  existing warnings. Storage report/clean remained dry-run with 14 legacy
  artifacts, 15,746 eligible bytes, and 0 removed. The explicit allowlist
  checkpoint is created by the task commit; its hash is reported in the
  handoff.
- Evidence: `docs/agent/tasks/2026-07-29-saxs-static-temperature-detector-figure.md`.


## SAXS strain 1D Figure projection provenance - checkpointed - 2026-07-29

- Strain evolution and ordinary/diagnostic sequence 1D Figure recipes now
  expose detached frame-indexed q/I projection counts with strict-JSON-safe
  `complete` or `partial_invalid` status; scientific analysis, heatmap, 2D,
  orientation, phase, and publication behavior are unchanged.
- Focused recheck passed `2 passed, 20 deselected`; the task verifier passed
  with quality `287` and preprocessing `106`.
- Checkpoint: `d9f4d6e`. Evidence:
  `docs/agent/tasks/2026-07-29-saxs-strain-1d-figure-provenance.md`.

## User-authorized test-storage apply - partial cleanup - 2026-07-30

- The exact `python scripts/test_storage.py clean --older-than-hours 24
  --apply` command ran after the process check. It removed 23 safe managed
  entries (`499046` bytes) and returned exit code `1` because five eligible
  repository-local legacy directories were denied by Windows ACLs.
- Eight C-drive legacy directories remain protected because they are younger
  than the 24-hour retention window; no ACL bypass, migration, or broad manual
  deletion was performed. The post-apply report shows `278` artifacts and
  `0` currently eligible bytes under the current retention/process state.

## Test-storage apply fail-soft - checkpointed - 2026-07-29

- `scripts/test_storage.py` now exposes an immutable detailed apply result,
  continues independent eligible deletions after an `OSError`, reports each
  failure path/type/message, and returns CLI exit code `1` for partial apply.
  The existing `apply_cleanup(...) -> list[Path]` compatibility wrapper and
  all safety gates are unchanged.
- TDD RED covered the missing detailed operation and the old CLI's false-zero
  partial apply; GREEN was `2` focused tests and the full storage suite was
  `28 passed, 1 skipped`. The task verifier passed quality `287` and
  preprocessing `106`; storage report/clean dry-run remained non-mutating.
- Checkpoint: `d314feb`. Evidence:
  `docs/agent/tasks/2026-07-29-test-storage-apply-fail-soft.md`.
- The earlier user-authorized real cleanup remains a separate maintenance
  action; ACL-denied directories are still preserved and no ACL bypass was
  added.

## SAXS temperature 1D Figure projection provenance - checkpointed - 2026-07-29

- Temperature representative-profile and waterfall Figure recipes now expose
  detached, frame-indexed aligned/retained/non-finite/non-positive-intensity
  q/I pair counts with `complete` or `partial_invalid` status. Existing
  temperature sequence, heatmap interpolation, Figure roles, and fail-closed
  behavior are unchanged.
- TDD RED was `2 failed, 4 deselected`; focused GREEN was `2 passed, 4
  deselected`; the temperature panel/provider slice passed `15` tests. The
  task verifier passed with quality `287` and preprocessing `106`. The fresh
  neutral-basetemp SAXS matrix passed `549` tests with `6` warnings and exit
  code `0`. A basetemp containing `temperature_1` exposed an existing
  condition-path regex collision; no IO change was made in this task.
- Checkpoint: `e0c167d`. Evidence:
  `docs/agent/tasks/2026-07-29-saxs-temperature-1d-figure-provenance.md`.
- Separate user-authorized storage maintenance removed 35 eligible D-drive
  legacy directories (`19,128,640,281` bytes); C-drive directories younger
  than 24 hours and permission-denied zero-byte entries remain protected.

## SAXS azimuthal Figure projection provenance - checkpointed - 2026-07-29

- The strain azimuthal Figure recipe now records detached per-frame aligned,
  retained, and non-finite chi/I pair counts with `complete` or
  `partial_nonfinite` status. Existing finite-pair projection, empty/all-
  invalid omission, orientation analysis, and publication gates are unchanged.
- TDD RED was recorded for the missing recipe field; the focused Figure/
  detector/orientation/publication matrix passed `59` tests. The structured
  verifier passed with quality `287` and preprocessing `106`. An independent
  current-thread full SAXS recheck returned `545 passed, 6 warnings in
  344.71s`, exit code `0`.
- Checkpoint: `5b7a412`. Evidence:
  `docs/agent/tasks/2026-07-29-saxs-azimuthal-figure-provenance.md`.

## Aggressive pytest test-storage lifecycle - checkpointed - 2026-07-29

- Managed pytest runs now carry retention-profile/run-state metadata, owned
  ephemeral cleanup and interruption reconciliation; the janitor reports
  profile/reason/byte summaries and protects evidence, invalid manifests,
  active, tracked, protected, symlinked, and outside-root paths.
- Storage regression passed `26 passed, 1 skipped`; the structured verifier
  passed with quality `287` and preprocessing `106`. The real legacy report
  and clean commands were dry-run only; no migration or deletion was run in
  this task. Checkpoints: `f685908`, `6d7290c`, `6ed7700`, `a305d37`, and
  `9080aa7`.

## SAXS detector Figure dirty projection - checkpointed - 2026-07-29

- The strain Figure detector projection now retains finite sampled pixels from
  mixed finite/non-finite 2D images, preserves their sampled coordinates, and
  records sampled/retained/non-finite pixel counts in Figure recipe
  provenance. All-invalid and malformed detector inputs remain unavailable;
  analysis, orientation, quality, and publication gates are unchanged.
- TDD RED was `1 failed, 13 deselected`; the focused Figure/detector matrix
  passed `55` tests. The structured verifier passed with quality `287` and
  preprocessing `106`. The fresh SAXS matrix returned `541 passed, 6
  warnings in 358.32s`, exit code `0`.
- Checkpoints: `bf9674f` (finite detector projection) and `e929982`
  (projection provenance). Evidence: `docs/agent/tasks/2026-07-29-saxs-detector-figure-dirty-projection.md`
  and `docs/agent/tasks/2026-07-29-saxs-detector-figure-provenance.md`.

## SAXS 1D Figure dirty projection - checkpointed - 2026-07-29

- A shared detached `_coerce_numeric_array()` now represents malformed tokens
  as position-preserving `NaN` and is used by static, temperature, strain, and
  legacy 1D q/I or derived-trace Figure paths. Existing finite/positive,
  minimum-point, sorting, overlap, fail-closed, quality, physical, AI/rescue,
  and publication semantics remain unchanged.
- TDD RED was `3 failed, 21 deselected` for q/I paths and `2 failed, 15
  deselected` for derived traces after restoring their old conversions. GREEN
  was `7 passed, 22 deselected`; related provider files returned `29 passed`.
  Structured verification passed with quality `287` and preprocessing `106`;
  exact SAXS returned `540 passed, 6 warnings in 315.38s`, exit code `0`.
  Storage report/clean remained dry-run with `302` artifacts, `40` eligible,
  `262` protected, and `0` removed. The explicit allowlist implementation
  checkpoint is `957e6ce`; no push or merge was performed.
- Evidence: `docs/agent/tasks/2026-07-29-saxs-figure-1d-dirty-projection.md`
  and `docs/acceptance/2026-07-29-saxs-figure-1d-dirty-projection.md`.

## Release decision packet - awaiting human input - 2026-07-29

- The remaining release gates are now explicit in
  `docs/agent/tasks/2026-07-29-release-decision-packet.md`: unlocked-GUI
  visual review, IR vendor coordinate/ROI semantics, NMR solid-C assignment
  policy, Joint conflict interpretation, and final release authorization.
- Automated evidence remains separate from these decisions. The product keeps
  unresolved IR/NMR/Joint outputs diagnostic or assignment-limited; no semantic
  promotion was made. The current desktop still exposes `LockApp`, so the
  packet awaits an unlocked session and responsible reviewer input.

## SAXS static Figure dirty projection - checkpointed - 2026-07-29

- The static Figure provider now converts q/intensity tokens elementwise at
  `_numeric_pairs`; invalid elements remain explicit as `NaN` in a detached
  projection and existing finite/positive/minimum checks decide whether a
  profile is emitted. No interpolation, padding, inference, analysis change,
  quality-level change, physical-threshold change, AI/rescue change, or
  publication-role change was made.
- TDD RED was `1 failed, 2 deselected`; GREEN was `2 passed, 1 deselected`,
  and the complete static panel file returned `3 passed`. Structured
  verification passed with quality `287` and preprocessing `106`; the exact
  SAXS matrix returned `535 passed, 6 warnings in 340.57s`, exit code `0`.
  Storage report/clean remained dry-run with `292` artifacts, `40` eligible,
  `252` protected, and `0` removed. The explicit allowlist checkpoint hash is
  reported in the handoff.
- Evidence: `docs/agent/tasks/2026-07-29-saxs-static-figure-dirty-projection.md`
  and `docs/acceptance/2026-07-29-saxs-static-figure-dirty-projection.md`.

## User-authorized test-storage apply - partial cleanup - 2026-07-30

- After all pytest processes ended, `python scripts/test_storage.py clean
  --older-than-hours 24 --apply` was executed on the user's explicit request.
  It partially removed eligible artifacts but stopped with exit code `1` and
  `WinError 5` at
  `D:\PolyNexus\PolyNexusPolyNexus.pytest_tmp_metric_position_full`.
- Post-apply dry-run reports `277` artifacts, `40` eligible,
  `19128640281` eligible bytes, and `237` protected; C: has `8` artifacts and
  `0` eligible. No ACL bypass or manual broad deletion was performed.
- Evidence: `docs/agent/tasks/2026-07-30-test-storage-apply-attempt.md` and
  `docs/acceptance/2026-07-30-test-storage-apply-attempt.md`.

## SAXS export fallback dirty-provenance - checkpointed - 2026-07-29

- Legacy analysis fallback profile export now has a RED regression: dirty q/raw
  values previously produced empty cells without provenance counts. The new
  task will merge elementwise conversion counts into a detached diagnostics map
  and expose `WARN` only for an otherwise `OK`/unknown fallback profile.
- TDD RED reproduced `1 failed, 12 deselected`; focused GREEN returned `2
  passed, 11 deselected`, and the export/processed-profile consumer matrix
  returned `18 passed`. Structured verification passed with quality `287` and
  preprocessing `106`; exact SAXS returned `533 passed, 6 warnings` in
  `295.48s`, exit code `0`. Storage dry-run reported `282` artifacts, `40`
  eligible, `242` protected, and `0` removed. The explicit checkpoint was
  created; its final commit hash is reported in the handoff.
  Evidence: `docs/agent/tasks/2026-07-29-saxs-export-fallback-dirty-provenance.md`.

## SAXS export dirty-profile guard - checkpointed - 2026-07-29

- The canonical `ProcessedProfile` now remains exportable when parallel q/I
  lists contain malformed tokens: bundle profile export prefers canonical q and
  uses the existing elementwise coercion fallback for CSV layers. Invalid
  positions remain empty cells and profile `WARN`/diagnostics stay in
  `provenance.json`; no analysis or publication semantics changed.
- TDD RED reproduced `1 failed, 11 deselected`; focused GREEN returned `1
  passed, 11 deselected`, and the export/processed-profile consumer matrix
  returned `17 passed`. Structured verification passed with quality `287` and
  preprocessing `106`. Fresh real SAXS published-run replay returned `3
  passed, 12 deselected in 81.40s` with exit code `0`; it covered static,
  temperature, and strain lifecycle transport after the export change. The
  replay remains transport evidence only.
  The exact SAXS matrix timed out after `304s` without a
  summary; storage dry-run reported `572` artifacts, `42` eligible, `530`
  protected, and `0` removed. The explicit checkpoint was created; its final
  commit hash is reported in the handoff.
  Evidence: `docs/agent/tasks/2026-07-29-saxs-export-dirty-profile-guard.md`.

## SAXS ProcessedProfile dirty-input guard - checkpointed - 2026-07-29

- `ProcessedProfile` now coerces every q/intensity projection layer element by
  element, preserves malformed positions as `NaN`, records
  `diagnostics["invalid_numeric_values"]`, and reports `WARN` only when a
  conversion failure is present. The SAXS payload adapter applies the same
  behavior to q/raw; analysis algorithms, physical gates, and publication
  roles are unchanged.
- TDD RED reproduced `2 failed, 3 passed`; GREEN returned `5 passed in 0.15s`.
  The earlier exact SAXS file matrix had no summary and is not counted, but an
  authoritative rerun returned `531 passed, 6 warnings in 205.58s`, explicit
  exit code `0`. Structured verification passed and the explicit allowlist
  checkpoint is `311a8a8`.
- Evidence: `docs/agent/tasks/2026-07-29-saxs-processed-profile-dirty-input-guard.md`
  and `docs/acceptance/2026-07-29-saxs-processed-profile-dirty-input-guard.md`.

## Windows-native all-route capture retry - automated pass, science gates open - 2026-07-29

- Fresh `tests/test_native_gui_real_route_capture.py` returned `17 passed, 15
  warnings in 370.95s`, explicit exit code `0`, with `68` PNG captures under
  `D:\PolyNexus_native_all_routes_capture_20260729_retry`.
- The route covers DSC `3`, SAXS `3`, WAXS `3`, IR `2`, NMR `4`, synthetic
  Joint `1`, and synthetic IR mapping `1`; each exercises Results/Gallery/
  History/Editor and no-Origin fallback Export.
- Inspected boundary states remain explicit: SAXS temperature diagnostic-only,
  IR mapping `Not confirmed yet`, dense NMR solid-C labels, and Joint PA6-A with
  2 errors/2 warnings. This is native capture evidence only; human scientific,
  unlocked desktop, and release approval remain open. No data was deleted or
  migrated. Evidence: `docs/agent/tasks/2026-07-29-native-route-capture-retry.md`
  and `docs/acceptance/2026-07-29-native-route-capture-retry.md`.

## Test-storage dry-run audit - no deletion - 2026-07-29

- With no Python/pytest process active, `scripts/test_storage.py report --json`
  completed with empty stderr. Total: `556` artifacts, `236` eligible, `320`
  protected, `90,330,056,419` eligible bytes, and `0` removed.
- C: paths: `306` artifacts, `212` eligible, `94` protected,
  `76,691,802,567` eligible bytes, and `0` removed. This remains a dry-run;
  no `--apply`, delete, or migration was performed. Evidence:
  `docs/agent/tasks/2026-07-29-test-storage-dry-run-audit.md`,
  `docs/acceptance/2026-07-29-test-storage-dry-run-audit.md`, and
  `D:\PolyNexus_storage_audit_20260729_run2.json`.

## Full-software goal requirements audit - automated evidence mapped, release gates open - 2026-07-29

- A requirement-level matrix now maps shared platform, SAXS/DSC/WAXS/IR/NMR/
  Joint modes, Manifest/Gallery/Editor/export/history, Golden, AI-off/failure/
  fallback, full boundary, and visual/scientific gates to current evidence.
- It confirms automated evidence but explicitly leaves restarted-GUI content
  unverified because the session is locked, and leaves IR ROI semantics, NMR
  solid-C assignment, Joint conflicts, and final release authorization open.
- Evidence: `docs/agent/tasks/2026-07-29-full-goal-requirements-audit.md` and
  `docs/acceptance/2026-07-29-full-goal-requirements-audit.md`. No data or
  scratch cleanup was performed.

## Preprocessing Golden data audit - automated pass - 2026-07-29

- Fresh D:-isolated `tests/eval/preprocess/test_preprocess_golden.py` returned
  `3 passed in 0.13s`, explicit exit code `0`, using
  `D:\PolyNexus_preprocess_golden_20260729`.
- Golden fixtures were not modified. This complements real-data and
  AI-off/failure/fallback evidence but does not close scientific, restarted-GUI,
  or final release gates. No test data was deleted or migrated. Evidence:
  `docs/agent/tasks/2026-07-29-preprocess-golden-audit.md` and
  `docs/acceptance/2026-07-29-preprocess-golden-audit.md`.

## Results Workbench and Figure contract matrix - automated pass - 2026-07-29

- Fresh D:-isolated matrix across shared Workbench profiles, SAXS series/Figure
  contracts, DSC/WAXS Figure contracts, IR/NMR/Joint profiles, and the shared
  cross-technique figure pipeline returned `57 passed in 10.33s`, explicit exit
  code `0`, using `D:\PolyNexus_workbench_contract_matrix_20260729`.
- This is contract evidence only; scientific semantics, restarted-GUI visual
  review, and final release approval remain open. No data was deleted or
  migrated. Evidence:
  `docs/agent/tasks/2026-07-29-workbench-contract-matrix.md` and
  `docs/acceptance/2026-07-29-workbench-contract-matrix.md`.

## Cross-technique AI-off/failure/fallback matrix - automated pass - 2026-07-29

- Fresh focused command across `test_preprocess_cross_technique_matrix.py`,
  `test_preprocess_ai_off_compat.py`, and `test_preprocess_fault_injection.py`
  returned `25 passed in 0.23s`, explicit exit code `0`, with D: basetemp
  `D:\PolyNexus_ai_fallback_matrix_20260729`.
- This closes the deterministic safety-contract evidence only. Scientific
  quality, calibration, IR mapping, NMR assignment, Joint conflicts,
  restarted-GUI visuals, and release approval remain open; no data was deleted
  or migrated. Evidence:
  `docs/agent/tasks/2026-07-29-ai-fallback-matrix-audit.md` and
  `docs/acceptance/2026-07-29-ai-fallback-matrix-audit.md`.

## Restarted GUI visual audit attempt - locked desktop limitation - 2026-07-29

- The canonical `scripts/launch_gui.py` started a live Qt child titled
  `PolyNexus v2.0` with `Responding=True`.
- Desktop and window-handle screenshot commands returned fresh paths, but both
  images contained only the Windows lock screen. The application content was
  not visible, so the restarted-GUI visual gate remains unverified; this is an
  environment limitation, not a product pass/failure. The audit-started GUI
  process was closed and no data was deleted or migrated.
- A user-unlocked interactive session is required for the remaining all-route
  visual walkthrough. Evidence:
  `docs/agent/tasks/2026-07-29-restarted-gui-visual-audit.md` and
  `docs/acceptance/2026-07-29-restarted-gui-visual-audit.md`.

## Real published-run lifecycle walkthrough - automated pass, scientific gates open - 2026-07-30

- Fresh `tests/test_real_published_run_walkthrough.py` returned `15 passed, 11
  warnings in 361.98s (0:06:01)`, with explicit `WALKTHROUGH_EXIT_CODE=0`, using
  `D:\PolyNexus_real_walkthrough_current_20260730` as the external basetemp.
- Coverage is DSC `3`, SAXS `3`, WAXS `3` (including strain/2D), IR `2`, and
  NMR `4`; the shared engine -> figure run manifest -> Gallery -> Editor ->
  export/provenance lifecycle completed for the real fixtures.
- This is lifecycle transport evidence only. Scientific interpretation,
  unresolved IR vendor/ROI semantics, NMR solid-C assignment, Joint conflict
  meaning, restarted-GUI visual review, and final release approval remain open;
  no test data was deleted or migrated.
- Evidence task and acceptance note:
  `docs/agent/tasks/2026-07-30-real-published-run-walkthrough.md` and
  `docs/acceptance/2026-07-30-real-published-run-walkthrough.md`.

## Latest full/boundary audit evidence - automated gates green, release review open - 2026-07-28

- The current-checkout `scripts/verify.py --changed --types --full --boundary`
  process completed with captured stdout at
  `D:\PolyNexus_full_boundary_async_20260730_2\stdout.log` and an empty
  `stderr.log`. The fresh all-tests summary is `2986 passed, 17 skipped, 12
  warnings in 1907.60s (0:31:47)`; quality is `287 passed`, preprocessing is
  `106 passed`, and verifier stdout ends with `all selected checks passed`.
- The background launcher did not persist its wrapper exit code, so no wrapper
  exit code is asserted. A fresh direct boundary audit from the same checkout
  returned `BOUNDARY_EXIT_CODE=0`.
- This closes the automated full/boundary evidence gate only. Restarted-GUI
  visual review, IR vendor/ROI semantics, NMR solid-C assignment, Joint
  conflict interpretation, and final human scientific/release approval remain
  open. No test data was deleted or migrated.
- Evidence task and acceptance note:
  `docs/agent/tasks/2026-07-30-full-boundary-latest-evidence.md` and
  `docs/acceptance/2026-07-30-full-boundary-latest-evidence.md`.

## SAXS melting-window status dirty-input guard - completed 2026-07-28

- `classify_melting_window_status()` now reuses `_coerce_optional_float()` for
  consumed temperature/Tm scalars and `_as_1d_float_array()` for the existing
  temperature-window margin calculation. Invalid values follow the prior
  unresolved/undetermined branches; clean status/reason behavior, margin
  floors, expected-melt hints, thresholds, and publication semantics remain
  unchanged. No interpolation, frame repair, sorting, AI/rescue, or
  publication decision was added.
- Focused TDD evidence: RED `4 failed, 1 passed`; GREEN `5 passed in 0.26s`.
  Temperature matrix passed `53`; the independent exact SAXS retry passed
  `529 passed, 6 warnings in 218.57s`. The first SAXS matrix invocation hit a
  120-second tool timeout without a summary and is not counted.
- Structured verifier passed with quality `287` and preprocessing `106`; the
  targeted Ruff/compile and diff checks passed. Test-storage report/dry-run
  found `532` artifacts, `206` eligible, and `0` removed; no `--apply` was
  executed. No fresh full/boundary result is attributed to this slice.
- Evidence: `docs/acceptance/2026-07-28-saxs-melting-window-status-dirty-input-guard.md`.
- The explicit seven-file allowlist checkpoint was created and doc-only
  amended after verification; its final hash is reported in the handoff.
  Parallel `current-state.md`, `saxs_engine/io.py`, GUI/editor, and test-output
  changes remain untouched.

## SAXS invariant-conservation dirty-input guard - completed 2026-07-28

- `check_invariant_conservation()` now uses detached `_as_1d_float_array()`
  values, common-prefix alignment, finite strain/Q* pair selection, and
  `_coerce_strain_value()` for tolerance. Existing equations, minimum-point
  gate, result keys, finite negative-Q behavior, and physical semantics remain
  unchanged; no repair, interpolation, AI/rescue, or publication behavior was
  added.
- TDD RED was `6 failed`; focused GREEN was `6 passed in 0.13s`; strain
  returned `11 passed`; exact SAXS returned `524 passed, 6 warnings in
  195.72s`, exit code `0`. Task verifier without changed-file lint exited `0`
  with Pyright `0 errors`, quality `287`, preprocessing `106`, compile,
  whitespace, memory/task, and diff checks passing; targeted Ruff/compile also
  passed.
- The prescribed `--changed --types` variant exited `1` only on ten unrelated
  pre-existing Ruff findings in parallel-modified `saxs_engine/io.py`; that
  file remains outside the task allowlist and untouched. Storage dry-run found
  `530` artifacts, `202` eligible, `328` protected, and `0` removed. No fresh
  full/boundary result is attributed to this slice. Evidence:
  `docs/acceptance/2026-07-28-saxs-invariant-conservation-dirty-input-guard.md`.

## SAXS condition path-candidate recovery - completed 2026-07-28

- `_parse_condition_detail()` now evaluates every path component for a
  path-search pattern until conversion and validation succeed. An invalid
  pytest basetemp token no longer shadows a later valid `temperature_180`
  directory.
- `recover_condition_axis()` and `scan_experiment_dir()` preserve the existing
  `path_directory`, `temp_directory_label`, value `180.0`, and `0.72`
  confidence metadata contract. Context/header precedence, filename parsing,
  grouping, and unresolved keys are unchanged.
- TDD RED was the two unresolved-source/metadata failures; focused GREEN was
  `5 passed in 0.29s`. The fresh sorted exact SAXS matrix returned `518
  passed, 6 warnings in 201.93s`, exit code `0`; warnings are the existing
  Arial glyph and EDF geometry-header fallback warnings.
- Evidence: `docs/acceptance/2026-07-28-saxs-condition-path-candidate-recovery.md`.
- Test-storage cleanup remains dry-run only; no test data was deleted.

## SAXS temperature-phase dirty-input guard - completed 2026-07-28

- `detect_temperature_phase()` now coerces Q*, solid Q*, L, and solid L with
  the existing `_coerce_optional_float()` policy before its unchanged phase
  thresholds and enum branches. No phase inference, substitution,
  interpolation, AI/rescue, or publication behavior was added.
- TDD RED was `3 failed, 2 passed`; focused GREEN was `5 passed in 0.10s`;
  temperature returned `53 passed`; exact SAXS returned `518 passed, 6
  warnings in 256.45s`, exit code `0`. Task verifier without changed-file
  lint exited `0` with Pyright `0 errors`, quality `287`, preprocessing `106`,
  compile, whitespace, memory/task, and diff checks passing. Targeted Ruff and
  compile for task files passed.
- The prescribed `--changed --types` variant exited `1` only on ten unrelated
  pre-existing Ruff findings in parallel-modified `saxs_engine/io.py`; that
  file remains outside the task allowlist and untouched. Storage dry-run found
  `526` artifacts, `192` eligible, `334` protected, and `0` removed. No fresh
  full/boundary result is attributed to this slice. Evidence:
  `docs/acceptance/2026-07-28-saxs-temperature-phase-dirty-input-guard.md`.

## SAXS melting-range dirty-input guard - completed 2026-07-28

- `detect_melting_from_saxs()` now uses detached `_as_1d_float_array()` values,
  common-prefix alignment, and finite temperature/peak-intensity pair
  selection before its unchanged initial-median and sustained-threshold logic.
  The unused q* argument, finite negative intensities, physical thresholds,
  result keys, and publication semantics remain unchanged.
- TDD RED was `4 failed, 1 passed`; focused GREEN was `5 passed in 0.10s`;
  temperature returned `48 passed`; exact SAXS returned `513 passed, 6
  warnings in 238.42s`, exit code `0`. Structured verification exited `0`
  with quality `287`, preprocessing `106`, Ruff/compile/type baseline,
  task/memory, and whitespace passing; `git diff --check` passed.
- Storage dry-run found `522` artifacts, `24` eligible, `498` protected, and
  `0` removed. No full/boundary result is attributed to this slice. Evidence:
  `docs/acceptance/2026-07-28-saxs-melting-dirty-input-guard.md`.

## SAXS Avrami temperature-series dirty-input guard - completed 2026-07-28

- `avrami_from_temp_series()` now reuses `_as_1d_float_array()` for time,
  temperature, and Xc, aligns a detached common prefix, filters only
  non-finite observations and the existing `Tc_target ± tolerance` selection,
  preserves source order, and delegates to the unchanged Avrami fit. No
  interpolation, padding, sorting, fabricated data, AI rescue, or new physics
  gate was introduced.
- TDD RED was `4 failed, 1 passed`; focused GREEN was `5 passed in 0.10s`;
  temperature returned `48 passed`; exact SAXS returned `508 passed, 6
  warnings in 194.16s`, exit code `0`. Structured verification exited `0`
  with quality `287`, preprocessing `106`, Ruff/compile/type baseline,
  task/memory, and whitespace passing; `git diff --check` passed.
- Storage dry-run found `524` artifacts, `29` eligible, and `495` protected.
  The requested apply removed five eligible legacy directories before stopping
  at `D:\PolyNexus\PolyNexusPolyNexus.pytest_tmp_metric_position_full` with
  `WinError 5` access denied; follow-up found `518` artifacts and `24`
  eligible remaining. No permission escalation or manual deletion was used.
- Evidence: `docs/acceptance/2026-07-28-saxs-avrami-temp-series-dirty-input-guard.md`.

## SAXS Avrami dirty-input guard - completed 2026-07-28

- `avrami_kinetics()` now uses the existing `_as_1d_float_array()` coercion and
  common-prefix alignment before its unchanged finite/positive-time mask, Xc
  range selection, and fit. Malformed numeric tokens and mismatched lengths no
  longer raise; no observations are fabricated or sorted.
- TDD RED was `2 failed, 1 passed`; focused GREEN was `3 passed`; the
  temperature matrix returned `48 passed`; and the exact SAXS matrix returned
  `503 passed, 6 warnings in 265.09s`, exit code `0`. Structured verification
  exited `0` with quality `287`, preprocessing `106`, Ruff/compile/type
  baseline, task/memory, and whitespace checks passing. `git diff --check`
  passed.
- Test-storage report and cleanup dry-run found `522` artifacts, `26` eligible,
  `496` protected, and `0` removed. No full/boundary result is attributed to
  this atomic task. The explicit allowlist checkpoint hash is reported in the
  handoff. Evidence: `docs/acceptance/2026-07-28-saxs-avrami-dirty-input-guard.md`.

## SAXS Gibbs-Thomson dirty-input guard - completed 2026-07-28

- `gibbs_thomson_analysis()` now uses the existing `_as_1d_float_array()`
  coercion and common-prefix alignment before its unchanged finite/positive
  `lc` mask and Gibbs-Thomson fit. Malformed numeric tokens and mismatched
  lengths no longer raise; no observations are fabricated or sorted.
- TDD RED was `2 failed, 1 passed`; focused GREEN was `3 passed`; the
  temperature matrix returned `48 passed`; and the exact SAXS matrix returned
  `500 passed, 6 warnings in 231.46s`, exit code `0`. Structured verification
  exited `0` with quality `287`, preprocessing `106`, Ruff/compile/type
  baseline, task/memory, and whitespace checks passing. `git diff --check`
  passed.
- Test-storage report and cleanup dry-run found `520` artifacts, `179` eligible,
  `341` protected, and `0` removed. No full/boundary result is attributed to
  this atomic task. The explicit allowlist checkpoint hash is reported in the
  handoff. Evidence: `docs/acceptance/2026-07-28-saxs-gibbs-thomson-dirty-input-guard.md`.

## SAXS strain-helper dirty-input guard - completed 2026-07-28

- `detect_strain_phase()` and `detect_voids()` now reuse detached
  `sanitize_1d_profile()` survivors at their public 1D boundaries. Malformed
  object q/I, non-finite values, non-positive intensities, unsorted q, and
  mismatched lengths are handled by the existing aligned-prefix policy;
  phase/void thresholds, windows, return keys, and scientific semantics remain
  unchanged.
- TDD RED was `2 failed, 1 passed`; focused GREEN was `3 passed`; the strain
  matrix returned `11 passed`; and the exact SAXS matrix returned `497 passed,
  6 warnings in 193.07s`, exit code `0`. Structured verification exited `0`
  with quality `287`, preprocessing `106`, Ruff/compile/type baseline,
  task/memory, and whitespace checks passing. `git diff --check` passed.
- Test-storage report and cleanup dry-run found `505` artifacts, `175` eligible,
  `330` protected, and `0` removed. No full/boundary result is attributed to
  this atomic task. The explicit allowlist checkpoint hash is reported in the
  handoff. Evidence: `docs/acceptance/2026-07-28-saxs-strain-helper-dirty-input-guard.md`.

## SAXS Herman helper dirty-input guard - completed 2026-07-28

- The public `herman_orientation_factor()` boundary now uses detached,
  elementwise numeric angle/intensity coercion, finite-pair filtering, and
  stable angle sorting. Finite negative intensities remain; the Herman formula,
  angular windows, and evidence/publication semantics are unchanged.
- TDD RED was `2 failed, 1 passed in 0.49s`; focused GREEN returned `3 passed in
  0.18s`; the related strain/orientation matrix returned `36 passed in 0.82s`.
  The exact SAXS matrix returned `494 passed, 6 warnings in 259.20s`, exit code
  `0`, using `D:\PolyNexus_saxs_herman_dirty_matrix`.
- Structured verification exited `0` with quality `287`, preprocessing `106`,
  and task/memory, Ruff, compile/type, and whitespace checks passing. The
  explicit allowlist checkpoint hash is reported in the handoff. Task/spec/
  plan/acceptance:
  `docs/agent/tasks/2026-07-28-saxs-herman-dirty-input-guard.md`,
  `docs/superpowers/specs/2026-07-28-saxs-herman-dirty-input-guard-design.md`,
  `docs/superpowers/plans/2026-07-28-saxs-herman-dirty-input-guard.md`, and
  `docs/acceptance/2026-07-28-saxs-herman-dirty-input-guard.md`.

## Fresh native focused visual recheck - completed 2026-07-28

- Current-checkout native shards passed Joint (`1 passed`), IR mapping (`1
  passed`), and NMR solid-C (`1 passed`) using Windows Qt and D: basetemps.
  Fresh captures are under `D:\PolyNexus_native_joint_recheck_20260730`,
  `D:\PolyNexus_native_ir_mapping_recheck_20260730`, and
  `D:\PolyNexus_native_nmr_solid_c_recheck_20260730`.
- Joint identity is now visually consistent as `PA6-A` across header,
  breadcrumb, Current task, and Review focus. IR mapping retains its explicit
  structural/Not-confirmed boundary. NMR solid-C Editor exposes labels while
  assignment correctness and label density remain scientific review items.
- This does not close restarted-GUI all-mode approval, IR vendor/ROI meaning,
  NMR solid-C assignment, Joint conflict interpretation, or final release
  approval. Evidence: `docs/acceptance/2026-07-28-native-focused-visual-recheck.md`.

## SAXS Guinier helper dirty-input guard - completed 2026-07-28

- The public low-level `guinier_analysis()` boundary now reuses the existing
  detached `sanitize_1d_profile()` survivors before its unchanged fit. String,
  non-finite, non-positive, and unsorted q/I observations no longer raise or
  enter the fit in invalid order; clean output and the existing NaN/empty
  insufficient-point contract remain unchanged.
- TDD RED was `2 failed, 1 passed`; focused GREEN was `3 passed`. The exact
  SAXS matrix returned `487 passed, 6 warnings in 260.77s`, exit code `0`.
  Structured verification exited `0` with quality `287`, preprocessing `106`,
  Ruff/compile/type baseline, task/memory, and whitespace checks passing; diff
  check passed.
- No new threshold, interpolation, rescue, AI action, or publication change
  was introduced. No full/boundary result is attributed to this slice; the
  independent process had no readable terminal summary or exit code.
- Explicit allowlist checkpoint: `c4c78a7`; no push or merge was performed.
- Task/spec/plan/acceptance:
  `docs/agent/tasks/2026-07-28-saxs-guinier-dirty-input-guard.md`,
  `docs/superpowers/specs/2026-07-28-saxs-guinier-dirty-input-guard-design.md`,
  `docs/superpowers/plans/2026-07-28-saxs-guinier-dirty-input-guard.md`, and
  `docs/acceptance/2026-07-28-saxs-guinier-dirty-input-guard.md`.

## SAXS long-period helper dirty-input guard - completed 2026-07-28

- `bragg_long_period()`, `lorentz_fit_long_period()`, and
  `correlation_function()` now reuse detached `sanitize_1d_profile()` survivors
  and return stable empty diagnostics before indexing an empty q profile.
  Existing windows, fit behavior, extrapolation, and physical gates are
  unchanged; no interpolation, rescue, AI, or publication behavior was added.
- TDD RED was `3 failed in 0.54s`; focused GREEN returned `3 passed in 0.19s`.
  The exact SAXS matrix returned `490 passed, 6 warnings in 239.12s`, exit code
  `0`, using `D:\PolyNexus_saxs_long_period_dirty_matrix`.
- Structured verification exited `0`: task/memory checks, Ruff, compile, type
  baseline, quality (`287 passed`), preprocessing (`106 passed`), and
  whitespace passed; `git diff --check` also passed. The explicit allowlist
  checkpoint was closed with a doc-only amend; its final hash is reported in
  the handoff. Task/spec/plan/acceptance:
  `docs/agent/tasks/2026-07-28-saxs-long-period-dirty-input-guard.md`,
  `docs/superpowers/specs/2026-07-28-saxs-long-period-dirty-input-guard-design.md`,
  `docs/superpowers/plans/2026-07-28-saxs-long-period-dirty-input-guard.md`,
  and `docs/acceptance/2026-07-28-saxs-long-period-dirty-input-guard.md`.

## SAXS strain sector fail-closed - checkpointed - 2026-07-28

- Malformed nested sector payloads are downgraded to strict JSON-safe Unusable
  orientation evidence with `strain_sector_data_invalid`; the strain frame and
  existing 1D analysis remain present, while valid sector payloads retain their
  behavior.
- Fresh 2026-07-30 focused 2D/strain/batch recheck returned `69 passed in
  1.12s`, exit code `0`, using external D: basetemp. The follow-up acceptance
  record is `docs/acceptance/2026-07-30-saxs-strain-sector-fail-closed.md`.
- No complete SAXS/full-boundary result is attributed to this slice; scientific
  orientation interpretation and final release review remain open.

## Full/boundary verification - automated pass, human release gates open - 2026-07-30

- The captured rerun of `scripts/verify.py --changed --types --full --boundary`
  returned `2940 passed, 17 skipped, 12 warnings` in `1951.18s`, wrapper exit
  `0`, with quality `287`, preprocessing `106`, compile/Ruff/type/whitespace,
  and boundary audit passing. Stdout/stderr/exit-code evidence is under
  `D:\PolyNexus_full_boundary_capture_20260728_193018.*`.
- The earlier process-exit-only observation remains classified separately as a
  tool-level timeout; it was not retroactively treated as a pass.
- Automated full/boundary verification is now green for the captured checkout.
  Restarted-GUI visual review, IR vendor/ROI semantics, NMR solid-C assignment,
  Joint conflict interpretation, and final human scientific/release approval
  remain open. No test data cleanup or migration was performed.

## SAXS 1D physical-helper dirty-input guard - completed 2026-07-28

- The invariant, Porod, and Kratky helper boundaries now reuse the existing
  detached `sanitize_1d_profile()` survivors. Dirty non-finite, non-positive,
  and unsorted pairs no longer pollute integration or method arrays; empty
  Kratky input returns a stable empty payload instead of raising. Existing
  windows, point gates, evidence levels, and physical semantics are unchanged.
- TDD RED was `3 failed`; focused GREEN was `8 passed in 0.37s`; exact SAXS was
  `484 passed, 6 warnings in 257.12s`. Final task verification exited `0` with
  quality `287`, preprocessing `106`, Ruff, compile, type baseline, memory/task,
  and whitespace checks passing. The first verifier attempt found only legacy
  `E741` findings in the touched helper; the final narrow compatibility fix
  preserved public parameter names and passed.
- No fresh full/boundary result is attributed to this task; the separate audit
  remains classified as a tool timeout. Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-1d-method-dirty-input-guard.md`,
  `docs/superpowers/specs/2026-07-28-saxs-1d-method-dirty-input-guard-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-1d-method-dirty-input-guard.md`.

## SAXS Guinier sequence DataFrame integrity - completed 2026-07-28

- The temperature `TempSeriesResult.to_dataframe()` projection now exposes
  existing Guinier sequence frame/source, missing, diagnostic, invalid,
  duplicate, continuity, and source-order facts as deterministic flat fields.
  It preserves explicit `source_index_order_reordered` and leaves the nested
  evidence payload unchanged; no new threshold, sorting, interpolation, or
  rescue behavior was introduced.
- TDD RED was `2 failed, 7 deselected`; focused GREEN/compatibility was `14
  passed in 0.34s`; the exact SAXS matrix was `481 passed, 6 warnings in
  260.61s`. The task-scoped verifier exited `0` with quality `287` and
  preprocessing `106`, plus Ruff, compile, type baseline, memory/task, and
  whitespace checks. `git diff --check` exited `0`.
- A fresh full/boundary result is intentionally not claimed: the pre-existing
  verifier process was kept untouched and has no attribution to this slice.
  The task card, design, and implementation plan are
  `docs/agent/tasks/2026-07-28-saxs-guinier-sequence-dataframe-integrity.md`,
  `docs/superpowers/specs/2026-07-28-saxs-guinier-sequence-dataframe-integrity-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-guinier-sequence-dataframe-integrity.md`.

## SAXS real method-evidence surfaces - completed 2026-07-28

- The real Static/Temperature/Strain evidence-surface contract now has a
  focused regression and a minimal Figure binding fix. Fresh RED reproduced
  two production mismatches; fresh GREEN returned `3 passed in 41.92s`.
- Root cause and fix: Figure frame-level `metric_evidence` previously preferred
  preliminary `_batch_results`. It now consumes the already-emitted
  Temperature series point by `source_index` and the Strain series point by
  frame order, with the existing fallback retained.
- Task verifier passed with quality `287` and preprocessing `106`; the exact
  SAXS matrix returned `455 passed, 6 warnings in 240.01s`; diff check passed;
  storage report was dry-run only. Keep `current-state.md` and parallel
  scratch untouched. Task/spec/plan/acceptance:
  `docs/agent/tasks/2026-07-28-saxs-real-method-evidence-surfaces.md`,
  `docs/superpowers/specs/2026-07-28-saxs-real-method-evidence-surfaces-design.md`,
  `docs/superpowers/plans/2026-07-28-saxs-real-method-evidence-surfaces.md`,
  `docs/acceptance/2026-07-28-saxs-real-method-evidence-surfaces.md`.
- The explicit allowlist checkpoint is prepared. The separately started
  full/boundary verifier ended at the tool-level timeout with exit `124` after
  about `1804s`, without a pytest summary; a post-timeout process check found
  no residual Python/pytest process. It is not counted as a pass or failure.
- The latest storage report exited `0` in dry-run mode: `468` artifacts,
  `75` eligible, `393` protected, `38013194773` eligible bytes, and `0`
  removed. No test artifacts were deleted or moved.

## Joint workflow task identity - completed 2026-07-29

- The Joint Workbench task card now reads a single populated report row's
  existing display-only sample identity, so `PA6-A` no longer appears with a
  contradictory `No data loaded` task source. Empty/multi-sample behavior and
  persisted identity still use the existing resolver contract.
- TDD RED was `1 failed`; the focused Workspace/Joint/History/Persistence
  matrix is `41 passed, 177 deselected in 56.97s`. Structured verification
  exited `0` with quality `287` and preprocessing `106`; diff check passed.
- The explicit allowlist checkpoint is the task's only commit action.
- Task card, design, plan, and acceptance note:
  `docs/agent/tasks/2026-07-29-joint-workflow-task-identity.md`.

## Joint workspace context identity - completed 2026-07-29

- Native Joint review showed the task card identity was corrected but the
  compact workspace context line still used `No data loaded`. The follow-up
  now reuses the same existing display-only resolver for that line; the Joint
  report and persistence payload remain unchanged.
- TDD RED was `1 failed`; the focused regression GREEN was `1 passed in
  0.63s`. The focused matrix returned `42 passed, 177 deselected in 38.36s`;
  structured verification exited `0` with quality `287` and preprocessing
  `106`; diff check passed. Native Joint route returned `1 passed, 16
  deselected in 9.20s`, and the fresh capture shows `PA6-A` in both header
  locations.
- The explicit allowlist checkpoint is the task's only commit action.
- Task card, design, plan, and acceptance note:
  `docs/agent/tasks/2026-07-29-joint-workspace-context-identity.md`.

## SAXS acceptance audit surfaces - completed 2026-07-28

- Existing `scientific_acceptance_audit` snapshots now reach the Workbench as
  advisory review text, Figure/Manifest `quality_provenance`, and the bundle
  `quality_evidence.json` top level. Missing snapshots remain absent and all
  source mappings are detached before serialization.
- TDD RED was `3 failed, 1 passed`; focused GREEN was `4 passed`, and the
  surface/provider matrix was `15 passed`. Exact SAXS was `449 passed, 6
  warnings`; structured verifier passed with quality `287` and preprocessing
  `106`; test-storage was dry-run only. Checkpoint is recorded in the task
  acceptance note and final handoff. Scientific interpretation and publication
  approval remain open.
- Task card and plan:
  `docs/agent/tasks/2026-07-28-saxs-acceptance-audit-surfaces.md` and
  `docs/superpowers/plans/2026-07-28-saxs-acceptance-audit-surfaces.md`.

## SAXS Static scientific acceptance audit - completed 2026-07-28

- Static SAXS single-profile, aligned-batch, and batch-fallback parameter
  payloads now expose the existing read-only `scientific_acceptance_audit`.
  Publication flags remain `None` unless supplied by the existing publication
  boundary, and `publication_decision_changed` remains `False`.
- Focused TDD GREEN passed (`3`); exact SAXS matrix passed (`444 passed, 6
  warnings`). The task-scoped verifier and explicit allowlist checkpoint are
  recorded in `docs/acceptance/2026-07-28-saxs-static-acceptance-audit.md`.
- No SAXS metric, physical threshold, rescue, AI, frame alignment, or
  publication behavior changed. Scientific interpretation remains subject to
  existing gates and human review.

## SAXS acceptance audit Guinier sequence evidence - completed 2026-07-28

- The existing scientific acceptance audit now includes the existing Guinier
  sequence level and reason codes, including the real PA6
  `guinier_sequence_no_valid_frames` boundary. No Guinier calculation, frame
  repair, threshold, rescue, AI, publication, or export behavior changed.
- Focused tests passed (`2`); exact SAXS matrix passed (`441 passed, 6
  warnings`). Task-scoped verifier and explicit allowlist checkpoint remain to
  be finalized for this atomic task; checkpoint `b1470e7` is now created.

## SAXS acceptance audit lifecycle consistency - completed 2026-07-28

- `SAXSEngine._validate_results()` now refreshes an already-attached
  `scientific_acceptance_audit` after the existing SAXS result contract is
  published, so final `result.validation_passed` and audit validation agree.
- Real PA6 temperature evidence remains conservative: final validation is
  `False`, audit is `diagnostic_only`, and existing
  `guinier_sequence_no_valid_frames` is retained. No physical threshold,
  Guinier calculation, rescue, AI, publication, or static behavior changed.
- Focused lifecycle tests passed (`2`); exact SAXS matrix passed (`439 passed,
  6 warnings`). Structured verifier passed and the explicit allowlist checkpoint
  is `e83bef7`.

## SAXS temperature scientific acceptance audit - completed 2026-07-28

- The existing read-only `build_saxs_scientific_acceptance_audit()` is now
  attached to the SAXS temperature parameter payload only. No Guinier, Q*, mask,
  physical threshold, quality level, rescue, AI, or publication behavior
  changed.
- The real PA6 temperature run remains diagnostic: five frames at 170--220 °C,
  final `validation_passed=False`, existing Guinier sequence `Unusable` with
  `guinier_sequence_no_valid_frames`, and audit status `diagnostic_only`.
- Focused GREEN passed (`2`); exact SAXS matrix passed (`437 passed, 6
  warnings`). Structured verifier passed with quality `287`, preprocessing
  `106`, task/memory, Ruff, compile, type baseline, and whitespace green. The
  explicit allowlist checkpoint is `02cbc42`.

## Current full/boundary release recheck - automated green - 2026-07-29

- The current checkout passed `python scripts/verify.py --changed --types
  --full --boundary` with an isolated D: basetemp: `2883 passed, 17 skipped,
  12 warnings in 1405.74s`, exit code `0`.
- Quality passed `287`, preprocessing passed `106`, and compile, Ruff/type
  baseline, whitespace, and boundary audit all passed. This supersedes the
  older `2845 passed, 16 skipped` count as current automated evidence.
- Restarted-GUI visual review, IR vendor mapping semantics, NMR solid-C
  assignment semantics, Joint conflict interpretation, and final scientific/
  release approval remain explicitly open.

## SAXS dirty numeric coercion - checkpointed - 2026-07-28

- `_as_1d_float_array()` now preserves individually convertible q/I values when
  a 1D input contains malformed numeric tokens. Conversion failures become
  explicit NaN observations for the existing sanitizer and quality report;
  no interpolation, padding, duplicate aggregation, threshold, rescue, or AI
  behavior was added.
- TDD RED was `4 passed, 2 failed`; focused GREEN was `6 passed`; exact SAXS
  was `430 passed, 6 warnings`. Structured verification exited `0` with
  quality `287`, preprocessing `106`, Ruff/compile/type/memory/task/
  whitespace all passing.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-dirty-numeric-coercion.md`,
  `docs/superpowers/specs/2026-07-28-saxs-dirty-numeric-coercion-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-dirty-numeric-coercion.md`.
- The unrelated Results Review prefix-deduplication changes,
  `current-state.md` edit, and historical test/scratch files remain outside
  this checkpoint.

## SAXS 2D input shape fail-closed - checkpointed - 2026-07-28

- `analyze_anisotropy()` now converts array-like inputs into detached numeric
  arrays and rejects invalid or incompatible matrix/q/χ/1D-axis shapes before
  boolean indexing. The existing detector/orientation evidence path returns
  `Unusable` with `orientation_input_invalid` or
  `orientation_input_shape_mismatch`; no reshape, interpolation, geometry
  inference, or physical threshold was added.
- TDD RED was `9 passed, 1 failed`; focused GREEN was `10 passed`; exact SAXS
  was `431 passed, 6 warnings`. Structured verification exited `0` with
  quality `287`, preprocessing `106`, and Ruff/compile/type/memory/task/
  whitespace all passing.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-2d-input-shape-fail-closed.md`,
  `docs/superpowers/specs/2026-07-28-saxs-2d-input-shape-fail-closed-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-2d-input-shape-fail-closed.md`.
- Full/boundary verification and real detector scientific approval remain
  separate gates. The shared `current-state.md` and other parallel scratch
  files remain outside this checkpoint.

## SAXS real 2D scientific acceptance audit - checkpointed - 2026-07-28

- Added the read-only `scientific_acceptance_audit` to SAXS strain-series
  parameters. It reports existing validation, publication flags, quality
  levels, raw geometry/mask validity, reliability, and reason codes without
  changing any physical gate or publication decision.
- Fresh PAD8 evidence: `validation_passed=True` but audit status
  `diagnostic_only`; five raw detector reports remain Diagnostic, geometry/mask
  validity remains `not_assessed`, and the existing paper flags remain false.
- TDD focused GREEN was `4 passed`; exact SAXS was `435 passed, 6 warnings`;
  structured verifier passed with quality `287`, preprocessing `106`, Ruff,
  compile/type, memory/task, and whitespace checks.
- Task/spec/plan/acceptance:
  `docs/agent/tasks/2026-07-28-saxs-real-2d-scientific-acceptance.md`,
  `docs/superpowers/specs/2026-07-28-saxs-real-2d-scientific-acceptance-design.md`,
  `docs/superpowers/plans/2026-07-28-saxs-real-2d-scientific-acceptance.md`,
  and `docs/acceptance/2026-07-28-saxs-real-2d-scientific-acceptance.md`.
- Full/boundary verification, detector scientific validity, restarted-GUI
  review, and final publication/release approval remain open.
- The explicit allowlist implementation checkpoint is `e377d6a`; no push or
  merge was performed.

## Results Review prefix deduplication - checkpointed - 2026-07-29

- The shared Results Review boundary now strips repeated leading English or
  Chinese `Risk note`/`风险提示` and `Next step`/`下一步` decoration before
  applying the existing localized formatter once. Evidence text after the
  prefix and embedded labels remain unchanged.
- TDD RED captured `3` expected failures; focused GREEN passed `6`, the full
  Results Review service passed `28`, the Results/MainWindow slice passed `35`,
  and the persistence review subset passed `67`.
- Structured verification exited `0`: quality `287`, preprocessing `106`,
  Ruff, compile, type baseline, memory/task, and whitespace checks passed.
- Fresh focused recheck returned `45 passed, 187 deselected in 27.99s`.
- The task's explicit allowlist checkpoint is the documentation checkpoint for
  this atomic slice; the pre-existing `current-state.md` edit remains outside
  it.
- Task card and plan:
  `docs/agent/tasks/2026-07-29-results-review-prefix-deduplication.md` and
  `docs/superpowers/plans/2026-07-29-results-review-prefix-deduplication.md`.
- The existing uncommitted `current-state.md` legacy-storage edit remains
  intentionally outside this checkpoint. Restarted-GUI visual review and
  scientific/release approval remain open for the overall goal.

## DSC non-isothermal no-fabricated method curves - checkpointed - 2026-07-29

- The non-isothermal provider now requires finite authoritative method x/y
  points. Rates-only fit metadata becomes a diagnostic definition with no plot
  objects; method parameters, r², point count, and `missing_method_plot_data`
  remain in recipe metadata. Explicit-point qualified methods remain Main.
- TDD RED was `1 failed`; selected GREEN was `2 passed`. The DSC
  provider/lifecycle/eval matrix passed `13`, and the complete DSC plus real
  publication matrix passed `70`.
- Task card and plan:
  `docs/agent/tasks/2026-07-29-dsc-nonisothermal-no-fabricated-method-curves.md`
  and
  `docs/superpowers/plans/2026-07-29-dsc-nonisothermal-no-fabricated-method-curves.md`.
- Structured verifier exited `0`: quality `283`, preprocessing `106`, Ruff,
  compile, type baseline, memory/task, and whitespace checks passed. The
  allowlisted checkpoint is the current task commit. Scientific DSC review and
  restarted-GUI release gates remain separate.

## SAXS strain dirty-frame post-processing - checkpointed at 777eaef - 2026-07-28

- Strain 1D post-processing now reuses the deterministic sanitizer for
  reference/per-frame invariant, phase, and void consumers while preserving
  original q/I and quality provenance in `analyze_single()`.
- Focused matrix passed `9`; exact SAXS passed `428 passed, 6 warnings`.
  Fresh full/boundary passed `2869 passed, 17 skipped, 12 warnings` in
  `1686.81s`, exit code `0`; boundary audit passed.
- The implementation checkpoint is `777eaef`; the acceptance reconciliation is
  recorded in `docs/acceptance/2026-07-28-saxs-strain-dirty-frame-postprocessing.md`.
  Orientation/geometry and scientific publication review remain separate gates.

## SAXS temperature dirty-frame post-processing - checkpoint created - 2026-07-28

- Temperature post-processing now reuses `sanitize_1d_profile()` for reference
  invariant/Bragg, per-frame invariant, and Bragg peak tracking, while the
  original q/I arrays still reach `analyze_single()` for complete quality
  provenance. No interpolation, duplicate aggregation, new threshold, or
  frame fabrication was added.
- TDD RED was `1 failed, 3 warnings`; dirty/empty focused regression was `2
  passed`; exact SAXS was `425 passed, 6 warnings`. Task-scoped verification
  exited `0` with quality `283`, preprocessing `106`, Ruff/compile/type,
  memory/task, and whitespace checks passing.
- Fresh full/boundary passed `2869 passed, 17 skipped, 12 warnings` in
  `1686.81s`, exit code `0`; boundary audit passed. Human scientific review
  remains open; the explicit task checkpoint is created for handoff.

## Joint history identity - checkpointed - 2026-07-29

- History restore now projects a Joint report's persisted/sample identity into
  the display-only project badge. Single-sample, multi-sample, empty-report,
  explicit-label, and persistence cases are covered by a focused matrix with
  `5 passed`; the complete MainWindow persistence slice also passed `197`.
- Task-scoped verification passed; the allowlist is ready for one atomic
  checkpoint. Scientific Joint conflict interpretation and the restarted-GUI
  release gate remain open.
- Fresh recheck returned `4 passed, 194 deselected in 11.13s` for the focused
  identity filter and `21 passed, 178 deselected in 39.10s` for the broader
  Joint/history selection.
- Task card and plan:
  `docs/agent/tasks/2026-07-29-joint-history-project-identity.md` and
  `docs/superpowers/plans/2026-07-29-joint-history-project-identity.md`.

## Real published-run reacceptance - checkpointed - 2026-07-30

- The recorded 15-case real published-run walkthrough covers DSC standard /
  isothermal / non-isothermal, SAXS static / temperature / strain, WAXS
  static / temperature / strain / full-2D strain, IR standard / temperature-2D,
  and NMR liquid / solid H/C. It exercises Manifest/Gallery, Editor/export,
  and History restore. Existing warnings and diagnostic-only roles remain
  explicit.
  - Fresh task verification without `--changed` passed: Pyright `0 errors`,
    quality `287`, preprocessing `106`, compile, task/memory, and whitespace
    checks all passed. The fresh scoped `--changed --types` verifier also
    exited `0` with Ruff, compile, type baseline, quality `287`, preprocessing
    `106`, and whitespace passing. The earlier E741 result is stale historical
    evidence, not a current blocker.
- The documentation checkpoint allowlist is the task card, acceptance note,
  and this active-work entry. Full/boundary verification, human visual review,
  IR vendor semantics, Joint conflict meaning, solid-C assignment review, and
  final release approval remain open.
- Task card and acceptance note:
  `docs/agent/tasks/2026-07-29-real-published-run-reacceptance.md` and
  `docs/acceptance/2026-07-29-real-published-run-reacceptance.md`.

## Results Review Hint long-token layout - checkpointed - 2026-07-30

- The shared `WrappedEvidenceLabel` now serves MainWindow Results Summary/
  Review and ResultsTablePanel Review Hint detail/next labels. Review Hint
  labels use ignored horizontal size policies so long evidence does not widen
  the Results Workbench.
- RED reproduced a `1188` px ResultsTablePanel size hint before the follow-up
  policy bound; focused widget/GUI coverage passed `26` tests.
- Real SAXS temperature restore geometry returned panel width `557`, review-hint
  detail/next widths `375`/`374`, and workspace content width `1188` against a
  `1356` viewport. Native single-route capture passed `1` test with `16`
  deselected in `17.09s`.
- The structured verifier returned exit code `0`, with quality `287`,
  preprocessing `106`, Ruff, compile, type-baseline, memory/task, and whitespace
  checks passing. The explicit allowlist checkpoint is local-only; no push,
  merge, deploy, or data cleanup was performed.
- Human visual/scientific/release gates remain open. Task card and acceptance:
  `docs/agent/tasks/2026-07-30-results-review-hint-long-token-layout.md` and
  `docs/acceptance/2026-07-30-results-review-hint-long-token-layout.md`.

## Results Summary long-token layout - checkpointed - 2026-07-30

- Results Summary and Result Review evidence labels now preserve their exact
  source `.text()` while allowing Qt to wrap delimiter-free diagnostic tokens
  through invisible display-only break opportunities.
- TDD RED reproduced a `14664` px minimum width; focused layout/semantic,
  Review-service, and Results/Persistence matrices passed `12`, `28`, and `52`
  tests respectively.
- Fresh native Windows Qt validation returned `17 passed, 15 warnings in
  307.72s`, exit code `0`, with 68 captures under
  `D:\PolyNexus_native_all_routes_long_token_wrap_20260730`.
- The initial combined Qt command timed out at 180 seconds without a summary;
  it is not counted as pass/fail. Split commands produced the evidence above.
- The structured verifier returned exit code `0`, with quality `287`,
  preprocessing `106`, Ruff, compile, type-baseline, memory/task, and whitespace
  checks passing. The explicit allowlist checkpoint is local-only; no push,
  merge, deploy, or data cleanup was performed.
- Human visual/scientific/release gates remain open. Task card and acceptance:
  `docs/agent/tasks/2026-07-30-results-summary-long-token-layout.md` and
  `docs/acceptance/2026-07-30-results-summary-long-token-layout.md`.

## Fresh native all-mode route acceptance - checkpointed - 2026-07-29

- Current-checkout post-Joint-fix Windows-native Qt matrix: `17 passed, 15
  warnings in 358.71s`, exit code `0`; cases are DSC `3`, SAXS `3`, WAXS `3`, IR `2`, NMR
  `4`, synthetic Joint `1`, and synthetic IR mapping `1`.
- D:-isolated post-fix captures contain 68 images (Results/Gallery/History/Editor
  for every case), and every case exercised the no-Origin PackageExporter fallback.
- Visual inspection confirms constructible native surfaces and live labels;
  Joint now shows `PA6-A` in the project badge while retaining synthetic `No data loaded`
  context. Crowded NMR solid-C labels, synthetic IR mapping, and SAXS diagnostic /
  validation signals. Human visual/scientific/release review remains open.
- The dedicated acceptance reconciliation is recorded in
  `docs/acceptance/2026-07-29-native-all-mode-route-acceptance.md`; the
  automated checkpoint is already present in the current branch. This does not
  close the human review gates.
- Task card and plan:
  `docs/agent/tasks/2026-07-29-native-all-mode-route-acceptance.md` and
  `docs/superpowers/plans/2026-07-29-native-all-mode-route-acceptance.md`.

## Joint real-data transport acceptance - checkpointed - 2026-07-29

- Added `tests/test_joint_real_data_lifecycle.py` for real DSC standard, SAXS
  static, and WAXS static engine -> SampleDB -> Joint dataset/report -> Figure
  Manifest transport. Fresh recheck: `1 passed in 23.91s`, exit code `0`.
- Focused Joint/NMR matrix: `23 passed in 18.98s`, exit code `0`. Task-scoped
  verifier: exit code `0`, quality `287`, preprocessing `106`,
  Ruff/compile/memory/task/whitespace passed; changed type baseline selected no
  targets. Scientific interpretation, conflict review, and final release
  approval remain open.
- Task card and plan:
  `docs/agent/tasks/2026-07-29-joint-real-data-lifecycle.md` and
  `docs/superpowers/plans/2026-07-29-joint-real-data-lifecycle.md`.

## SAXS Static publication gate binding - checkpointed - 2026-07-28

- Static eligibility now requires the existing explicit
  `paper_figure_candidate=True` when assigning `main`; implicit
  `quality_flag="OK"` promotion is removed only from the Static provider path.
  Temperature and strain classifier behavior remains unchanged.
- TDD evidence: RED `1 failed, 2 passed` for the first gate and a second RED
  for reliability-only authorization; focused Static/provider/figure matrix
  `29 passed, 1 warning`; fresh SAXS matrix `423 passed, 8 warnings`.
- Fresh real SAXS walkthrough: `3 passed, 12 deselected, 2 warnings`; the
  generated Static Manifest has no Main, retains SI/Diagnostic entries, and
  persists `no_publication_ready_figure` with reason
  `static_frame_publication_authorization_missing`.
- Final structured verifier passed via the repository Python runtime after the
  reliability-only ordering correction with quality `283 passed, 2 warnings`,
  preprocessing `106 passed, 2 warnings`, Ruff, compile/type, memory, and
  whitespace checks passed. A fresh isolated full/boundary rerun then passed
  `2856 passed, 17 skipped, 14 warnings` in `1365.15s`; boundary audit also
  passed. The initial unisolated run's two user-directory permission failures
  were reproduced as `2 passed` in a writable environment and are retained as
  environmental diagnostics only. Implementation checkpoint: `63059d5`.
- Human GUI restart, scientific interpretation, and final publication/release
  approval remain open; no claim of scientific publication approval is implied.

## SAXS Workbench review evidence readability - checkpointed - 2026-07-28

- Existing advisory risk/next-step sections now render as ordered newline
  paragraphs instead of one space-joined paragraph. No evidence, physical,
  rescue, AI, or publication semantics changed.
- RED was `1 failed`; focused Workbench consumers were `104 passed`; exact SAXS
  matrix was `419 passed, 6 warnings`. Post-change full/boundary passed with
  `2851 passed, 17 skipped, 12 warnings` in 1567.25s; quality `283`,
  preprocessing `106`, compile, whitespace, and boundary audit passed.
- Task verifier passed with quality `283`, preprocessing `106`, Ruff, compile,
  memory/task, and whitespace checks. Explicit allowlist checkpoint:
  `6fe3128`. Keep the modified native GUI harness and all scratch/release files
  outside this task.
- Fresh 2026-07-30 focused recheck returned `36 passed in 4.28s` with external
  D: basetemp. The follow-up documentation allowlist is recorded in the task
  card and acceptance note; scientific and restarted-GUI review remain open.

## SAXS invalid temperature-time values fail-closed - checkpointed - 2026-07-28

- Correctly-sized optional time values are now coerced elementwise. Invalid or
  non-finite values preserve all temperature frames/source indices and disable
  Avrami with `temperature_time_axis_invalid_values`; length mismatch remains
  authoritative.
- RED was `1 failed`; focused GREEN was `25 passed`; exact SAXS was `418
  passed, 6 warnings`. Full/boundary verification is not claimed.
- Structured verifier passed with quality `283`, preprocessing `106`, Ruff,
  compile, memory/task, and whitespace checks. Explicit allowlist checkpoint:
  `c07d49a`. Full/boundary verification is not claimed.

## SAXS mismatched temperature time axis fail-closed - checkpointed - 2026-07-28

- A supplied time list with the wrong frame count now leaves temperature-frame
  analysis intact and marks Avrami unavailable with
  `temperature_time_axis_length_mismatch`; no synthetic time axis is used.
- RED was `1 failed`; focused GREEN was `24 passed`; exact SAXS was `417
  passed, 6 warnings`. Invalid time elements are a separate next boundary;
  full/boundary verification is not claimed.
- Structured verifier and explicit allowlist checkpoint passed locally; keep
  unrelated release/GUI/editor/scratch changes out of scope.

## SAXS invalid temperature-axis fail-closed boundary - checkpointed - 2026-07-28

- Invalid/non-finite temperature elements now become explicit NaN axis values
  through the existing coercion helper; frames and source indices remain
  visible and sequence evidence remains conservative.
- RED was `1 failed`; focused GREEN was `23 passed`; exact SAXS was `416
  passed, 6 warnings`. The separate mismatched-`times` `IndexError` is the
  next isolated boundary; no full/boundary pass is claimed.
- Structured verifier and explicit allowlist checkpoint passed locally; keep
  unrelated release/GUI/editor/scratch changes out of scope.

## SAXS empty temperature series fail-closed boundary - checkpointed - 2026-07-28

- Empty `temperatures/q_list/I_list` now returns a structured empty
  `TempSeriesResult` with existing `Unusable` sequence/metric evidence; the
  existing length mismatch `ValueError` remains unchanged.
- RED was `1 failed, 1 passed`; focused GREEN was `22 passed`; exact SAXS was
  `415 passed, 6 warnings`. No interpolation, frame fabrication, transition
  inference, rescue, AI, or non-empty path change was introduced.
- Structured verifier and checkpoint passed locally. Full/boundary repository
  verification is not claimed; keep unrelated release/GUI/editor/scratch
  changes outside the allowlist.

## SAXS empty-profile fail-closed boundary - checkpointed - 2026-07-28

- The deterministic sanitizer can produce an empty profile for empty or
  wholly invalid input. `analyze_single()` now stops at that boundary and
  returns empty `LongPeriodResult`/`StructureParams` plus existing `Unusable`
  quality and Guinier evidence, preserving source and actions.
- TDD RED was `1 failed`; focused GREEN was `17 passed`; the exact SAXS
  matrix was `413 passed, 6 warnings`. The task verifier passed with quality
  `283`, preprocessing `106`, Ruff/compile/type/memory/task/whitespace, and
  `git diff --check`.
- Full/boundary repository verification was not run for this scoped task. The
  explicit allowlist checkpoint is local-only; do not mix pre-existing
  GUI/editor/release/scratch files or claim the full software goal complete.

## Full release-audit recheck - open - 2026-07-28

- Latest D:-isolated full/boundary result is green: `2845 passed, 16 skipped,
  12 warnings` in `1574.30s`, verifier exit code `0`; compile, quality (`283`),
  preprocessing (`106`), Ruff/type baseline, whitespace, and boundary audit
  also passed. The earlier `2836 passed, 16 skipped, 12 warnings, 2 failed`
  result (verifier exit `1`) is retained as historical diagnostic evidence;
  its two SAXS condition-recovery failures were not reproduced by the focused
  rerun or the fresh full run.
- Fresh delegated-shard rechecks are green: IR published-run `2 passed, 13
  deselected in 84.78s`; NMR solid-C lifecycle `1 passed, 3 deselected in
  126.89s`; both exit code `0`.
- The later independent recheck captured full output rather than relying on
  process exit: IR walkthrough `2 passed, 13 deselected in 88.67s`; NMR
  walkthrough `4 passed, 11 deselected in 132.02s`; exact NMR solid-C lifecycle
  `1 passed, 3 deselected in 138.00s`; all exit code `0`.
- Continuation visual review re-inspected the D:-isolated 68-capture native
  matrix. Synthetic IR mapping Results/Editor are structurally usable; NMR
  solid-C peak labels remain crowded; and synthetic Joint diagnostics retain a
  `No project` / `No data loaded` restore header. A direct OS capture of the
  stale running window returned wallpaper and is not counted as restarted-GUI
  evidence. The full plan now separates automated completion from the open
  restarted-GUI and human-scientific gates.
- A new GUI process (`PID 39700`) was started and closed gracefully after
  Qt-native captures of the default shell and SAXS static-to-temperature
  switch. This is fresh restarted-shell evidence, not completion of the
  all-mode real-data/Gallery/Editor/export or human release gates.
- Automated full-release evidence is green for the fresh run. Restarted-GUI,
  scientific review, and final release approval remain open; do not call the
  overall goal complete while those human gates remain open.

## SAXS structure-parameter fail-closed guard - checkpointed - 2026-07-28

- Root-cause reproduction showed that a 24-point `q=0.02..0.6` profile raised
  `UnboundLocalError` because `idf_is_artifact` was initialized only inside
  the tangent-success branch. The minimal default initialization is now in
  place; the existing artifact heuristic and confidence logic are unchanged.
- TDD RED was `1 failed`, focused GREEN was `21 passed`, and the exact SAXS
  matrix was `412 passed, 6 warnings`. The external-D structured verifier
  passed with quality `283`, preprocessing `106`, task/memory, Ruff,
  compile/type, and whitespace checks. The explicit allowlist checkpoint was
  created locally; no push, merge, release, or scientific publication approval
  is implied. Do not mix pre-existing GUI/editor/release/scratch files.

## SAXS 1D quality provenance source binding - checkpointed - 2026-07-28

- `DataQualityReport` provenance is now bound through `analyze_single()`, the
  temperature/strain series APIs, and the high-level static/temperature/strain
  engine paths. Temperature retains original frame indices after sorting;
  missing or mismatched sources stay empty.
- TDD RED was `5 failed`; focused GREEN was `27 passed`; the exact SAXS matrix
  is `411 passed, 6 warnings`. The only repair was a compatibility-only update
  to an existing temperature test double so it accepts the new optional kwargs.
- The first verifier attempt hit the existing `.pytest_tmp` Windows permission
  lock; the external-D rerun passed with quality `283`, preprocessing `106`,
  Ruff/compile/type/memory/task/whitespace checks green. Final focused tests
  and diff check passed. The explicit allowlist checkpoint was created
  locally; no push, merge, release, or scientific publication approval is
  implied. Do not mix GUI/editor/release/scratch files or claim the full
  software goal complete.

## SAXS deterministic 1D profile sanitization - checkpointed locally - 2026-07-28

- The new `Sanitized1DProfile` contract gives SAXS 1D methods a detached
  finite/positive q/I copy. Invalid pairs are removed and q is stably sorted;
  exact duplicate q observations remain in order and are explicitly marked,
  with no interpolation, averaging, frame fabrication, or new threshold.
- TDD RED was `4 failed, 11 passed`; GREEN focused evidence is `20 passed`.
  Exact SAXS evidence is `406 passed, 6 warnings`. The task verifier passed
  with quality `283` and preprocessing `106`.
- An earlier D:-isolated full/boundary verification passed `2838 passed, 16
  skipped, 12 warnings` in `1579.21s`; the later release-audit rerun is now
  authoritative and has the two SAXS condition-recovery failures recorded in
  the release-audit section above. The earlier C:-based attempt failed from
  `No space left on device` and is not counted.
- The explicit allowlist checkpoint is local-only; no push. Existing
  GUI/editor/release drafts, scratch directories, and parallel changes remain
  untouched.

## Native all-mode route evidence refreshed - 2026-07-28

- Fresh current-checkout native rerun returned `17 passed, 15 warnings in
  363.16s`, exit code `0`, in a new pytest process with D:-isolated temp and
  capture roots. It covered the 15 real fixture routes (including WAXS
  full-2D strain), synthetic Joint, and synthetic IR mapping; all four shared
  surfaces and PackageExporter fallback were exercised. Captures are under
  `D:\PolyNexus_native_all_routes_capture_20260728_with_ir_mapping`.
- Visual inspection confirms live CJK and opaque Results text. The synthetic
  IR mapping heatmap/ROI/editor route is constructible but does not validate
  vendor-native semantics. Solid-C peak-label crowding and the synthetic
  Joint `No project`/`No data loaded` header alongside diagnostics remain
  review signals; human scientific review and final release approval remain
  open.
- After the shared Results opacity correction, the D:-isolated native harness
  passed `15 passed, 1 deselected, 15 warnings in 398.02s`, exit code `0`,
  covering every real DSC/SAXS/WAXS/IR/NMR mode. Each route restored a
  populated Results Workbench, Gallery, History, Editor, and PackageExporter
  fallback output. Synthetic Joint passed `1 passed, 15 deselected in 8.92s`.
- Representative native captures are under
  `D:\PolyNexus_native_all_routes_capture_20260728`; Results text is opaque
  and live CJK labels render. NMR solid-C peak-label crowding remains a review
  signal rather than an unverified production change.
- The first C:-based run (`4 passed, 11 failed`) hit the actual full-volume
  limit and is classified as environment failure. Old unreferenced diagnostic
  directories were moved, not deleted, to
  `D:\PolyNexus_temp_archive_20260728`.
- Next action remains human restarted-GUI/scientific review and release
  decision; this evidence does not close the active full-software goal.

## Results Workbench main-Tab opacity correction - checkpointed - 2026-07-28

- The native pale-body diagnosis was isolated to the shared main-Tab fade:
  `_on_tab_changed()` applied `QGraphicsOpacityEffect` to the whole scientific
  page. It now leaves main Tab pages opaque and keeps only local transient
  animations.
- TDD RED was the new Tab-route assertion failing on the installed effect;
  GREEN is `23 passed` across the focused Results/MainWindow matrix. Native
  SAXS static/temperature/strain capture passed `3` cases in `44.10s`, and the
  fixed Results screenshots were inspected under
  `C:\Temp\polynexus_native_saxs_visual_20260728_fixed`.
- The task verifier passed with external basetemp, including quality `283`,
  preprocessing `106`, Ruff, compile/type, memory/task, and whitespace. The
  initial in-repository verifier attempt hit the known `.pytest_tmp` Windows
  permission lock and is excluded; no scratch cleanup was performed.
- Fresh 2026-07-30 follow-up returned focused `23 passed in 5.42s` and native
  SAXS `3 passed, 14 deselected in 57.98s`, exit code `0`, with D: isolation.
- The documentation checkpoint is allowlisted in the task card and acceptance
  note. Restarted-GUI visual review for all techniques, scientific review, and
  release approval remain open. Task card:
  `docs/agent/tasks/2026-07-28-results-workbench-tab-opacity.md`.

## SAXS parameter quality-evidence reference - checkpointed at 1608643 - 2026-07-28

- SAXS bundle `parameters.json` now points to the authoritative
  `quality_evidence.json`, and each `data/parameters.csv` row carries the
  relative `quality_evidence_ref`; AI/quality payloads are not duplicated into
  CSV.
- TDD RED/GREEN, focused History/Export `14 passed`, exact SAXS `402 passed,
  6 warnings`, task verifier, and fresh full/boundary `2832 passed,
  16 skipped, 12 warnings` with boundary audit pass are recorded in the task
  card. Checkpoint `1608643` was local-only; no push.
- This is traceability only: it does not promote evidence, accept rescue
  candidates, or authorize scientific/publication claims.

## Joint evidence-weighted conflict severity - completed 2026-07-28

- Joint Tm/Gibson-Thompson conflicts now inherit the minimum DSC/SAXS evidence
  weight at the dataset boundary. A failed conflict with weight `< 0.5` is a
  visible `WARN` rather than a hard `ERROR`; numeric details and `passed=False`
  remain unchanged. Fully evidenced conflicts remain `ERROR`.
- TDD RED exposed the diagnostic-only SAXS case as an `ERROR`; GREEN plus the
  Joint component/lifecycle/provenance matrix passed `23` tests. The task
  verifier passed quality `283` and preprocessing `106`.
- See `docs/acceptance/2026-07-28-joint-evidence-weighted-conflicts.md` and
  `docs/agent/tasks/2026-07-28-joint-evidence-weighted-conflicts.md`.
  Real Joint inputs, IR/NMR calibration semantics, restarted-GUI review, and
  human scientific approval remain open.

## NMR release evidence reconciliation - automated boundary recorded - 2026-07-28

- Fresh NMR provider/provenance/eval/profile evidence passed `26` tests with
  an external basetemp. The real liquid/solid H/C published-run walkthrough
  passed `4` selected cases with `11` deselected.
- The evidence is recorded in
  `docs/acceptance/2026-07-28-nmr-release-evidence-reconciliation.md` and the
  task card
  `docs/agent/tasks/2026-07-28-nmr-release-evidence-reconciliation.md`.
- This closes only the automated NMR software lifecycle boundary. Solid-C Xc
  remains assignment-limited/provisional; vendor semantics, restarted-GUI
  visual review, human scientific review, and final release approval remain
  open.

## IR release evidence reconciliation - automated boundary recorded - 2026-07-28

- The focused current-head IR provider/mapping/lifecycle matrix passed `31`
  tests with an external basetemp. The real standard and temperature-2D
  published-run walkthrough passed `2` selected cases with `13` deselected.
- The evidence is recorded in
  `docs/acceptance/2026-07-28-ir-release-evidence-reconciliation.md` and the
  task card
  `docs/agent/tasks/2026-07-28-ir-release-evidence-reconciliation.md`.
- This closes only the automated IR software-lifecycle/evidence boundary.
  Vendor mapping/ROI semantics, restarted-GUI visual review, and human
  scientific/release approval remain open. The task-scoped changed/type
  verifier passed with quality `283` and preprocessing `106`; unrelated
  untracked SAXS work remains outside this checkpoint.

## Results Workbench Light-theme contrast correction - ready for checkpoint - 2026-07-28

- Reproduced the native pale-body issue as a production defect: Results labels
  used dark-only inline colors while the active Light background was pale.
  `MainWindowResultsMixin` now reapplies active `ThemeTokens` during creation
  and live theme changes; Light `text_muted` is `#667085` with `4.72:1` body
  contrast against `#f7f9fc`.
- TDD RED: the Light-theme label assertion failed with `#e8eaf0`, and the
  contrast assertion failed at `2.98:1`. GREEN: Results/theme focus `24 passed`.
  Native representative route passed `1` case; the full non-Joint native matrix
  passed `15` cases with exit `0` after the fix.
- Remaining work is activated/restarted-GUI visual review and the existing
  scientific/release gates; no scientific threshold or result semantics changed.
- The native harness now raises and activates the window before each capture.
  A fresh DSC probe passed `1` case in `6.90s` without deprecated Qt activation
  warnings, but Gallery body text remained pale; no additional production
  Gallery color change is justified by this screenshot alone.
- The explicit allowlist checkpoint is the next action; no push, merge,
  deployment, or release approval is implied.

## Native Results restore acceptance correction - evidence refreshed - 2026-07-28

- The native GUI route harness now restores the actual engine result payload
  (`parameters` plus `AnalysisResult.to_dict()`) instead of an empty result
  record. A regression assertion requires a primary Results section and at
  least one rendered Results row, preventing a Gallery-only false positive.
- TDD RED was the DSC native route failing at `assert 0 > 0`; GREEN was the
  same route passing. Fresh technique shards passed with exit code `0`: DSC
  `3`/`23.13s`, SAXS `3`/`48.91s`, WAXS `3`/`85.25s`, IR `2`/`65.91s`, and NMR
  `4`/`111.49s`. Independent real walkthrough refreshes also passed: IR `2`
  in `70.19s` and NMR `4` in `105.59s`, both exit `0`.
- Representative native Results captures now correspond to populated tables,
  but body text remains pale in inactive `grab()` captures. Restarted-GUI
  contrast/activity review, IR vendor mapping/ROI semantics, solid-C NMR
  assignment, Joint scientific conflicts, and final release approval remain
  open. No production GUI or scientific semantics changed.

## SAXS rescue-candidate Workbench visibility - checkpointed at e214d76 - 2026-07-28

- The existing deterministic temperature sequence-rescue candidates are now
  copied into the public temperature parameters payload and rendered as
  read-only Workbench review evidence. The display is bounded to candidate
  ID, frame/source, proposed value/mode, validation-required state, and reasons.
- Candidate values remain advisory: no apply, rerun, acceptance, interpolation,
  or physical interpretation was added. Malformed/empty candidates stay absent;
  static and strain paths remain unchanged.
- TDD RED was `2 failed, 1 passed`; GREEN was `3 passed`. Focused consumer
  evidence is `97 passed`; exact SAXS evidence is `393 passed, 6 warnings`.
  The task verifier exited `0` with quality `283`, preprocessing `106`,
  task/memory, Ruff, compile/type baseline, and whitespace checks. Full/boundary
  verification was not run for this slice.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-rescue-candidate-workbench-visibility.md`,
  `docs/superpowers/specs/2026-07-28-saxs-rescue-candidate-workbench-visibility-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-rescue-candidate-workbench-visibility.md`.
- The explicit allowlist implementation checkpoint is `e214d76`; no push,
  merge, deployment, or scientific/publication approval is implied.

## SAXS DataQualityReport Workbench visibility - checkpointed at fb76039 - 2026-07-28

- The Results Workbench now presents the existing q/I `DataQualityReport` as
  read-only advisory context across static, temperature, and strain payloads.
  Top-level reports show existing level, source/data refs, point counts,
  reasons, and actions. Batch payloads show only reported-frame coverage,
  emitted level counts, and first-seen reason/action summaries.
- Malformed or missing reports remain absent; one frame's report is never
  copied to another row. Presentation is non-mutating and does not alter q/I
  cleaning, thresholds, physical gates, rescue, AI, or publication roles.
- TDD RED covered missing batch-summary boundaries and the raw-reference field;
  GREEN/focused evidence is `59 passed`. The task-scoped verifier with external
  basetemp exited `0`: quality `283`, preprocessing `106`, task/memory, Ruff,
  compile/type baseline, and whitespace checks passed. Full/boundary coverage
  was not run for this slice.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-data-quality-workbench-visibility.md`,
  `docs/superpowers/specs/2026-07-28-saxs-data-quality-workbench-visibility-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-data-quality-workbench-visibility.md`.
- The explicit implementation checkpoint is `fb76039`; no push, merge,
  release, or scientific/publication approval is implied.

## SAXS DataQualityReport DataFrame and CSV export - 2026-07-28

- The existing q/I `DataQualityReport` is now projected into temperature and
  strain DataFrame rows plus static parameter CSV fields. The projection keeps
  source/reference fields, level, ordered reasons/actions, defect counts, and
  emitted boolean flags; missing reports remain empty. No cleaning, fitting,
  threshold, physical gate, rescue, AI, or publication behavior changed.
- TDD RED was `3 failed, 18 passed`; GREEN was `21 passed`. The exact SAXS
  matrix was `383 passed, 6 warnings`; the structured verifier exited `0` with
  quality `283`, preprocessing `106`, Ruff, compile/type, memory/task, and
  whitespace checks.
- Status is checkpointed at `b0c63d7` with the explicit allowlist; no push was
  performed. Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-data-quality-dataframe-export.md`,
  `docs/superpowers/specs/2026-07-28-saxs-data-quality-dataframe-export-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-data-quality-dataframe-export.md`.
- Scientific review of whether dirty-data reports support a particular claim,
  detector calibration, rescue approval, and publication eligibility remain
  separate gates.

## SAXS detector provenance DataFrame and CSV export - 2026-07-28

- The existing raw-detector provenance is now projected into temperature and
  strain DataFrame rows plus static parameter CSV dictionaries through one
  fixed ten-column helper. Field-source ordering is deterministic, mask shape
  is `heightxwidth`, missing reports remain empty, and `not_assessed` is copied
  literally. No nested evidence, quality level, physical gate, rescue, or
  publication role changed.
- Focused GREEN passed `21`; the exact SAXS matrix passed `383` with `6`
  existing warnings; structured verification exited `0` with quality `283`,
  preprocessing `106`, Ruff, compile/type, memory/task, and whitespace checks.
  The first unsplit matrix invocation was incomplete and is not counted;
  four fresh isolated shards are the authoritative matrix evidence.
- Status is checkpointed at `4d09085` with the explicit allowlist; no push was
  performed. Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-detector-provenance-dataframe-export.md`,
  `docs/superpowers/specs/2026-07-28-saxs-detector-provenance-dataframe-export-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-detector-provenance-dataframe-export.md`.
- Detector calibration, beam-center interpretation, mask validity, saturation
  meaning, and human scientific/publication approval remain open.

## SAXS Workbench geometry and mask provenance visibility - 2026-07-28

- Results Workbench now presents existing raw-detector geometry aggregate/source
  counts and mask source/configured/shape facts as read-only review context.
  `validity=not_assessed` remains explicit; no quality level, threshold,
  scientific status, rescue, or publication role is inferred.
- The formatter is raw-field-only: sector-map evidence remains separate and
  cannot inherit raw geometry/mask claims. Input mappings are not mutated and
  English/Chinese labels are deterministic.
- TDD RED was `3 failed, 3 passed, 44 deselected`; GREEN was `6 passed, 44
  deselected`; Workbench/Export/Figure consumers were `67 passed`. Focused
  Ruff, compile, and diff checks passed. The exact SAXS matrix was `380 passed,
  6 warnings`; the task verifier exited `0` with quality `283` and
  preprocessing `106`.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-workbench-geometry-mask-provenance.md`,
  `docs/superpowers/specs/2026-07-28-saxs-workbench-geometry-mask-provenance-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-workbench-geometry-mask-provenance.md`.
- Geometry calibration, beam-center interpretation, mask scientific validity,
  saturation meaning, and human release/publication review remain open.

## SAXS raw detector geometry and mask provenance transport - 2026-07-28

- Raw detector reports now carry read-only `geometry_provenance` and
  `mask_provenance`. Geometry records per-field header/default/invalid source
  plus effective config values; mask records only the existing dummy-value
  configuration and aligned shape. Both explicitly use `validity=not_assessed`.
- Figure evidence transports the two fields only through the semantic
  `raw_detector_quality_report` allowlist. Sector-map `detector_quality_report`
  remains separate and cannot acquire raw geometry/mask claims.
- TDD RED was `4 failed, 5 passed`; GREEN focused raw transport was `9 passed,
  2 warnings`. Consumer matrix was `64 passed`; exact SAXS matrix was `377
  passed, 6 warnings` under external basetemp.
- The task-scoped verifier initially hit the pre-existing repository
  `.pytest_tmp` Windows permission lock (`229 passed, 54 errors`) while
  unrelated GUI/IR Python processes were alive. Rerun with external basetemp
  exited `0`: quality `283`, preprocessing `106`, Ruff/compile/type, memory,
  task check, and whitespace passed. No unrelated process or scratch file was
  changed.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-raw-detector-provenance.md`,
  `docs/superpowers/specs/2026-07-28-saxs-raw-detector-provenance-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-raw-detector-provenance.md`.
- Detector geometry calibration, beam-center interpretation, mask scientific
  validity, saturation meaning, rescue/publication approval, and human release
  review remain open.

## SAXS Workbench detector evidence visibility - 2026-07-28

- The Results Workbench now projects the existing `raw_detector_quality_report`
  and `detector_quality_report` separately into advisory risk/next-step text.
  The projection uses only existing source kind, level, frame coverage,
  coverage fraction, and reason codes; it does not recompute detector quality,
  infer geometry/mask validity, change levels, or authorize rescue/publication.
- TDD evidence: RED `3 failed, 44 deselected`; GREEN `3 passed, 44 deselected`.
  The Workbench/Export/Figure consumer matrix passed `64`; the exact SAXS
  matrix passed `374` with `5` existing warnings under external basetemp
  `C:\Temp\PolyNexus_saxs_workbench_detector_saxs_matrix`.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-workbench-detector-evidence-visibility.md`,
  `docs/superpowers/specs/2026-07-28-saxs-workbench-detector-evidence-visibility-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-workbench-detector-evidence-visibility.md`.
- Structured verifier exited `0` with task/memory, Ruff, compile/type baseline,
  quality `283`, preprocessing `106`, and whitespace checks passed using
  external basetemp `C:\Temp\PolyNexus_saxs_workbench_detector_verify_final`.
  The explicit allowlist checkpoint was created with `scripts/auto_commit.py`;
  no push was performed. Human review of detector geometry, beam-center
  meaning, mask validity, saturation interpretation, and publication
  eligibility remains open.

## Native Windows Qt DSC route capture - 2026-07-28

- Ran the existing real-result GUI capture with
  `QT_QPA_PLATFORM=windows` and external basetemp
  `C:\Temp\PolyNexus_native_gui_route`: `1 passed in 5.93s`.
- Inspected native captures for DSC Results, Gallery, History, and Editor at
  1600x1000. CJK glyphs rendered normally and the shared route surfaces were
  constructible. This closes live-font evidence for one DSC route only; it
  does not close all-mode visual review or export interaction.
- Evidence remains in the full release task/acceptance note; no production
  code or scientific semantics changed.

## Native Windows Qt all-route capture - 2026-07-28

- The reusable `tests/test_native_gui_real_route_capture.py` harness now merges
  `_real_cases()` with `_full_2d_real_cases()`, covering all 15 real modes,
  including `waxs.strain` and `ir.temperature_2d`.
- Fresh native Windows Qt shards passed with exit code `0`: DSC `3` in
  `25.44s`, SAXS `3` in `49.93s`, WAXS `3` in `86.35s`, IR `2` in `66.72s`,
  and NMR `4` in `114.85s`. Each case captured Results, Gallery, History, and
  Editor under external `C:\Temp\PolyNexus_native_gui_*_verified` folders.
- Representative native captures show constructible shared routes, plots,
  Editor controls, and live CJK labels. Results/Gallery body contrast in
  inactive `grab()` captures and Export button interaction remain human visual
  gates; no production code or scientific semantics changed.
- The earlier combined native invocation is recorded as a tool-level timeout
  without a pytest summary. Its old `waxs.strain` filter exit code `5` was a
  harness-selection error before full-2D imports were added, not a product
  failure. See `docs/acceptance/2026-07-27-full-software-release-audit.md`.

## Native all-route package Export interaction - 2026-07-28

- The native harness now triggers the real Chart Editor Export `QAction` after
  opening each real mode's Editor. It injects only the existing `PackageExporter`
  adapter so the test cannot start an installed Origin/COM process.
- The export matrix passed with exit code `0`: DSC `3` in `24.25s`, SAXS `3`
  in `49.85s`, WAXS `3` in `87.35s`, IR `2` in `67.19s`, and NMR `4` in
  `117.75s`. Every case produced `Origin_Export/figure_document.json`,
  `metadata.json`, and `import.ogs` in its external run output.
- This closes automated package-fallback Export coverage across all modes. The
  installed OriginPro/COM adapter path remains optional-runtime/manual review;
  inactive native screenshot body contrast also remains a human visual gate.

## Native synthetic Joint route - 2026-07-28

- A native synthetic Joint probe passed `1 passed, 15 deselected in 5.94s`,
  exit code `0`. It restores the existing `JointCoordinator` report through
  `joint.compare`, captures Results/Gallery/History/Editor, and verifies the
  package Export artifacts.
- This is shared GUI/export route evidence only. No real-data Joint fixture or
  scientific conflict interpretation is inferred; those remain human review.

## Fresh current full/boundary release verification - 2026-07-27

- The current working tree completed
  `python scripts/verify.py --changed --types --full --boundary` with an
  external basetemp. The full pytest portion returned `2793 passed, 10
  warnings in 1607.00s (0:26:46)` and exit code `0`.
- Compile, quality `283`, preprocessing `106`, Ruff/type, whitespace, and
  boundary audit all passed. Existing warnings are tight-layout,
  DSC polynomial-conditioning, and Arial CJK glyph warnings.
- This supersedes the older `2af4baf`/`2790` count for current-state
  reporting. Restarted-GUI visual review, IR vendor mapping/ROI semantics,
  assignment-limited NMR/Joint review, and final human release approval remain
  open.

## Joint route plan reconciliation - 2026-07-27

- The old Phase 7 wording that `joint.compare` still lacked the shared figure
  entrypoint was stale. `JointHubWorker` currently calls
  `JointCoordinator.publish_hub_report()`, and the Joint lifecycle restores
  the custom Workbench plus Manifest-backed Gallery after Editor/export/
  History operations.
- Current provider/coordinator/lifecycle/Workbench focused evidence is
  `14 passed` using external basetemp
  `C:\Temp\PolyNexus_joint_current_audit`.
- The final task-scoped verifier passed task/memory, Ruff, compile/type,
  quality `283`, preprocessing `106`, and whitespace with exit code `0` using
  external basetemp `C:\Temp\PolyNexus_joint_route_verify`.
- The full plan now marks automated Joint report/Workbench/figure/export/
  History linkage complete. Scientific consistency/conflict semantics,
  real-data behavior, restarted-GUI review, and final release approval remain
  open.
- Task and acceptance evidence:
  `docs/agent/tasks/2026-07-27-joint-route-plan-reconciliation.md` and
  `docs/acceptance/2026-07-27-joint-route-plan-reconciliation.md`.

## SAXS real 2D detector evidence transport - 2026-07-27

- Real PAD8 EDF replay exposed a transport gap: geometry was read from the
  header for all five frames (`confidence=0.95`), and orientation evidence
  contained a sector-map detector report, but strain point/series detector
  fields were `None`.
- The minimal TDD fix now returns the existing report from
  `herman_from_sector_data` and copies it into `StrainPointResult` before the
  existing series rollup. It does not infer raw-detector mask, saturation, or
  geometry validity and does not change any threshold or publication role.
- Evidence: RED `1 failed, 11 passed`; GREEN focused `12 passed`; exact SAXS
  matrix `365 passed, 4 warnings`; structured verifier quality `283`,
  preprocessing `106`; real replay now transports five `sector_map` reports
  and retains conservative series `Unusable` reasons.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-27-saxs-real-2d-evidence-transport.md`,
  `docs/superpowers/specs/2026-07-27-saxs-real-2d-evidence-transport-design.md`,
  `docs/superpowers/plans/2026-07-27-saxs-real-2d-evidence-transport.md`.

## Qt font runtime acceptance - 2026-07-27

- Real Windows Qt diagnostics resolved `QApplication.font()` and
  `QFontInfo` to `Microsoft YaHei UI` with a 399-family database; all tested
  Chinese GUI characters had glyph coverage. The existing theme fallback
  chain is therefore present in the production runtime.
- The same diagnostic under `QT_QPA_PLATFORM=offscreen` returned zero font
  families and no glyph coverage. Offscreen square CJK placeholders are an
  environment limitation, not a reason to change the GUI font chain or the
  Matplotlib publication font.
- Task evidence is recorded in
  `docs/agent/tasks/2026-07-27-qt-font-runtime-acceptance.md` and
  `docs/acceptance/2026-07-27-qt-font-runtime-acceptance.md`.
- The task-scoped verifier passed task/memory, Ruff, compile/type, quality
  `283`, preprocessing `106`, and whitespace checks with exit code `0` using
  external basetemp `C:\Temp\PolyNexus_qt_font_runtime_verify`.
- Automated evidence is complete; restarted-GUI pixel-level review and final
  human release approval remain open.

## SAXS quality and analysis program route audit - 2026-07-27

- The route-level task card now records the automated contract acceptance
  criteria as satisfied and links the new implementation plan
  `docs/superpowers/plans/2026-07-26-saxs-quality-analysis-program.md`.
- The plan maps Stage 0 through Stage 7 to the existing SAXS task/spec/plan
  slices and preserves the conservative boundary: deterministic evidence and
  existing physical/quality gates are authoritative; AI remains
  candidate/replay/confirm-only; missing frames are never interpolated or
  fabricated.
- Current-head evidence indexed by the route audit is the exact SAXS matrix
  `364 passed, 4 warnings in 31.08s`, real SAXS walkthrough `3 passed, 12
  deselected`, and Workbench/figure profiles `29 passed`. These are automated
  evidence, not human scientific or release approval.
- Remaining gates are restarted-GUI interaction/visual review, real
  temperature/strain scientific meaning review, raw 2D detector/geometry and
  mask-propagation acceptance, and final publication approval. The older
  `2026-07-12-saxs-temperature-strain-production-cutover.md` card remains a
  historical record and is not silently rewritten by this audit.

## SAXS real Workbench acceptance current-head refresh - 2026-07-27

- Fresh current-head evidence: real SAXS walkthrough `3 passed, 12
  deselected in 53.40s`; Workbench/figure profile matrix `29 passed in 0.29s`;
  launcher diagnosis resolved `D:\PolyNexus`, package under the same root,
  branch `codex/origin-editor-usable-controls`, commit `9fa7b82`.
- Reinspection of the external real bundle preserved the conservative quality
  boundary: static quality `Trend` but Guinier/Porod/Kratky/invariant/lamellar
  `Diagnostic`; temperature four `Quantitative` plus one `Diagnostic` frame and
  `Unusable` sequence Guinier evidence; strain five `Trend` frames. Near-
  saturated strain heatmap and temperature end-of-axis truncation remain
  scientific-review signals.
- No production code, threshold, evidence level, publication role, or export
  behavior changed. Human restarted-GUI interaction and scientific release
  approval remain open.

## Full release GUI route evidence - structural/live captures - 2026-07-27

- A live `PrintWindow` capture of the existing canonical GUI process was
  obtained at normal and maximized sizes. The maximized shell shows the
  sidebar plus Data/Config/Results/Plots/History and fits its Data surface;
  the normal-size right edge remains open for human visual review.
- An offscreen capture, using the scientific-stack preload order from
  `tests/conftest.py`, constructed all five tabs and the Chart Editor from a
  restored real DSC figure. It produced one active manifest Gallery entry and
  six structural screenshots under `C:\Temp\polynexus-route-*`.
- These are not publication or visual sign-off: offscreen CJK glyphs are
  square placeholders, and live interaction was limited by the Windows lock
  screen. The release task remains in progress.
- The first docs-only verifier attempt hit 54 pytest setup errors because the
  default `D:\PolyNexus\.pytest_tmp` is an existing protected directory.
  Rerun with external basetemp
  `C:\Temp\PolyNexus_release_gui_route_verify_20260727` passed quality `283`,
  preprocessing `106`, Ruff, compile/type, task/memory, and whitespace.

## SAXS AI confirmation UI acceptance - route evidence added - 2026-07-27

- The real offscreen `MainWindow` completion route now has focused regression
  evidence for a SAXS `request_confirmation` report. The test constructs the
  real `SideTuningReportDialog`, clicks its actual enabled Apply button, and
  observes the existing `PreprocessTransactionService` enter one
  `apply_pending` SAXS transaction. The reject path performs no apply or rerun.
- TDD outcome: the new test passed immediately (`2 passed in 6.30s`), showing
  that the automated route was already implemented. No production code or
  scientific gate changed.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-27-saxs-ai-confirmation-ui-acceptance.md`,
  `docs/superpowers/specs/2026-07-27-saxs-ai-confirmation-ui-acceptance-design.md`,
  and `docs/superpowers/plans/2026-07-27-saxs-ai-confirmation-ui-acceptance.md`.
- Remaining release gates are restarted-GUI visual inspection, real-data
  scientific meaning review, and human release approval. The route remains
  subject to the existing SAXS physical/quality gates.

## SAXS condition-axis Export/History boundary audit - implementation in progress - 2026-07-27

- The cross-boundary audit added regressions for the existing nested
  `metric_evidence[*].condition_axis` in `quality_evidence.json` and History.
  Export already preserved the full axis, including diagnostic positions and
  `None` values.
- TDD RED was `1 failed, 1 passed`: History's generic `to_jsonable` converted a
  public `MetricEvidenceSummary` DTO to text instead of using `to_dict()`, so
  its axis was lost. The minimal fix is a `to_dict()`-aware normalization branch
  in `polynexus/gui/analysis_run_service.py`.
- GREEN focused matrix was `29 passed`; isolated SAXS was `362 passed, 4
  warnings` (existing Arial CJK glyph warnings). The structured task verifier
  passed quality `283`, preprocessing `106`, Ruff, compile/type baseline,
  memory/task checks, and whitespace. The explicit allowlist checkpoint is the
  checkpoint `fac9c8d` was created with the explicit allowlist; no push was
  performed and no parallel GUI/scratch files were included.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-27-saxs-condition-axis-export-history-audit.md`,
  `docs/superpowers/specs/2026-07-27-saxs-condition-axis-export-history-audit-design.md`,
  and `docs/superpowers/plans/2026-07-27-saxs-condition-axis-export-history-audit.md`.

## SAXS condition-axis Figure provenance - ready for checkpoint - 2026-07-27

- Figure/Manifest evidence projection now preserves the existing public
  `metric_evidence[*].condition_axis` mapping for both frame records and
  series records. The change is one explicit `_COMMON_EVIDENCE_FIELDS`
  allowlist entry; existing strict JSON conversion, detached copies,
  non-finite-to-`null` handling, figure roles, and orientation separation are
  unchanged.
- TDD RED was `2 failed, 23 passed, 4 warnings`; GREEN Figure/Document was
  `25 passed, 4 warnings`; the Figure/provider consumer matrix was `45 passed,
  4 warnings`; and the complete isolated SAXS matrix was `361 passed, 4
  warnings`. Task-scoped verification passed quality `282`, preprocessing
  `106`, task/memory, Ruff, compile/type, and whitespace checks.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-27-saxs-condition-axis-figure-provenance.md`,
  `docs/superpowers/specs/2026-07-27-saxs-condition-axis-figure-provenance-design.md`,
  and `docs/superpowers/plans/2026-07-27-saxs-condition-axis-figure-provenance.md`.

## SAXS condition-axis Workbench visibility - ready for checkpoint - 2026-07-27

- The SAXS Workbench now consumes existing nested
  `metric_evidence[*].condition_axis` mappings and emits advisory review text
  only for `diagnostic`/`empty` axes. It reports the metric, condition name,
  invalid/duplicate/non-monotonic counts, and bounded representative
  positions; the complete values and position arrays remain in Diagnostics.
- Clean `ordered` axes do not add risk text. The formatter does not sort source
  data, add thresholds, alter metric levels/counts, infer physical
  transitions, or apply temperature ordering semantics to strain axes.
- TDD RED was `2 failed, 12 passed, 2 errors` under the default locked temp
  path; the failures were expected missing-hint assertions and the errors were
  pre-existing `.pytest_tmp` `WinError 5` cleanup failures. Isolated GREEN was
  `16 passed`; the consumer matrix was `56 passed`; and the complete SAXS
  matrix was `359 passed, 4 warnings`. The isolated task verifier passed
  quality `282`, preprocessing `106`, task/memory, Ruff, compile/type, and
  whitespace checks.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-27-saxs-condition-axis-workbench-visibility.md`,
  `docs/superpowers/specs/2026-07-27-saxs-condition-axis-workbench-visibility-design.md`,
  and `docs/superpowers/plans/2026-07-27-saxs-condition-axis-workbench-visibility.md`.

## SAXS temperature condition-axis evidence - ready for checkpoint - 2026-07-27

- Temperature-series `MetricEvidenceSummary` records a frozen, strict-JSON
  `condition_axis` for existing Porod, Kratky, invariant, lamellar, and
  Guinier summaries. It preserves values by frame position, marks invalid
  values as `null`, and reports duplicate/non-monotonic/mismatched axes as
  diagnostic provenance. Existing metric levels, counts, physical gates,
  interpolation/repair policy, AI behavior, and publication roles are
  unchanged.
- Temperature aggregation passes the existing sorted `result.temperatures`
  as `temperature_C`; existing original-frame `source_index` mapping remains
  separate and unchanged. Strain axes are intentionally out of scope.
- TDD RED was `4 failed, 13 passed`; focused GREEN was `17 passed`; the
  consumer matrix was `41 passed`; and the isolated full SAXS matrix was
  `356 passed, 4 warnings`. Task-scoped verification with an isolated
  basetemp passed quality `282`, preprocessing `106`, task/memory, Ruff,
  compile/type, and whitespace checks.
- The prescribed verifier without an isolated basetemp hit `229 passed, 53
  errors`, all due to the pre-existing `.pytest_tmp` cleanup
  `PermissionError: [WinError 5]`. A fresh isolated full/boundary verifier
  exited `0`, reported selected checks passed, and passed the boundary audit;
  its middle full-pytest count was truncated by the tool output and is not
  inferred from historical evidence.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-27-saxs-temperature-condition-axis-evidence.md`,
  `docs/superpowers/specs/2026-07-27-saxs-temperature-condition-axis-evidence-design.md`,
  and `docs/superpowers/plans/2026-07-27-saxs-temperature-condition-axis-evidence.md`.

## SAXS series metric position evidence - checkpoint bd7c3fd - 2026-07-27

- Existing series `MetricEvidenceSummary` now records deterministic evidence,
  missing, diagnostic, unusable, and invalid-level frame positions. A valid
  optional source-index list is preserved without truncation; mismatched lists
  are discarded with `series_metric_source_index_mismatch`.
- Temperature metric summaries pass the existing sorted point order and
  original `source_index` values. No numerical method, physical threshold,
  interpolation, repair, AI action, or publication role changed.
- TDD RED was `4 failed, 10 passed`; focused GREEN was `38 passed, 2
  warnings`; the isolated complete SAXS matrix was `353 passed, 6 warnings`.
  Direct quality/preprocessing equivalents passed `282`/`106`; allowlist Ruff,
  compile, and whitespace checks passed.
- The structured `--changed --types` verifier was blocked by pre-existing Ruff
  findings in unrelated modified files (`config.py`, `saxs_anisotropy.py`, and
  other shared-worktree paths); a non-changed verifier attempt hit the known
  Windows `pytest` child launch `WinError 5`. No unrelated file was repaired.
- Two initial `scripts/auto_commit.py` attempts were blocked by transient
  `D:/PolyNexus/.git/index.lock` permission denied; after the shared Git
  process state cleared, the exact allowlist checkpoint `bd7c3fd` was created.
  No push or unrelated cleanup was performed.
- Task/spec/plan: `docs/agent/tasks/2026-07-27-saxs-series-metric-position-evidence.md`,
  `docs/superpowers/specs/2026-07-27-saxs-series-metric-position-evidence-design.md`,
  and `docs/superpowers/plans/2026-07-27-saxs-series-metric-position-evidence.md`.

## SAXS strain Herman orientation table - implementation ready for checkpoint - 2026-07-27

- The existing 2D preprocessing `sector_data` is now retained per loaded frame,
  passed through both SAXS strain entry points, and used by the existing
  `analyze_strain_series(sector_data_list=...)` contract. Per-frame
  `StrainPointResult.f_herman` is published as `_batch_params["f_Herman"]`,
  while missing 1D/sector frames remain `None` and render as unavailable.
- No Herman algorithm, detector geometry, orientation threshold, GUI
  recalculation, or generic 1D review behavior changed. The existing GUI table
  field is reused.
- Verification evidence: focused core/table matrix `66 passed`; complete SAXS
  matrix `341 passed, 4 warnings`; structured verifier passed with external
  basetemp, including quality `282`, preprocessing `106`, Ruff, compile/type
  baseline, memory, task-card, and whitespace checks.
- The repository `.pytest_tmp` lock caused setup errors only when the verifier
  used its default temp path; the authoritative rerun used
  `C:\Temp\PolyNexus_saxs_herman_verify` and passed. The locked directory was
  left untouched.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-27-saxs-strain-herman-table.md`,
  `docs/superpowers/specs/2026-07-27-saxs-strain-herman-table-design.md`, and
  `docs/superpowers/plans/2026-07-27-saxs-strain-herman-table.md`.

## Full software release audit - in progress - 2026-07-27

- A dedicated audit task/plan/acceptance note now separates automated evidence
  from restarted-GUI and scientific-review gates:
  `docs/agent/tasks/2026-07-27-full-software-release-audit.md`,
  `docs/superpowers/plans/2026-07-27-full-software-release-audit.md`, and
  `docs/acceptance/2026-07-27-full-software-release-audit.md`.
- Fresh WAXS publication/provider/workbench recheck is `30 passed` with an
  isolated basetemp. The prior full-suite WAXS failure remains a historical
  full-run limitation until a fresh full verifier completes.
- Fresh cross-technique AI-off/failure/fallback contract matrix is `25 passed`;
  it does not prove model quality, calibration, or scientific approval.
- Fresh real published-run walkthrough shards passed all 15 single-technique
  cases: DSC `3` (11 existing warnings), WAXS `3`, SAXS `3`, IR `2`, and NMR
  `4`. Separate lifecycle closures passed DSC `3`, WAXS `3`, IR `3`, NMR `4`,
  and Joint `1`; solid-state NMR C assignment remains provisional.
- GUI shell/workbench/gallery/editor route contracts add `58 passed`; pixel-level
  restarted-GUI review remains a human gate.
- A temporary real-result GUI capture passed `1` case and produced Results,
  Gallery, History, and Editor screenshots with one manifest entry. Offscreen
  CJK glyph boxes mean this is structural evidence only; live-font review stays
  open.
- IR mapping/ROI plus lifecycle regression is `11 passed`; NMR/Joint provenance
  plus lifecycle regression is `4 passed`. These are structural/provenance
  contracts only; vendor semantics, assignment-limited NMR C, and Joint
  scientific conflicts remain human gates.
- The combined real/lifecycle command exceeded the 180-second tool window
  without a summary and was explicitly terminated; it is recorded as a
  bounded timeout, not a pass. Canonical GUI default-shell screenshot evidence
  is in the acceptance note; full restarted-GUI walkthrough and final human
  release approval remain open.
- Fresh current-head full verification retry at `2af4baf` passed: `2790 passed,
  10 warnings` in `1454.97s` (`24:14`); selected compile/quality (`283`),
  preprocessing (`106`), Ruff/type/whitespace, and boundary checks all passed.
  The first same-turn attempt had one transient focused maintenance-cleanup
  failure and was rerun; it is not treated as the final result. The GUI
  responsive-shell task is checkpointed as `83083bc`, and a fresh canonical
  launcher diagnose resolved that commit.
  Remaining work is all-route live GUI review, IR vendor mapping/ROI semantics,
  assignment-limited NMR/Joint scientific review, and final human release
  approval.

## SAXS AI confirmed-rerun safety - local checkpoint - 2026-07-27

- The current slice adds a core SAXS adapter for strict JSON-safe confirmed
  rerun evidence and candidate/hash/guard identity validation. It reuses the
  existing static, temperature, and strain frame/series evidence; it does not
  add thresholds, interpolation, frame repair, or automatic rescue.
- The generic preprocessing transaction now keeps original config/result until
  post-rerun gates pass, persists experience only after acceptance, records a
  detached audit, and rolls back on missing/Diagnostic/Unusable evidence,
  physical failure, config drift, or rerun exception. The GUI resolves the
  generic worker result to the existing SAXS temperature/strain DTOs before
  gating, and export carries the audit under `quality_evidence.json` AI
  provenance.
- Fresh evidence: RED collection failure due to missing adapter; focused GREEN
  `33 passed`; complete SAXS matrix `338 passed, 4 warnings`; task-scoped
  verifier passed task/memory, Ruff, compile/type baseline, quality `282`,
  preprocessing `106`, and whitespace checks. Fresh full verification reached
  `2763 passed, 1 failed, 10 warnings` after about 25:42; the unrelated
  `tests/test_waxs_publication_cutover.py::test_waxs_engine_publishes_manifest_backed_assets`
  failure stopped the chain before boundary audit. No full/boundary pass is
  claimed and no child processes remain.
- Task/plan/spec:
  `docs/agent/tasks/2026-07-27-saxs-ai-confirmed-rerun-safety.md`,
  `docs/superpowers/plans/2026-07-27-saxs-ai-confirmed-rerun-safety.md`,
  `docs/superpowers/specs/2026-07-27-saxs-ai-confirmed-rerun-safety-design.md`.
- The explicit allowlist checkpoint was created locally; this documentation-only
  amend records the final state. No push, merge, or deploy was performed.
- A later doc-only verifier rerun without the dedicated basetemp hit the
  pre-existing `.pytest_tmp` lock (`229 passed, 53 setup errors`); the earlier
  dedicated task-scoped code verification remains the authoritative code
  evidence, and the lock was not altered.

## SAXS Figure/Manifest evidence binding - local checkpoint - 2026-07-27

- The new provider-side `figure_evidence` projection binds existing frame and
  completed-series quality evidence to `FigureDefinition.recipe["evidence"]`
  under `quality_provenance`. It is detached and strict JSON-safe, maps
  non-finite values to `null`, preserves existing role/omission evidence, and
  references the authoritative `quality_evidence.json`.
- Static, temperature, strain, and compatibility figure providers now attach
  the projection. Temperature retains provider frame indices and matched
  existing `source_index` values; sequence evidence stays at series level.
  Strain keeps detector/orientation evidence separate from 1D metric evidence.
  No analysis, threshold, role, interpolation, repair, or AI rescue behavior
  changed.
- TDD evidence: focused Figure/Manifest/provider matrix `33 passed`; complete
  SAXS matrix `317 passed, 4 warnings` (existing Arial CJK glyph warnings).
  Task-scoped verification passed task/memory, Ruff, compile/type baseline,
  quality `282`, preprocessing `106`, and whitespace checks. `git diff --check`
  passed.
- Fresh full/boundary verification with an isolated basetemp timed out with
  exit `124` after about 1204 seconds, without a test-failure summary. The
  timeout left the verifier and pytest child processes alive; they were
  identified as this run and terminated, then a post-stop audit found no
  remaining verifier or pytest process. No full/boundary pass is claimed. The
  explicit allowlist checkpoint is being recorded locally with no push.
- Task/spec/plan: `docs/agent/tasks/2026-07-27-saxs-figure-evidence-binding.md`,
  `docs/superpowers/specs/2026-07-27-saxs-figure-evidence-binding-design.md`,
  and `docs/superpowers/plans/2026-07-27-saxs-figure-evidence-binding.md`.

## SAXS temperature Guinier sequence evidence transport - checkpoint b7bad1c 2026-07-27

- The existing observational `build_guinier_sequence_evidence()` contract now
  carries optional `frame_source_indices` without changing its level logic,
  q-based frame evidence, or interpolation/repair policy. A mismatched source
  list remains explicitly Diagnostic with a reason code.
- Temperature analysis passes the existing sorted point order plus each
  `TemperaturePointResult.source_index`; the DataFrame exposes `source_index`.
  Temperature `get_parameters()` and the existing quality-copy path now retain
  detailed sequence evidence. Export already had the pass-through field, and a
  regression locks its source mapping.
- Workbench review now shows sequence level, valid/total counts,
  missing/diagnostic counts, source indices, and reason codes as advisory
  diagnostic evidence. It explicitly asks users to confirm frame-level SAXS
  physical indicators and quality gates; it does not enable rescue or promote
  evidence.
- TDD evidence: RED was `5 failed, 51 passed`; GREEN/focused post-change was
  `56 passed`. Complete SAXS matrix was `311 passed, 4 warnings`. Isolated
  task-scoped verification passed task/memory, Ruff, compile/type baseline,
  quality `282`, preprocessing `106`, and whitespace checks.
- A fresh full/boundary verifier was started with an isolated basetemp but
  exceeded the tool's `124` second window while still in the
  `verify.py -> quality_gate.py --all-tests -> pytest -q` chain. It was
  terminated without a final count, so no full/boundary pass is claimed for
  this modification. A process audit after termination found no remaining
  verifier or pytest process.
- Task/spec/plan: `docs/agent/tasks/2026-07-27-saxs-temperature-guinier-sequence-transport.md`,
  `docs/superpowers/specs/2026-07-27-saxs-temperature-guinier-sequence-evidence-design.md`,
  and `docs/superpowers/plans/2026-07-27-saxs-temperature-guinier-sequence-evidence.md`.
- Checkpoint `b7bad1c` contains the explicit implementation allowlist. Fresh
  revalidation on 2026-07-27 passed the task-scoped verifier with quality
  `282` and preprocessing `106`, the exact SAXS file matrix with `311 passed,
  4 warnings`, and `git diff --check`. Real-data scientific sign-off, AI
  execution/calibration, detector/geometry acceptance, and final release
  review remain open.

## SAXS aligned-batch evidence mode resilience - implementation checkpoint 2026-07-27

- Generic aligned `_batch_results` serialization now preserves existing
  per-frame evidence even when `cfg.experiment_type` carries a stale or
  non-static label and the dedicated temperature/strain result is absent.
  The shared scope helper emits `static_batch` only for static mode and
  `aligned_batch` for temperature/cooling/heating/isothermal/strain labels.
- Export uses the same scope contract. Workbench review text says
  “Aligned batch quality” and asks for missing/diagnostic-frame review; it does
  not describe the payload as a static batch or a series trend.
- TDD evidence recorded by the implementation pass: the deterministic scope
  regression was RED in parameters, Export, and Workbench, then GREEN; the
  adjacent matrix passed `51` tests and the complete SAXS matrix passed `305`
  tests with `4` warnings. A separate independent full/boundary verifier
  rerun reported `2707 passed, 10 warnings`, quality `282`, preprocessing
  `106`, and a passing boundary audit.
- Fresh task-scoped verification with an isolated basetemp passed quality
  `282`, preprocessing `106`, changed Ruff/compile/type, task/memory, and
  whitespace checks; the focused SAXS matrix passed `37`. The default verifier
  path remains environmentally blocked by the pre-existing `.pytest_tmp`
  lock (`229 passed, 53 setup errors`). An independent full/boundary rerun
  reported `2707 passed, 10 warnings` and a passing boundary audit.
- Checkpoint `5984bd3` has been created and committed with the explicit
  allowlist for this atomic slice. Scientific review of real
  temperature/strain meaning, restarted-GUI
  review, AI model calls/candidate reruns, expert calibration, and raw
  detector/geometry acceptance remain open.
- Task card: `docs/agent/tasks/2026-07-27-saxs-batch-evidence-mode-resilience.md`.

## SAXS static 1D evidence - implementation checkpoint 2026-07-27

- Static single-frame `get_parameters()` now transports existing
  `data_quality_report`, `guinier_evidence`, and `metric_evidence` mappings
  without mutating the `SAXSResult`.
- Static multi-file parameters carry aligned per-frame evidence and preserve
  missing/failed rows as missing. The top-level summary reuses the existing
  conservative metric aggregation and declares `metric_evidence_scope` as
  `static_batch`; it is not a temperature or strain trend.
- Workbench review text uses batch-quality wording while Diagnostics retains
  nested evidence. Existing History persistence carries the same payload.
- Static Export now includes the summary and only analyzable frame snapshots in
  `quality_evidence.json`; strict JSON sanitization remains unchanged.
- Evidence: focused matrix `77 passed`, complete SAXS matrix `290 passed, 4
  existing font warnings`, task verifier quality/preprocessing gates `282`/`106`,
  and `git diff --check` passed. Atomic checkpoint is pending in this working
  tree; scientific/data-contract review remains open.
- Task card: `docs/agent/tasks/2026-07-27-saxs-static-1d-evidence.md`.

## SAXS temperature Guinier metric evidence - implementation checkpoint 2026-07-27

- Existing `TemperaturePointResult.guinier_evidence["metric"]` is now copied
  into a derived per-frame mapping and included as
  `TempSeriesResult.metric_evidence["guinier"]` through the existing immutable
  series builder. Missing or failed frames remain missing; the original frame
  and sequence evidence are not mutated.
- The Workbench labels the common `guinier` key as `Rg` while retaining the
  existing level, coverage, counts, and reason-code display contract. History,
  Export provenance, and figure roles use their existing pass-through paths.
- TDD evidence: RED observed for missing common Guinier summaries and for the
  missing `Rg` review label; focused implementation evidence is `7 passed` and
  the consumer matrix is `22 passed` in isolated basetemps.
- The task-scoped verifier passes with quality `282`, preprocessing `106`,
  Ruff, compile/type, memory, and whitespace checks when an isolated basetemp
  is supplied. The repository's configured `.pytest_tmp` is pre-existing and
  locked, so the default verifier path reports WinError 5 during pytest cleanup.
- Final full SAXS matrix is `283 passed, 4 existing font glyph warnings`; the
  task verifier and `git diff --check` pass with an isolated basetemp. Atomic
  checkpoint `3324b2e` was created with the explicit allowlist. Real-data
  scientific review and later Porod/Kratky/invariant/lamellar vertical routes
  remain open.

## SAXS Workbench series evidence visibility - checkpoint 2026-07-27

- Temperature and strain `SAXSEngine.get_parameters()` now transport a deep
  copy of the existing series `metric_evidence` summaries. The transport does
  not rebuild evidence or mutate series/frame data, and the existing History
  persistence path retains the mapping in run parameters.
- `build_saxs_results_presentation()` now formats the existing level, coverage,
  downgrade counts, and up to three reason codes into the Workbench's existing
  review channels. Complete series summaries remain Trend-capped; mixed or
  incomplete summaries become visible review risks. Diagnostics still exposes
  the full nested JSON and figure routing/Export contracts are unchanged.
- Evidence: focused Workbench/History/Figure/Export matrix `24 passed`; full
  SAXS matrix `282 passed, 4 existing font warnings`; task-scoped verifier
  passed with quality `282`, preprocessing `106`, changed Ruff/compile,
  memory check, and whitespace check.
- A post-checkpoint review identified and the follow-up fix now preserves
  malformed/non-mapping evidence values for Diagnostics instead of filtering
  them during parameter transport; review reported no Critical or Important
  findings.
- The wrapper's module-scoped Ruff compatibility annotation is limited to
  pre-existing `F401`, `E741`, and `F841` diagnostics caused by retained public
  imports and legacy intensity names. AI execution, publication promotion,
  and human scientific review remain separate gates.
- Next action is to continue the SAXS vertical route at the next unconsumed
  boundary; no continuous autonomous runner or release sign-off is implied.

## GUI responsive shell - checkpointed 2026-07-27

- Restarted canonical GUI inspection found right-edge clipping caused by
  window-width-only responsive thresholds, long header minimum sizes, and the
  History action toolbar becoming the minimum width of the full tab set.
- The shell now measures actual content width, collapses optional metrics and
  top-bar shortcuts while retaining the task card/menu routes, makes header
  labels compressible, and puts History actions in an internal horizontal
  scroll container.
- Focused shell/streamlining regression is `18 passed`. Full deferred-startup
  Qt grabs show default `viewport/content=1036/1036` and maximized
  `1486/1486`; the task card remains geometrically complete. Acceptance is
  recorded in `docs/acceptance/2026-07-27-gui-responsive-shell.md`.
- Fresh task-scoped verification passed task/memory, Ruff, compile/type,
  quality `282`, preprocessing `106`, and whitespace checks with an isolated
  basetemp. Fresh full/boundary verification passed `2773` tests with `10`
  existing warnings in `1451.67s`; the boundary audit passed as well. The
  older order-sensitive full-suite failure is retained as historical evidence
  only. Real-data science, all-mode live GUI walkthrough, and final release
  approval remain open.

## SAXS series metric evidence rollup - checkpointed 2026-07-27

- Added immutable `MetricEvidenceSummary` and
  `build_series_metric_evidence` in the SAXS quality contract layer. The
  builder summarizes only existing per-frame mappings, preserves missing and
  invalid frames, caps complete series at `Trend`, and never mutates q/I or
  frame evidence.
- Temperature and strain series now expose `metric_evidence` summaries while
  retaining all existing frame fields, numeric arrays, DataFrame rows, and
  Export quality provenance. Focused contract/propagation/export evidence is
  `11 passed`; the full SAXS matrix is `274 passed, 4 existing warnings`.
- Explicit task-scoped revalidation passes task/memory checks, changed Ruff,
  compile/type baseline, quality `282`, preprocessing `106`, and whitespace.
  The focused series/mode/export matrix is `14 passed`; the current complete
  SAXS matrix is `317 passed, 4 existing Arial CJK glyph warnings`; and
  `git diff --check` passes.
- The code was already present in the current checkpoint history; this
  documentation checkpoint closes the task card and records the fresh
  verification. Full/boundary release verification and human scientific
  review remain separate gates.

## SAXS candidate replay and calibration audit - checkpointed 2026-07-27

- Every bounded SAXS preprocessing candidate now produces a JSON-safe,
  mode-aware replay row for static, temperature, and strain paths. Rows carry
  candidate identity, config hashes, run status, existing evidence/decision,
  bounded source context, and explicit `original_preserved`/
  `apply_performed=false` flags; export preserves them as audit-only
  `quality_evidence.json` provenance.
- Calibration validation now blocks incomplete SAXS expert-case contracts,
  low evidence coverage, hard-guard false accepts, and insufficient expert
  agreement. It does not enable tiered-auto or change physical thresholds.
- Focused replay/orchestrator/export/calibration evidence is `31 passed`;
  structured gates are quality `282` and preprocessing `106`. Current-HEAD
  full/boundary verification passed `2671` tests with `10` known warnings and
  a passing boundary audit.
- External model calls, confirmed real candidate reruns, expert-labelled
  promotion, user confirmation UI, restarted-GUI review, and human scientific
  publication approval remain open.

## SAXS AI prompt protection contract - verification-ready 2026-07-27

- The preprocessing prompt now renders the active policy's protected-feature
  list and explicitly requires every listed feature for SAXS. The core
  validator remains authoritative and fail-closed.
- Prompt regressions pass (`20`); the touched prompt-builder file is now Ruff
  clean after seven mechanical pre-existing lint blockers were removed.

## SAXS AI orchestrator handoff - verification-ready 2026-07-27

- The shared preprocessing orchestrator now validates SAXS intents through the
  SAXS bridge before candidate generation, requiring all protected physical
  features.
- Valid runs carry the exact generated candidates in a JSON-safe
  `saxs_ai_rescue_plan` and wrap the shared evidence decision in
  `saxs_ai_rescue_decision`; the source engine carries both for existing export
  audit. Shadow remains `keep_original` with `apply_allowed=false`.
- Focused bridge/handoff tests pass (`8`); SAXS/orchestrator/preprocess matrix
  passes (`383`, with four existing font warnings). Model provider calls,
  user-confirmed real reruns, calibration, and scientific publication review
  remain separate gates.
- A fresh full/boundary verifier attempt timed out after 20 minutes with exit
  `124` before producing a summary; focused and structured verification remain
  the current evidence. The orphaned child processes were identified as that
  run and terminated.

## SAXS real data and Workbench acceptance - automated slice 2026-07-27

- Real static, temperature, and strain lifecycle replay passed (`3 passed,
  12 deselected`) without writing to the source fixture directories.
- External real exports all returned `ok` and registered `quality_evidence.json`
  in their manifests. Mode-scoped evidence was preserved; the temperature
  validation error remained a visible gate.
- SAXS Workbench contracts passed (`9 passed`). Launcher diagnostics resolved
  `D:\PolyNexus` and commit `41588a0`.
- Human restarted-GUI visual review and scientific sign-off remain open. See
  task `docs/agent/tasks/2026-07-27-saxs-real-workbench-acceptance.md` and
  acceptance note `docs/acceptance/2026-07-27-saxs-real-workbench-acceptance.md`.

## SAXS quality export provenance - verification-ready 2026-07-27

- Export bundles now write `quality_evidence.json` and register it in the
  bundle manifest. The snapshot preserves static/temperature/strain quality,
  sequence evidence/candidates, 2D evidence, and optional AI plan/decision as
  audit-only JSON; it never applies candidates or changes publication roles.
- Verification evidence: export/provider slice `27 passed, 4 warnings`; full
  SAXS matrix `260 passed, 4 warnings`. Restarted GUI visual review, real-data
  science sign-off, and final release policy remain open.

## SAXS AI rescue bridge - checkpointed 2026-07-27

- Added `saxs_ai_rescue.py` as a strict bridge to the existing preprocessing
  contracts. AI intent payloads must be SAXS and protect weak peaks, area,
  Guinier, beamstop boundaries, peak position/width, and physical parameters.
- Candidate plans are candidate-only and preserve the original configuration;
  decisions reuse the shared evidence hard guards. Default shadow keeps the
  original, confirm-only requests confirmation, and calibrated tiered-auto is
  the only state that can expose `apply_allowed` after all guards pass.
- Verification evidence: focused `4 passed`, preprocessing integration `48
  passed`, full SAXS `259 passed, 4 warnings`. Model calls, candidate execution,
  user confirmation UI, calibration and publication remain open.
- Code checkpoint: `2eb3c49`; the bridge is contract-only and does not apply
  candidate configurations.

## SAXS sequence rescue - checkpointed 2026-07-27

- Added an evidence-only adapter around the existing temperature `lc` path:
  non-primary deterministic alternatives become JSON-safe `RescueCandidate`
  records with frame/axis/original/proposed values and
  `preserve_missing_frames=True`.
- Added all-gates `validate_sequence_rescue_candidate`; hard, physical, data
  preservation and sequence gates are explicit, and one failed gate rejects
  regardless of soft score. `TempSeriesResult` retains candidate dictionaries
  and exposes candidate IDs in its DataFrame without rewriting legacy values.
- Verification evidence: focused `8 passed`; temperature/Guinier/mode
  propagation `26 passed`; full SAXS matrix `255 passed, 4 warnings`; task
  verifier quality `282`/preprocessing `103`. Candidate reanalysis, calibrated
  phase-transition thresholds, AI shadow/confirm, and publication remain open.

## Full boundary/release verifier after SAXS orientation checkpoint - passed 2026-07-27

- Re-ran `python scripts/verify.py --changed --types --full --boundary` on
  the current HEAD after the SAXS detector/orientation checkpoint: **2647
  passed, 10 warnings in 1389.67s (23:09)**, with a passing boundary audit.
- The warnings are existing Qt tight-layout, DSC polyfit-conditioning, and
  SAXS CJK glyph warnings. This closes the current automated regression
  evidence only; restarted-GUI visual review, human scientific sign-off, IR
  mapping semantics, and final release policy remain open.

## SAXS 2D detector/orientation evidence - checkpointed 2026-07-27

- Added strict JSON-safe `DetectorQualityReport` and conservative orientation
  `MetricEvidence` around the existing anisotropy output. Explicit masks,
  saturation values, source kind, beam-center availability, coverage, and
  invalid-pixel counts are preserved; missing metadata never becomes a guessed
  raw-detector claim.
- `AnisotropyResult` keeps all legacy numeric fields and now exposes optional
  detector/orientation dictionaries, including the empty-input path. Unknown
  applicability is at most `Diagnostic`; complete supported evidence is capped
  at `Trend`.
- Verification evidence: focused `6 passed`; full SAXS matrix `250 passed, 4
  warnings`; structured verifier quality `282`/preprocessing `103`. Real raw
  detector geometry/mask propagation, orientation sequence semantics, figure
  publication, and scientific review remain separate gates.

## SAXS 2D evidence mode propagation - verification-ready 2026-07-27

- The shared SAXS quality transport now deep-copies detector and orientation
  evidence alongside existing 1D fields. Static batches aggregate supplied
  reports without creating a temperature/strain axis; temperature rows align
  evidence by `source_index`; strain rows remain positional.
- Mode summaries preserve coverage, missing counts, source reason codes, and
  detector source kinds. No summary is emitted when no 2D evidence is supplied.
  Orientation remains a separate Diagnostics payload and is not added to the
  generic 1D metric review text.
- Workbench Diagnostics, History persistence, and `quality_evidence.json`
  retain mode/frame evidence. No raw-detector reader, new anisotropy algorithm,
  AI apply, or scientific threshold was introduced.
- Verification evidence: new propagation file `11 passed`; focused 2D/mode/
  parameter/Workbench/Export matrix `53 passed`; full SAXS matrix `301 passed,
  4 warnings`; structured verifier quality `282`/preprocessing `106`.
- Task card: `docs/agent/tasks/2026-07-27-saxs-2d-evidence-propagation.md`.
  The final atomic checkpoint is created in this task's allowlist; real
  detector/geometry and human scientific review remain separate.

## SAXS mode evidence propagation Stage 4 - checkpointing 2026-07-27

- Temperature and strain point DTOs now propagate frame-local
  `metric_evidence` and `data_quality_report` from successful `SAXSResult`
  frames. Failed core frames remain `None`; no neighbor evidence is copied and
  frame count/order remain unchanged. Both DataFrames expose a compact
  `Metric_evidence_levels` column.
- Temperature keeps its existing Guinier sequence evidence; strain does not
  create temperature sequence state. Mode-specific Q*/phase/void/orientation
  fields remain separate.
- Verification evidence: mode propagation plus existing temperature/strain
  regressions `26 passed`; exact SAXS matrix `244 passed, 4 warnings`;
  structured verifier quality `282`/preprocessing `103`.
- Task card: `docs/agent/tasks/2026-07-27-saxs-mode-evidence-propagation.md`.
  Next action is the atomic checkpoint, then 2D detector/orientation quality
  propagation remains a separate stage.

## SAXS 1D method evidence Stage 3 - verification-ready 2026-07-27

- Existing Porod, Kratky, invariant (`Q*`), and lamellar outputs now have
  conservative read-only `MetricEvidence` builders. `SAXSResult` retains the
  legacy payloads and adds JSON-safe `metric_evidence` entries for all four
  methods; builder failures become diagnostic evidence without dropping the
  legacy result.
- Method evidence uses existing data-quality checks and explicit applicability;
  it is capped at `Trend`. Porod slope deviation, Kratky peak evidence,
  beamstop/invariant state, and lamellar missing/range fields are recorded as
  evidence, not new unreviewed hard cutoffs.
- Evidence: builder focused `5 passed`; combined method/Guinier/temperature/
  physical/helper/result matrix `34 passed`; exact SAXS file matrix `242
  passed, 4 warnings`; structured verifier quality `282`/preprocessing `103`.
- Task card: `docs/agent/tasks/2026-07-27-saxs-1d-method-evidence.md`. Next
  action is the atomic checkpoint, then propagation to temperature/strain and
  Results Workbench remains a separate boundary.

## Real published-run walkthrough replay - verified 2026-07-27

- Replayed `tests/test_real_published_run_walkthrough.py` on the current
  branch with an external basetemp: **15 passed in 338.23s**, with 11 existing
  warnings (DSC polyfit conditioning and missing CJK glyphs).
- The replay covers SAXS static/temperature/strain, DSC standard/isothermal/
  non-isothermal, WAXS static/temperature/strain/2D, IR standard/
  temperature-2D, and NMR liquid/solid H/C. It preserves the shared run ID
  through Manifest/Gallery, Editor working/published revisions, export
  provenance, and History restore.
- This strengthens automated real-lifecycle evidence only. Diagnostic-only or
  validation-error results remain in their declared roles; restarted-GUI
  visual review, human scientific sign-off, IR mapping semantics, and final
  release policy remain open.

## SAXS temperature Guinier sequence evidence - checkpointed 2026-07-27

- Stage 2 adds immutable `GuinierSequenceEvidence` and the pure
  `build_guinier_sequence_evidence` builder. It preserves missing/diagnostic
  frame positions, invalid and duplicate temperature positions, and failed
  frame evidence without interpolation, deletion, or `Rg` rewriting.
- Sequence classification is capped at `Trend`; empty sequences are
  `Unusable`, insufficient or defective sequences are `Diagnostic`, and
  isolated continuity breaks remain diagnostic evidence rather than an
  automatic downgrade or phase-change decision.
- `TempSeriesResult` now carries the strict JSON-safe sequence summary and
  compatible `Rg_sequence_level`/`Rg_sequence_reason_codes` table columns.
- Verification evidence: focused Guinier/temperature tests `11 passed`; full
  `tests/test_saxs_*.py` matrix `237 passed, 4 warnings`; structured verifier
  passed with quality gate `282` and preprocessing gate `103`. The existing
  Arial CJK glyph warnings remain limited to SAXS figure layout.
- The checkpoint uses the explicit task allowlist in
  `docs/agent/tasks/2026-07-27-saxs-guinier-sequence-evidence.md`. Real
  experimental-data thresholds, phase-change semantics, AI shadow/rescue, and
  human scientific/GUI acceptance remain outside this stage.

## SAXS temperature Guinier evidence Stage 1 - checkpointed 2026-07-27

- Existing deterministic Guinier output now has a separate evidence builder
  with R², slope uncertainty, Rg uncertainty, explicit applicability, and the
  hard `qRg < 1.3` gate. `SAXSResult` and each temperature point retain the
  data-quality report, evidence payload, Rg, level, and reason codes.
- Focused evidence passes: Guinier/temperature propagation `24 passed`; the
  complete SAXS test matrix passes `227 passed` with four existing Matplotlib
  font warnings; quality gate `282 passed`; preprocessing gate `103 passed`.
  The structured verifier also passes. The legacy `core.py`/
  `saxs_temperature.py` Ruff baseline findings remain separately documented and
  are not treated as new scientific regressions.
- Stage task card: `docs/agent/tasks/2026-07-27-saxs-temperature-guinier-evidence.md`.
  Code checkpoint: `17dcb0b`. Next action is to add sequence-level Guinier
  trend/continuity gates without fabricating missing temperature frames.

## SAXS temperature Guinier evidence Stage 1 - fresh verification 2026-07-27

- Existing single-frame Guinier outputs now produce strict-JSON
  `GuinierEvidence` with fit statistics, slope/Rg uncertainty, explicit
  applicability, `qRg < 1.3`, and data-quality gates. `SAXSResult` carries the
  quality/evidence payload, and `TemperaturePointResult` preserves each
  frame's own evidence without interpolating failed frames.
- The metric provenance chain now retains `processed_data_ref` when no raw
  source ID is available. This is covered by a focused regression.
- Focused evidence: Guinier/temperature/quality `18 passed`; extended SAXS
  temperature/physical-helper matrix `36 passed`; full SAXS file matrix
  `228 passed, 4 warnings` with external basetemp.
- Structured verification passed: quality gate `282 passed`, preprocessing
  gate `103 passed`, Ruff/compile/type/whitespace checks passed. The default
  `.pytest_tmp` cleanup lock remains a Windows environment limitation; all
  authoritative reruns use an external basetemp.
- The main Stage 1 implementation checkpoint is `17dcb0b`; this fresh rerun
  additionally closes the changed-file Ruff baseline for the touched core
  boundary. Sequence-level trend classification, rescue/AI behavior,
  publication roles, and real scientific/GUI acceptance remain separate
  follow-up boundaries.

## SAXS quality contracts Stage 0 - in progress 2026-07-27

- The first typed quality/evidence contracts are present in
  `polynexus/core/saxs_engine/saxs_quality_contracts.py` with seven focused
  regressions and in-memory fault fixtures in `tests/test_saxs_quality_contracts.py`
  and `tests/fixtures/saxs_quality_cases.py`.
- The contract layer is non-mutating and strict-JSON serializable; it records
  data defects, metric evidence, and rescue validation state without changing
  SAXS calculations or publication roles.
- Focused evidence currently passes: contract `7 passed`, SAXS regression `37
  passed`, quality gate `282 passed`, and preprocessing gate `103 passed`;
  scoped Ruff is clean. The structured
  checkpoint is ready under
  `docs/agent/tasks/2026-07-27-saxs-quality-contracts-stage0.md`.
- Next action: wire the contract into the temperature 1D Guinier evidence path
  only after a separate Stage 1 task card and physical acceptance tests exist.

## Complete 2D publication performance - updated 2026-07-26

- WAXS strain publication image grids now use vectorized, bounded 256×256
  snapshots while raw detector arrays remain available to analysis. IR
  temperature-2D publication skips duplicate generic per-frame figures and
  caps correlation snapshots at 420×420; full analysis matrices are retained
  in the result object.
- Focused provider/document/renderer matrix: `23 passed`; focused IR
  provider/temperature/lifecycle matrix: `20 passed`.
- The complete real 2D shared-lifecycle walkthrough passed `2` cases in
  `101.39s`; the expanded real published-run matrix passed 15 cases in
  historical `276.15s` record, including SAXS temperature/strain and DSC
  isothermal/non-isothermal. The
  non-isothermal fixture uses its existing SI conversion entry and the SAXS
  strain fixture uses a diagnostic entry; both roles remain unchanged.
  Evidence and external output roots are recorded
  in `docs/acceptance/2026-07-26-real-published-run-audit.md`.
- Review follow-up now keeps generic IR frame figures when an incomplete
  temperature-2D payload produces no valid series definitions, and adds
  regression coverage for fallback availability, raw WAXS array preservation,
  and correlation snapshot value preservation.
- Remaining gates are restarted canonical-GUI visual review, publication-role
  review, IR mapping/ROI vendor semantics, and scientific sign-off; the
  performance fix does not promote diagnostic or warning results to Main.
- Review follow-up for the real published-run matrix now asserts the SAXS
  temperature/strain Manifest ID namespaces and exact role sets (`si` plus
  `diagnostic` for temperature; `diagnostic` only for strain). The matrix
  remains 15 cases in `276.15s`; the SAXS role slice passed 2 cases in
  `31.78s`.

## Full-software audit and verifier unblock - updated 2026-07-26

- MainWindow's intentional dynamic compatibility exports are now explicit;
  checkpoint `cbb3077` makes `python scripts/verify.py --changed --types`
  pass with quality 282 and preprocessing 103.
- Fresh lifecycle evidence includes MainWindow persistence 197, ChartEditor +
  DSC 251, Joint closure 1, and NMR cutover 5. The broader matrices are
  recorded in their task/acceptance notes.
- The full/boundary verifier now passes with a 30-minute allowance:
  `2587 passed, 8 warnings in 1042.86s`; the boundary audit also passes. The
  earlier 15-minute exit was an insufficient runtime budget, not a test hang.
  Real published-run, restarted-GUI visual, human scientific, and final
  release gates remain open.

## Real-fixture publication audit - updated 2026-07-26

- Fresh real runs completed for DSC standard, WAXS static/temperature, IR
  standard, and SAXS temperature. The per-run paths, outcomes, and bounded
  timeout results are recorded in
  `docs/acceptance/2026-07-26-real-published-run-audit.md`.
- SAXS temperature exposed a shared colorbar-axis audit bug. The correction is
  covered by 20 focused tests in task card
  `docs/agent/tasks/2026-07-26-colorbar-audit-regression.md`; it does not
  override the real run's scientific validation failure.
- WAXS strain and IR temperature-2D real directories initially exceeded the
  bounded diagnostic runtime; the publication snapshot fix is recorded in
  the active 2D performance task. Their complete shared lifecycle now passes;
  restarted-GUI visual review, vendor semantics, and scientific sign-off
  remain open.

## Real published-run walkthrough matrix - updated 2026-07-26

- Added `tests/test_real_published_run_walkthrough.py`. The real-case matrix
  now covers all automated SAXS/DSC/WAXS/IR/NMR modes, including full 2D cases;
  the latest SAXS temperature/strain addition passed both cases. Each case
  preserves one run ID through active Manifest Gallery selection, Main Editor
  working/published revision, export `metadata/runs/` plus active pointer, and
  MainWindow History restore.
- Fresh DSC isothermal and non-isothermal engine runs also completed the
  shared walkthrough manually. The non-isothermal fixture correctly retains
  its conversion as SI (only one valid curve) and keeps kinetics in diagnostic
  roles; it is not promoted to Main.
- A real PAD8 SAXS EDF frame also completed the static engine and the same
  shared walkthrough; the run published six figures and restored six Gallery
  entries with the static Main figure selected.
- Two-frame real smoke runs for WAXS strain/2D and IR temperature-2D also
  completed the same shared walkthrough; full directories remain bounded
  timeout/scientific-review items. Acceptance details are in
  `docs/acceptance/2026-07-26-real-published-run-audit.md`.

## Runtime/editor regression checkpoint - automated complete 2026-07-26

- Fixed ChartEditor annotation mixin MRO ownership and compact inspector
  nested size hints; restored legacy text selection geometry fallback while
  retaining explicit axes display-space overlays; synchronized live text
  preview selection frame/handles immediately; and isolated GUI logger
  propagation in `tests/conftest.py` so fallback warnings remain caplog-visible.
- Focused changed-file tests, task verifier, full `pytest -q` (2587), and the
  boundary audit all pass. Task card:
  `docs/agent/tasks/2026-07-26-full-suite-runtime-investigation.md`.
- No verifier implementation change was needed. The remaining blocker is
  product/scientific acceptance, not automated test execution.

## Qt lifecycle stability - checkpointed 2026-07-27

- Deferred `FigureFilePreview` fit callbacks now use parent-owned timers;
  MainWindow workspace context uses a distinct QLabel attribute with a legacy
  fake-compatible fallback; and ChartEditor test teardown clears dirty
  windows before deferred deletion.
- Focused evidence: viewer/lifecycle 23 passed, ChartEditor + DSC lifecycle
  251 passed, workspace/AI context 11 passed, and the complete MainWindow
  persistence file 197 passed in an external basetemp.
- MainWindow lint baseline cleanup is separately checkpointed at `cbb3077`, so
  the structured verifier now reaches its quality gates. Focused lifecycle
  evidence is `274 passed`; quality/preprocessing gates are `282`/`106`; the
  current full/boundary verifier passed `2671` tests with `10` known warnings
  and a passing boundary audit. The lifecycle code checkpoint is `fbf22b6`.
- Restarted-GUI visual review and human scientific/publication review remain
  open in the full-software release ledger.

## NMR real-data lifecycle closure - automated boundary completed 2026-07-25

- Added `tests/test_nmr_lifecycle_closure.py` across repository liquid 1H/C and
  solid 1H/C fixtures. Each run covers engine input/preprocessing/analysis,
  evidence, Manifest/Gallery, editor revision publication, export provenance,
  and History restore.
- Four-partition lifecycle: 4 passed in 252.98s; combined NMR matrix: 47
  passed in 348.63s. Evidence:
  `docs/acceptance/2026-07-25-nmr-lifecycle-closure.md`.
- Assignment-limited solid 13C Xc remains provisional; restarted-GUI visual
  review, scientific sign-off, and AI-off/failure/fallback remain open.

## IR figure lifecycle closure - automated boundary completed 2026-07-25

- Added `tests/test_ir_lifecycle_closure.py` for standard, temperature-2D, and
  explicit mapping/ROI DTOs. Mapping provenance and invalid-pixel diagnostics
  are asserted through the shared lifecycle.
- Focused IR lifecycle/provider/temperature/mapping/export/history matrix: 47
  passed. Evidence: `docs/acceptance/2026-07-25-ir-lifecycle-closure.md`.
- Vendor-native mapping input, real/Golden source review, restarted-GUI visual
  review, and the shared AI-off/failure/fallback matrix remain open.

## WAXS figure lifecycle closure - automated boundary completed 2026-07-25

- Added `tests/test_waxs_lifecycle_closure.py` for static, temperature, and
  strain. The strain case retains the existing `image_grid` reactive V2
  worksheet edit/save/publish route.
- Focused WAXS lifecycle/publication/provider/Workbench/V2/history matrix:
  29 passed. Evidence: `docs/acceptance/2026-07-25-waxs-lifecycle-closure.md`.
- Restarted-GUI 2D visual review, real-data scientific sign-off, and the shared
  AI-off/failure/fallback release matrix remain open.

## DSC figure lifecycle closure - automated boundary completed 2026-07-25

- Added `tests/test_dsc_lifecycle_closure.py`, a parameterized standard /
  isothermal / non-isothermal regression over provider -> Manifest/Gallery ->
  editor working save -> complete publication -> export provenance -> History
  restore.
- Focused DSC lifecycle matrix: 78 passed; history/gallery subset: 10 passed.
  The task-scoped verifier passed with quality gate 282 and preprocessing gate
  103. Evidence: `docs/acceptance/2026-07-25-dsc-lifecycle-closure.md`.
- No production code was needed because the shared lifecycle contracts were
  already connected. Restarted-GUI visual review, real-data scientific sign-off,
  and the shared AI-off/failure/fallback release matrix remain open.

## Unified engine evidence handoff - code completed 2026-07-25

- Ordinary DSC, WAXS, and IR analysis now attach the shared
  `AnalysisEvidence` payload to `AnalysisResult` through one core helper,
  without overwriting richer SAXS/NMR/mapping payloads.
- Focused engine/evidence matrix: 44 passed. Task card:
  `docs/agent/tasks/2026-07-25-unified-engine-evidence-handoff.md`; acceptance:
  `docs/acceptance/2026-07-25-unified-engine-evidence-handoff.md`.
- This is a code-level handoff only. Real mode-by-mode GUI restart, Editor/
  export inspection, AI/fallback scientific review, IR mapping semantics, and
  release approval remain open in the full-software goal.

## NMR evidence persistence - code completed 2026-07-25

- Ordinary `NMREngine.analyze()` now builds the shared NMR `AnalysisEvidence`
  payload from the representative typed result and attaches it to
  `AnalysisResult`; spectrum count remains explicit metadata.
- The focused engine-assembly regression is green, and the repository's real
  NMR reader/core matrix remains `17 passed`. GUI/export/restart and scientific
  review are still open; this is not a complete NMR release claim.
- Task card: `docs/agent/tasks/2026-07-25-nmr-evidence-persistence.md`.
- A read-only real-engine smoke run over the repository's liquid H/C and
  solid H/C fixtures completed through external output roots. All four runs
  passed validation and emitted evidence plus active Manifest figures; solid
  13C remained assignment-limited for Xc and fit/assignment warnings were
  retained. This proves core/publication behavior, not GUI restart or human
  scientific acceptance.

## Joint lifecycle closure - automated boundary completed 2026-07-25

- Added `tests/test_joint_lifecycle_closure.py`, which verifies one fixed Joint
  run ID across hub publication, active Manifest Gallery, Editor working and
  published revisions, export `metadata/runs/` plus active pointer, and
  MainWindow History restore with the custom Joint Workbench.
- Focused regression: `1 passed in 4.39s`. No production code was needed; the
  existing shared contracts already form the complete automated path.
- Evidence: `docs/acceptance/2026-07-25-joint-lifecycle-closure.md` and task
  card `docs/agent/tasks/2026-07-25-joint-lifecycle-closure.md`.
- Real-data, AI/fallback, restarted-GUI, and human scientific release review
  remain open and are not implied by this contract test.

## Full-software baseline inventory - verified 2026-07-25

- The evidence ledger is now recorded in
  `docs/acceptance/2026-07-25-full-software-baseline.md`.
- External-basetemp core matrices pass: SAXS 210, DSC 64, WAXS 46, IR 30,
  NMR 24, Joint 18; shared quality gate 282 and preprocessing gate 103.
- These are contract/core results only. The ledger explicitly leaves IR
  mapping/ROI semantics, real-run Gallery/Editor/export verification, fallback
  and AI-failure coverage, restarted-GUI visual review, and release approval
  open.

## Cross-technique AI safety matrix - contract boundary verified 2026-07-25

- `tests/test_preprocess_cross_technique_matrix.py` covers AI-off registration,
  engine failure, and fallback rejection for DSC, IR, WAXS, SAXS, and NMR.
- `tests/test_preprocess_ai_off_compat.py` covers deterministic AI-off output
  and clean report metadata; `tests/test_preprocess_fault_injection.py`
  covers invalid intent, timeout, engine failure/exception, audit failure, and
  config-hash rollback.
- Joint is explicitly report-level AI review and remains outside single-
  technique preprocessing. This is automated safety evidence, not a human
  scientific release sign-off.

## Full-software audit - 2026-07-25

- Default `python scripts/verify.py --changed --types` passed with quality gate
  282 and preprocessing gate 103.
- The prescribed `--full --boundary` variant was run with an external
  basetemp but timed out after 364 seconds (exit 124) without a failure
  summary. Treat it as incomplete verification, not as a pass.
- The goal remains active until the explicit scientific, real-run, restarted-
  GUI, AI/fallback, and human release gates are closed.

## NMR Workbench/Figure checkpoint - verified 2026-07-25

- Liquid H/C and solid H/C profiles are customized; the shared NMR provider
  covers spectrum, deconvolution, comparison, region-integral, and
  assignment-gated crystallinity definitions. `NMREngine.plot()` preserves
  parameters/peaks CSV exports after the unified publisher migration.
- Focused NMR engine/provider/document/preprocessing/profile matrix: 29 passed.
  Acceptance note: `docs/acceptance/2026-07-25-nmr-workbench-checkpoint.md`.
- Remaining: real four-partition visual review, Gallery/Editor/export bundle,
  provenance/history, AI-off/failure/fallback, and release acceptance.

## Joint Figure provider checkpoint - code completed 2026-07-25

- Added `polynexus/core/joint/figure_provider.py` over the existing
  `JointBatchRow` contract. It emits main crystallinity comparison, SAXS/WAXS
  multiscale support, and evidence-coverage diagnostic definitions.
- `JointCoordinator.publish_figure_definitions()` and
  `publish_hub_report()` now publish through the shared production pipeline
  and attach Manifest context to the report. `JointHubWorker` calls this
  service, so a real `joint.compare` run produces the new entries. Workbench
  IDs are `joint.series.crystallinity` and `joint.series.multiscale`.
- Joint completion now persists through History, History restore rehydrates the
  Joint report, the typed custom Workbench presentation is used, and export
  bundles preserve `runs/<run_id>/` under `metadata/runs/`. Evidence:
  `docs/acceptance/2026-07-25-joint-figure-provider-checkpoint.md`; focused
  integration/contract matrix 37 passed plus restore regression 7 passed.
- Remaining: active Gallery selection against a real published run, conflict
  provenance and AI-off/failure/fallback tests, then real-data and restarted-
  GUI review. Do not call Joint complete yet.

## Joint conflict provenance - code checkpoint in progress 2026-07-25

- Joint validation rows now preserve exact source run IDs, submodules, evidence
  status/weight/reasons, and missing-source state for each cross-tech check.
- Joint Main/SI/diagnostic figure recipes carry the same batch-level run
  provenance for Gallery/Editor/export traceability.
- Focused Joint/NMR provenance matrix is `14 passed`; task verifier,
  changed/type verifier, and checkpoint commit remain pending. This does not
  close real-data, restarted-GUI, export-bundle, or AI/fallback acceptance.

## IR temperature-2D Figure lifecycle checkpoint - code completed 2026-07-25

- `IREngine.build_figure_definitions()` now passes the existing
  `IRTemp2DResult` to the shared IR provider. The provider emits validated
  Manifest IDs for the main heatmap, band tracking, band indices, and
  synchronous/asynchronous correlation diagnostics.
- The Workbench profile now routes to
  `ir.temperature_2d.heatmap` and `ir.temperature_2d.band-tracking`; the old
  `Fig-IRT*` files remain legacy output and are not treated as normal Gallery
  entries.
- Evidence: `docs/acceptance/2026-07-25-ir-temperature-2d-workbench-checkpoint.md`;
  focused provider/lifecycle/profile matrix 7 passed; changed/type verifier,
  quality gate 282, and preprocessing gate 103 passed.
- IR mapping/ROI provider and the complete standard/temperature/mapping Figure
  Pack are now covered by the shared contract; vendor input semantics,
  real/Golden data, fallback/AI, and restarted-GUI visual acceptance remain
  release gates.

## IR mapping/ROI contract checkpoint - completed 2026-07-25

- Added `IRMappingResult`/`IRMappingROISpectrum` with explicit map geometry,
  invalid-pixel mask, ROI spectra, metric label, and provenance source id.
- Added structural evidence and `IREngine.set_mapping_result()` handoff;
  provider emits Main `ir.mapping.roi`, SI `ir.mapping.spectra`, and diagnostic
  `ir.mapping.invalid-pixels` through the shared FigurePipeline.
- Mapping Workbench now links all three logical IDs. Masked NaN heatmap cells
  remain visible as masked cells instead of being imputed.
- Focused implementation tests are green; task verifier passed and checkpoint
  `863ec3a` was created. Vendor reader, real fixture, fallback/AI gates, and
  restarted-GUI acceptance are intentionally open.

## IR three-mode vertical slice - code checkpoint completed 2026-07-25

- Standard IR now assigns an explicit Main role to the first spectrum and the
  crystallinity overview, SI to subsequent spectra and peak fits, and
  diagnostic to experimental/computed comparisons.
- Temperature-2D and mapping/ROI role matrices are explicitly regression
  tested; mapping provenance and invalid-pixel evidence remain unchanged.
- The shared FigurePipeline sibling-failure behavior is covered: one
  `generation_failed` entry does not hide ready siblings.
- Focused matrix is `26 passed`; task-scoped verifier and allowlist checkpoint
  `349bbae` passed. Real reader/fixture, AI/fallback, export-bundle, and
  restarted-GUI acceptance remain open.

## NMR/Joint published-run provenance matrix - code checkpoint completed 2026-07-25

- NMR spectrum/deconvolution publication roles are now explicit (`main` and
  `diagnostic`) instead of inheriting `si`.
- Synthetic NMR and Joint runs now have focused evidence for Manifest-only
  active Gallery discovery, object-editing documents, run-relative data sources,
  and visible diagnostic generation failures.
- Real-data/restarted-GUI review, export bundle inspection, AI-off/failure/
  fallback scientific acceptance, and final release review remain open.

## Preprocessing fallback safety matrix - code checkpoint completed 2026-07-25

- `PreprocessEvidence` now records normalized fallback state/reason and the
  shared decision guard fails closed for fallback-active candidates across DSC,
  IR, WAXS, SAXS, and NMR.
- The cross-technique matrix covers AI-off shadow defaults, failed runs, and
  fallback-derived evidence; Joint is explicitly preprocessing N/A.
- Focused matrix is `42 passed`; task-scoped verifier passed with quality 282
  and preprocessing 103; checkpoint `6bafcaa` is present. Real/Golden and
  GUI/scientific review remain release gates.

## Results Workbench profile platform - Phase 1 completed 2026-07-25

- Added the typed profile registry at `polynexus/gui/results_workbench_profiles.py`.
- SAXS static/temperature/strain now have distinct titles, narratives, tabs,
  review actions, empty/error states, and validated existing SAXS figure IDs.
- DSC/WAXS/IR/NMR/Joint modes are registered through the same profile boundary.
- `ResultsTableModel` carries the profile; `ResultsTablePanel` renders the
  profile header, figure links, profile action, and empty/error state; main
  window routing sends figure links to the manifest-backed gallery.
- Acceptance note: `docs/acceptance/2026-07-25-results-workbench-phase1.md`.
- Next action: complete the SAXS three-mode vertical slice against real/Golden
  fixtures, including Gallery/Editor/export and fallback/AI-off acceptance.

## SAXS three-mode vertical slice - code checkpoint completed 2026-07-25

- Profile Figure links now use real static/temperature/strain Manifest IDs and
  fallback candidates; Gallery exposes logical ID selection for this route.
- Evidence/provider, figure lifecycle, export, gallery, main-window, and real
  SAXS evaluation regressions are green. Acceptance note:
  `docs/acceptance/2026-07-25-saxs-full-vertical-slice.md`.
- Release claim remains blocked on restarted-GUI visual/scientific review and
  the final cross-module AI-off/failure/fallback matrix.
- Next action: build the DSC three-mode profile/Workbench vertical slice.

## DSC three-mode Workbench checkpoint - code completed 2026-07-25

- DSC standard/isothermal/non-isothermal profiles now use mode-specific tabs
  and real publication-provider Manifest IDs; existing structured analysis,
  evidence, FigureDocument, export, and evaluation contracts remain intact.
- Evidence: `docs/acceptance/2026-07-25-dsc-workbench-checkpoint.md`;
  focused DSC matrix 53 passed and Results Workbench matrix 47 passed.
- Release visual/scientific review and cross-module AI-off/failure/fallback
  audit remain pending. Next action: WAXS profile and figure-contract slice.

## WAXS three-mode Workbench checkpoint - code completed 2026-07-25

- WAXS static/temperature/strain profiles now use mode-specific tabs and real
  provider Manifest IDs, including the 2D strain figure route.
- Evidence: `docs/acceptance/2026-07-25-waxs-workbench-checkpoint.md`;
  focused WAXS provider/evaluation matrix 33 passed.
- Next action: IR standard/temperature-2D/mapping profile and figure-contract
  slice; release visual/scientific and AI failure gates remain pending.

## PolyNexus full software vertical delivery - active 2026-07-25

- Overall goal: complete the shared platform, customized Results Workbench,
  SAXS/DSC/WAXS/IR/NMR/Joint vertical slices, AI quality gates, export and
  release acceptance. The complete scope and completion definition are recorded
  in `docs/agent/tasks/2026-07-25-full-software-vertical-delivery.md`.
- Overall design/plan:
  `docs/superpowers/specs/2026-07-25-full-software-development-architecture-design.md`
  and `docs/superpowers/plans/2026-07-25-full-software-development.md`.
- Current status: Phase 0 inventory and Phase 1 Workbench contract are next;
  previous SAXS provider contracts and editor work are foundations, not a
  complete overall product release.
- Constraint: every technique mode must pass the full vertical definition of
  done before its phase is marked complete.

## SAXS other modules polish - temperature slice completed 2026-07-25

- Goal: 按温变 -> 拉伸 -> 静态顺序扩展 SAXS 板块组织经验；当前只处理温变
  `evolution / Avrami / selected evidence`，保持 waterfall 现状。
- Design/task/plan: `docs/superpowers/specs/2026-07-25-saxs-temperature-other-panels-design.md`、
  `docs/superpowers/plans/2026-07-25-saxs-temperature-other-panels.md`、
  `docs/agent/tasks/2026-07-25-saxs-other-modules-polish.md`。
- Current evidence: 新增温变 provider 契约测试 `2 passed`；既有 review-hint 与
  result-table 回归合计 `15 passed`。`python scripts/verify.py --changed --types`
  在外置 pytest basetemp 下通过，quality gate `282 passed`、preprocessing gate
  `103 passed`；Ruff、compile、type baseline、memory 和 whitespace checks 通过。
  现有 provider 已满足顺序、fallback、role 边界，因此本阶段没有科学算法或
  生产 provider 改动。
- Next action: checkpoint 后为拉伸 SAXS 单独创建设计/计划，不与本阶段混改。

## SAXS other modules polish - strain slice in progress 2026-07-25

- Design/plan: `docs/superpowers/specs/2026-07-25-saxs-strain-other-panels-design.md`、
  `docs/superpowers/plans/2026-07-25-saxs-strain-other-panels.md`。
- Provider contract is covered by a strain order/role regression; the GUI review
  hint now accepts `saxs.strain` and the red-green test is passing. Static tests
  are isolated in `tests/test_saxs_static_figure_panels.py` for the next checkpoint.
- Next action: run strain-slice verification and create its allowlisted checkpoint,
  then verify the static slice independently.

## SAXS other modules polish - all slices completed 2026-07-25

- Design/plan: `docs/superpowers/specs/2026-07-25-saxs-static-other-panels-design.md`、
  `docs/superpowers/plans/2026-07-25-saxs-static-other-panels.md`。
- Static provider order/role regression is isolated in
  `tests/test_saxs_static_figure_panels.py`; focused result: `1 passed`.
- Static checkpoint: `2346df0`; the full SAXS goal is now reconciled across
  temperature, strain and static slices. Further work is limited to optional
  restarted-GUI visual walkthrough and human scientific review.

## Unified LegendGeometry persistence boundary - completed 2026-07-24

- Completed the final migration layer for the Origin-style legend object.
  `LegendGeometry` now carries canonical axes/display rectangles plus legacy
  automatic anchor metadata, so editor helpers, previews, status text,
  presentation sizing, and both renderers no longer interpret legacy placement
  fields independently.
- Style commands, `FigureObjectStore`, and document saves remove `loc`,
  `bbox_to_anchor`, and `box_size` whenever `legend_geometry` is present while
  legacy-only documents remain readable through the importer. Undo restores the
  prior style snapshot correctly.
- Evidence: focused legend/editor matrix `297 passed`; structured verifier and
  default verifier both passed, including quality gate `282` and preprocessing
  gate `103`. Task card:
  `docs/agent/tasks/2026-07-24-legend-object-geometry.md`.
- Manual GUI walkthrough of static, log-axis, and multi-series visuals remains
  pending after restarting the desktop process; Chromium is unavailable.

## Legend overlay viewport synchronization - completed 2026-07-24

- Fixed the remaining real-GUI mismatch where the legend moved after the Qt
  canvas/sidebar resized but its display-space selection frame and handles kept
  their original pixels. A draw-time overlay synchronizer now refreshes the
  frame and handles from the live Matplotlib legend extent on every render.
- Evidence: focused legend/editor matrix remains `297 passed`; the dedicated
  adapter and ChartEditor viewport-resize regressions pass; structured and
  default changed/type verifiers pass with quality gate `282` and preprocessing
  gate `103`.

## Unified LegendLayout refactor - completed 2026-07-24

- Generated legends now resolve legacy `loc`, two/four-value
  `bbox_to_anchor`, and `box_size` through the pure
  `polynexus/core/figures/legend_layout.py` model. Auto layouts retain legacy
  anchors for inspector compatibility; fixed layouts canonicalize to a
  lower-left axes anchor and positive width/height.
- Formal and legacy renderers, selection frames/handles, hit testing, drag
  previews, inspector geometry, undo transactions, and persistence consume the
  same resolved geometry. Disjoint persisted boxes no longer trigger a hidden
  rendered-bounds fallback, so the visible legend and edit frame cannot belong
  to different layout interpretations.
- Origin-like corner resize now treats the box as a true content scale: the
  drag transaction captures the starting geometry/font, derives a continuous
  area-based font scale, applies it during preview, and persists it with the
  box dimensions. Undo restores both geometry and typography, eliminating the
  former "frame grows, text snaps back" behavior.
- First fixed-box edit normalizes the style to `loc="lower left"`; preview and
  commit share the same style update. Generated export clears selection before
  rendering, so transient frames/handles remain non-exported. Invalid legacy
  dimensions surface a concise status diagnostic.
- Evidence: focused legend/editor matrix `292 passed`; task verifier passed
  with quality gate `282` and preprocessing gate `103`. Task card:
  `docs/agent/tasks/2026-07-24-legend-layout-refactor.md`.
- Known follow-up: restart the GUI for manual visual review of static images,
  log axes, and multi-series legends; the optional Chromium visual companion
  could not launch because the local executable is unavailable.

## Editor legend viewport and typography - completed 2026-07-23

- Formal manifest previews pass the actual live canvas width to the shared
  Matplotlib renderer.  Long automatic sample-name legends choose a safe
  single-column presentation before constrained layout can collapse the plot;
  publication exports retain their independent planned width and can remain
  two-column.
- The same responsive label-aware rule now also applies to legacy generated
  previews.  An explicit legend font size is a normal editable style property:
  it is persisted, rendered in preview/export, and restored through undo.
  Selecting a legend exposes only the font-size control; unrelated color,
  line-width, and alpha controls remain disabled.
- Evidence: focused matrix `291 passed`; structured and default verifier runs
  passed, including quality-gate `282` and preprocessing `103`.  Task card:
  `docs/agent/tasks/2026-07-23-editor-legend-viewport.md`.  The verifier used
  an isolated pytest base directory because the pre-existing repository
  `.pytest_tmp` has a Windows access restriction; no existing scratch artifact
  was changed. Restart the GUI before visual confirmation.

## Editor legend interaction polish - completed 2026-07-23

- Automatic multi-series legends now share one responsive presentation policy
  across formal `MatplotlibFigureRenderer` output and the ChartEditor's legacy
  generated preview: wide canvases retain two columns, while narrow canvases
  use one compact in-plot column and a smaller readable font. This policy is
  transient and never changes saved legend position or style merely because a
  user selects it.
- Double-clicking a generated legend now opens a compact localized dialog with
  one curve-name input per visible legend series. Confirming applies all
  nonblank names through one undoable document replacement, persists once,
  redraws once, and keeps the legend selected; Escape/Cancel leaves the
  document untouched.
- A final review hardening pass ensures a double-click must land on the legend
  itself and filters multi-panel dialog rows to the legend's own panel, so text
  and blank-canvas double-clicks remain available for their existing actions.
- Evidence: focused object-store/render/editor matrix passed `274`; the task
  verifier and default changed/type verifier both passed, including the quality
  gate (`282`) and preprocessing optimization gate (`103`). Task card:
  `docs/agent/tasks/2026-07-23-editor-legend-interaction.md`. Restart the GUI
  before live visual confirmation.

## Multi-series chart legend defaults - completed 2026-07-23

- Object-mode figures now materialize a persisted legend only when at least two
  named plot series are visible. The legend uses sample names verbatim,
  defaults to upper-right placement, and switches to two columns when more
  than three series are present.
- Renaming a series refreshes its legend entry through the existing editor
  name control. Existing legend visibility and dragged position remain
  authoritative; a single-series chart remains legend-free.
- The legacy and formal renderer paths now use the same persisted legend
  object. Multi-panel documents intentionally retain their pre-existing legend
  state rather than receiving an unassigned automatic object. This also fixed
  selected-line endpoint switching, where the second endpoint click had
  previously cleared selection instead of moving the active handle emphasis.
- TDD evidence: object-store, renderer, and offscreen ChartEditor regressions
  first failed for one-series suppression, formal `show_legend: false` output,
  compact columns, multi-panel safety, and endpoint selection; the final
  focused matrix passed `266` tests. Task card:
  `docs/agent/tasks/2026-07-23-editor-multiseries-legend.md`. Running GUI
  instances must be restarted before manual inspection.

## Responsive editor inspector sidebar - completed 2026-07-23

- The ChartEditor inspector can now shrink to 280 logical pixels without
  horizontal scrolling or clipped controls. Inspector forms wrap labels above
  controls, object labels elide instead of forcing width, and the object tree
  has a bounded height so its property fields remain reachable below.
- Batch actions use a three-column grid rather than one long horizontal strip;
  object action controls can shrink with the sidebar without changing commands.
- The focused compact-width Qt regression and editor matrix passed (`78 passed`,
  four known Matplotlib tight-layout warnings). Restart the GUI before visual
  inspection.

## Inline text editor visual polish - completed 2026-07-23

- Direct canvas text entry no longer displays the native blue `QLineEdit`
  focus frame or the `标注文字` / `Annotation text` placeholder over the
  figure. It now uses a transparent input layer, a subtle dashed edit range,
  and Qt's existing blinking caret.
- Enter-to-commit, Escape-to-cancel, focus, text geometry, and double-click
  editing remain on the same shared inline-editor path.
- TDD evidence: the focused visual contract first failed because the input
  retained its native frame, then passed after the minimal chrome change. The
  direct-text workflow matrix passed (`77 passed`, four known Matplotlib
  tight-layout warnings). Restart the GUI before visual inspection.

## Generated undo/redo visual synchronization - completed 2026-07-23

- Fixed generated-object undo and redo so session history now immediately
  rebuilds the canvas, refreshes selection controls, and persists the restored
  document. Previously the document changed first, while the canvas continued
  showing the old artist until a later canvas interaction caused a redraw.
- History navigation now clears the UI selection when an undone add no longer
  exists, then restores the object(s), layer-tree selection, and inspector when
  redo recreates them. Repeated history navigation of an unchanged selection
  source also redraws explicitly rather than relying on a selection signal.
- Regression coverage verifies an inspector geometry edit, immediate undo
  redraw, immediate redo redraw, added-object selection/inspector recovery,
  and batch-selection recovery without an intervening canvas click.

## Editor history shortcuts in numeric controls - completed 2026-07-23

- Fixed the ChartEditor's Ctrl+Z routing when focus is inside a numeric style
  or geometry control. Those controls previously consumed the key before the
  window-level history shortcut could run, making a just-completed font-size
  edit appear non-undoable.
- Ctrl+Z now undoes from canvas or numeric-control focus; Ctrl+Shift+Z and
  Ctrl+Y redo. Plain text inputs retain their local text-editing behavior.
- Qt workflow coverage exercises static canvas focus, generated canvas focus,
  and the generated context font-size spin control, including redo.

## Generated text font-size commit fix - completed 2026-07-23

- Fixed the formal manifest-render styling pass so it no longer overwrites a
  generated text object's persisted `style.font_size`. This keeps a corner-drag
  font-size preview visually identical after mouse release and the resulting
  document rebuild.
- TDD evidence: the focused regression initially failed because a `72 pt`
  object label was reset to `12 pt`; it passes after the object-level style
  boundary is preserved. The ChartEditor workflow suite passes (`48 passed`,
  four known Matplotlib tight-layout warnings).
- The isolated generated-document mixin suite retains one pre-existing,
  unrelated harness failure in
  `test_manifest_editor_registers_native_image_grid_artists_for_object_editing`:
  it instantiates an incomplete mixin without `_generated_figure_object_by_id`.

## Editor workflow convergence - implementation complete 2026-07-23

- Task card: `docs/agent/tasks/2026-07-22-editor-workflow-convergence.md`.
- M1 context identity and stale-result gating are committed; M2 capability
  header, M3 lifecycle controls, M4 export/gallery scope, and M5 shell
  diagnostics are implemented in local checkpoints.
- The 2026-07-23 hardening checkpoint aligns actionable selection feedback,
  defers visibility-tree refresh until the active Qt `itemChanged` call
  returns, adds copyable error diagnostics, and formalizes the GUI `RunState`
  contract so cancelled work cannot publish a late result.
- Evidence: `tests/test_chart_editor.py` passes (`238`); the focused workflow
  matrix passes (`118`, four known Matplotlib tight-layout warnings); the
  structured verifier passes with quality gate `282` and preprocessing
  optimization `103`; `scripts/launch_gui.py --diagnose` resolves the active
  `D:\PolyNexus\polynexus\__init__.py` on
  `codex/origin-editor-usable-controls` at `9fc109c6`.
- M6 decision: no broad `main_window.py` split in this task because the new
  service boundaries cover the accepted behavior. A human visual walkthrough
  remains the only planned follow-up; existing untracked drafts and diagnostics
  remain untouched.

## Origin-style generated text labels - completed 2026-07-22

- Task card: `docs/agent/tasks/2026-07-22-origin-label-text.md`. Generated
  labels are unwrapped, use tight rendered selection overlays, resize by font
  size, and now open a compact one-line editor at the rendered label top edge.
- TDD evidence: the new tall-rectangle Qt regression failed first (`240 !=
  24`), then the focused creation/double-click Enter/Escape workflow passed
  (`3 passed`). The required full label matrix passed (`87 passed`, four known
  Matplotlib tight-layout warnings).
- Verifier commands: `python scripts/verify.py --task
  docs/agent/tasks/2026-07-22-origin-label-text.md --changed --types` and
  `python scripts/verify.py --changed --types` both passed, including Ruff,
  compile, quality gate (`282 passed`), preprocessing gate (`103 passed`), and
  whitespace checks.
- Commit evidence: prerequisite label slices are `63acd9a5`, `ef2d297f`,
  `9de895c8`, `13ab1961`, and `e1dc44a`; the completion checkpoint is
  `bfa6f2ed`, created after verification. None of these commits were pushed.
- A running GUI must be restarted before manual inspection.

## Generated text double-click editing - verification-ready 2026-07-22

- Existing generated text now opens the shared inline editor on a canvas
  double-click, prefilled with the displayed `text` value rather than the
  object-list name.
- Submission uses `UpdateTextCommand`, persists the object document, refreshes
  the rendered figure, and remains undoable.
- Focused ChartEditor workflow/curve matrix passes (`62 passed`); the four
  tight-layout warnings are pre-existing log-axis warnings.
- A running GUI must be restarted from `D:\PolyNexus\scripts\launch_gui.py`
  before visual acceptance.

## Viewport-anchored generated text boxes - verification-ready 2026-07-22

- Implemented the approved Axes-relative text-box slice from task card
  `docs/agent/tasks/2026-07-22-viewport-text-box-refactor.md`. New generated
  text creation stores normalized `x/y/width/height` with
  `coordinate_space: "axes"`; rendering, preview, hit testing, selection
  frames/handles, body movement, corner resizing, and Inspector edits consume
  the same Axes transform.
- Legacy data-coordinate text remains readable and is converted to a persisted
  Axes-relative box when the generated document is saved. Core renderer export
  uses the same transform for marked boxes.
- Fresh expanded focused matrix passes (`106 passed`), structured and default verifiers
  pass with quality gate `282 passed` and preprocessing gate `103 passed`.
- The live GUI acceptance pass remains pending; restart the canonical launcher
  from `D:\PolyNexus` before manual visual verification. The pre-existing
  `.pytest_tmp` ownership issue is avoided with `D:\PolyNexus\.pytest_tmp_alt`.

## Generated text drag anchor follow-up - completed 2026-07-22

- Reproduced the screenshot issue with a regression test: the generated text
  preview moved its Matplotlib `Text` artist to the persisted box origin
  `(x, y)` while the box renderer uses the left/top anchor `(x, y + height)`.
  This made the text visibly fall to the box's lower-left corner during drag.
- Added the shared `polynexus/core/figure_text_geometry.py` anchor contract and
  routed formal rendering, legacy generated preview rendering, and live drag
  preview through it. The focused editor/render matrix now passes (`103`),
  including log-axis text-box movement.
- The final structured/default verifiers pass; live GUI acceptance still
  requires restarting the canonical launcher from
  `D:\PolyNexus\scripts\launch_gui.py`.

## Generated text placement and font sizing - completed 2026-07-22

- Generated text boxes now use their stored box origin as the visual left-top
  anchor, while unboxed text keeps its legacy anchor behavior. The renderer and
  generated-document preview use the same alignment calculation, so selection
  and final rendering no longer disagree about where text begins.
- The generated-object Inspector and context style bar now expose and hydrate
  text font size. Changes are routed through the shared undoable style command,
  persisted to the document, and immediately rebuild the visible artist.
- Generated style submission now only sends line width to object types whose
  core edit capabilities support it; text font-size changes are no longer
  rejected by an unrelated line-width field.
- Focused text/renderer regression checks pass. The broader batch retains the
  pre-existing `test_manifest_editor_registers_native_image_grid_artists_for_object_editing`
  fixture failure because it directly instantiates an incomplete mixin without
  `_generated_figure_object_by_id`; it is outside this fix and remains untouched.
- The canonical launcher diagnostic resolves `D:\PolyNexus\polynexus\__init__.py`.

## High-DPI live canvas fit - completed 2026-07-22

- Fixed generated/editor figure fitting on Windows display scaling: Qt widget
  dimensions are logical pixels, while Matplotlib's Agg buffer uses device
  pixels. The live figure now scales both dimensions by
  `devicePixelRatioF()`, preventing interaction rebuilds from rendering at
  2/3 or 1/2 of the available canvas width/height.
- Figure replacement now assigns the new figure, restores only its viewport
  state, and performs the device-pixel fit last; both the Qt backend assignment
  and viewport-size restoration previously overwrote the corrected size.
- Added a regression test that reproduces a 150% display and asserts the
  figure buffer matches the device-pixel canvas size. Focused render/workflow
  tests pass (`40 passed`); the default changed/type verifier passes with
  quality gate `282 passed` and preprocessing gate `103 passed`.

## Unified canvas interaction - completed 2026-07-21

- Added immutable `Box`, `Segment`, and `Curve` geometry records with legacy
  payload adapters. Generated text and rectangle previews now retain full box
  geometry while moving on linear and logarithmic axes; selection frames and
  handles update from that same geometry.
- Generated text now uses the dragged box's left-bottom anchor, supports body
  movement and four-corner resizing, and commits width/height in one undoable
  edit. Static text and rectangle creation normalizes reversed drags through
  the same box contract.
- Focused cross-mode interaction matrix passed (`141 passed`). Structured and
  default changed/type verifiers pass when `PYTEST_ADDOPTS` points to
  `D:\\PolyNexus\\.pytest_tmp_alt`: quality gate `282 passed`, preprocessing
  gate `103 passed`, compile, whitespace, and memory checks passed.
- Running the local preview server still owns repository `.pytest_tmp`, so the
  verifier without the basetemp override reports WinError 5 during pytest
  cleanup; this is an environment limitation, not a source failure.
- Implementation commits are `e34ed75`, `814d9f5`, `d0b297b`, and `d24cc8b`.


## Inline text editor layering fix - completed 2026-07-21

- Real Qt reproduction showed the generated text input was visible and focused
  but covered by the Matplotlib canvas. The shared inline text editor now raises
  itself before focusing, so the input is visible and interactive for direct
  canvas text placement.
- Focused text/inline matrix passed (`15 passed`), including the real Qt widget
  stacking regression. Structured verification passed with Ruff, compile,
  quality gate `282 passed`, preprocessing gate `103 passed`, and whitespace
  checks. The task card is
  `docs/agent/tasks/2026-07-21-inline-text-layering.md`.
- The GUI must be restarted after this checkpoint; the screenshot supplied by
  the user predates this fix.

## Empty selection visibility follow-up - completed 2026-07-21

- The editor now distinguishes an empty selection from the compatibility
  Background row with localized `未选择对象` / `No object selected` feedback.
  Clearing generated or static selection returns to this state, while explicit
  background activation still reports Background.
- Focused behavior checks pass (`4 passed`); structured and default changed/type
  verification both pass with quality gate `282 passed` and preprocessing gate
  `103 passed`. The task card is
  `docs/agent/tasks/2026-07-21-empty-selection-visibility.md`.
- A running GUI must be restarted to load the new source; the launcher probe
  confirms the canonical root is `D:\PolyNexus`.

## Strong editor feedback mode - implementation complete, checkpoint blocked 2026-07-21

- Generated chart selection now renders transient blue dashed frames for text,
  rectangle, line, arrow, curve, and rendered series bounds. Frames stay
  outside the persistent artist map and are absent during generated export.
- Static annotation selection now has a transient blue dashed scene frame below
  handles. It is hidden by `render_scene()` exports, removed on Escape/clear/
  rebuild, and does not enter annotation history. The object tree preserves the
  background row for compatibility but clears its selection state when there is
  no editable object and scrolls matching nested rows into view.
- Focused matrix passed: `127 passed` for annotation canvas, layout, and
  workflow tests; renderer/workflow selection and export checks passed with
  `20 passed`. Changed modules compile and `git diff --check` passes.
- The task card is valid after adding numbered implementation steps. `ruff
  0.15.22` and `pyright 1.1.411` are now installed in the bundled Python
  runtime and the verifier reaches the quality gate. The quality gate remains
  blocked by Windows permission errors while cleaning `.pytest_tmp`; the full
  combined editor matrix also retains the known Qt access violation in the
  legacy `LayerTreeItem.setData()` path.
- The atomic checkpoint could not be created because this sandbox identity lacks
  write permission for `.git/index` and `.git/objects`; no push, merge, or
  cleanup was performed, and pre-existing untracked drafts remain untouched.

## Unified editor interaction architecture — completed 2026-07-21

- Connected the Qt-independent `EditorInteractionController` to static
  `AnnotationCanvas` creation, body drag, handle drag, cancellation, and the
  generated ChartEditor tool/gesture lifecycle. Creation tools return to
  Select, and generated object mode continues to deactivate Matplotlib
  navigation before annotation gestures.
- Added `GeneratedInteractionAdapter` and immutable `HitTarget` records so
  generated text, line, curve, rectangle, legend, and point targets expose a
  consistent object/body/handle/cursor contract while existing edit-session
  commands remain the history authority.
- Added focused adapter/controller tests and a real Qt static creation gesture
  regression. Focused interaction/workflow matrix: `115 passed`; all
  ChartEditor/AnnotationCanvas regressions: `465 passed`.
- Structured and default verifiers passed: Ruff/compile, quality gate `282
  passed`, preprocessing gate `103 passed`, and whitespace checks. Task card:
  `docs/agent/tasks/2026-07-21-unified-editor-interaction-architecture.md`.
- Code checkpoint: `36a0cc5`; local mainline finish completed through
  `scripts/repo_maintenance.py` in `8fecc26`.

## Navigation toolbar interaction conflict — completed 2026-07-21

- Generated object-edit mode now hides Matplotlib's pan/zoom toolbar, which was
  drawing the orange zoom rubber-band and intercepting annotation drags.
- Selecting a generated text, line, arrow, curve, or rectangle tool now exits
  any active navigation mode before the gesture begins; static preview mode
  retains the navigation toolbar.
- Focused layout/workflow tests pass (`49 passed`). Task card:
  `docs/agent/tasks/2026-07-21-navigation-toolbar-interaction-conflict.md`.

## Curve body hit regression — completed 2026-07-21

- Generated curve body picking now samples the quadratic path in data space,
  transforms it through the rendered artist into pixels, and reuses the
  existing segment hit tolerance. This fixes visible-stroke misses on
  logarithmic axes while retaining the original artist fallback.
- The curve body can now enter the existing preview drag transaction; endpoint
  and control-point movement remain persisted through the existing geometry
  command path.
- Focused workflow, curve, and hit-testing tests pass (`47 passed`); the task
  verifier passes with Ruff, compile, quality gate (`282 passed`), preprocessing
  gate (`103 passed`), and whitespace checks.

## Generated canvas drag regression — completed 2026-07-21

- Text body hit testing now uses the rendered artist window extent, so labels
  remain selectable when logarithmic-axis data coordinates make the old fixed
  fallback bounds inaccurate.
- Generated drag viewport snapshots now retain X/Y axis scales. Non-linear
  axis body movement uses the active artist transform and pointer pixel delta;
  linear axes retain the exact data-coordinate movement contract.
- Focused generated drag/workflow tests pass (`31 passed`). The structured
  verifier passes for task card
  `docs/agent/tasks/2026-07-21-generated-canvas-drag-regression.md`, including
  Ruff, compile, quality gate (`282 passed`), preprocessing gate (`103 passed`),
  and whitespace checks.
- The pre-existing untracked drafts and diagnostics remain intentionally
  untouched; no push or mainline merge was performed for this follow-up.

> Last updated: 2026-07-20

## Editor interaction reliability — completed 2026-07-20

- Added direct body-drag transactions for static annotations and generated
  text/rectangle/curve objects. Handles now resize text boxes as well as
  rectangles, curve defaults use a distance-aware control point, line body
  movement preserves both endpoints, and generated selection redraw preserves
  manual axes limits.
- The context style bar is a fixed-height overlay surface, so tool/selection
  changes do not add or remove canvas layout height. Drag preview remains
  non-persistent until release; release creates one edit-session/canvas history
  entry and undo/redo restores the exact geometry.
- Focused interaction matrix: `109 passed`; remaining ChartEditor-related
  modules: `156 passed`; targeted legacy ChartEditor drag/undo/static checks:
  `7 passed`. Structured verifier passed for task card
  `docs/agent/tasks/2026-07-20-editor-interaction-reliability.md`.
- Known limitation remains the pre-existing Windows Qt access violation in the
  legacy `LayerTreeItem.setData()` compatibility path when the full
  `tests/test_chart_editor*.py` set is combined; stable focused batches pass.
- Local checkpoint commit: `132bf912` (`fix(editor): stabilize direct canvas
  interactions`). The explicit finish metadata is being merged to local
  `main`; no push is performed. All pre-existing untracked drafts/diagnostics
  remain intentionally untouched.

## Local finish verification — recorded 2026-07-20

- The completed editor-workflow branch and the local `main` worktree both
  resolve to `5e973d30`; the feature code is already locally integrated.
- Fresh structured verification passed with
  `python scripts/verify.py --task docs/agent/tasks/2026-07-20-editor-workflow-completion.md --changed --types`.
- Fresh default verification passed with
  `python scripts/verify.py --changed --types`; the quality gate reported
  `282 passed` and the preprocessing optimization gate reported `103 passed`.
- The focused completion matrix reported `51 passed`. Existing untracked
  design drafts, acceptance notes, temporary diagnostics, and legacy worktrees
  were intentionally left untouched; the worktree remains unregistered and is
   not eligible for automatic removal.

## Editor visual polish — completed 2026-07-20

- The editor shell now gives the canvas expanding space, uses a readable
  text-under-icon tool rail with grouped history/export actions, keeps all
  inspector tabs visible without scroll arrows, and exposes selection actions
  beside the object/layer tree.
- Focused visual/editor tests pass (`34 passed`); `tests/test_chart_editor.py`
  passes independently (`238 passed`) and the workflow suite passes
  independently (`19 passed`). Structured and default changed/type verifiers
  both pass with quality gate `282` and preprocessing gate `103`.
- A combined Qt-heavy invocation can still trigger a Windows access violation
  inside the pre-existing `LayerTreeItem.setData` compatibility path; this is
  recorded in the task card and is not claimed as resolved by this UI-only
  slice.
- Local finish sequence is ready: source branch `codex/origin-editor-usable-controls`
  is at `943411b2`, target `main` is clean at `0086ca40`, and the source-only
  untracked drafts and diagnostics remain intentionally untouched.

## Origin-like editor mainline integration — completed 2026-07-20

- Integrated the tested Origin-like annotation and generated-canvas
  interactions into `codex/origin-editor-usable-controls` without replacing
  the current object tree, batch editing, comparison, templates, export, or
  canonical GUI launcher.
- Text, line, arrow, curve, and rectangle creation now share direct-canvas
  preview/commit behavior; static and generated geometry handles remain
  undoable and export excludes editor overlays.
- Fixed the release router so generated `plot_series` point edits and legend
  drags commit through the preview transaction instead of falling back to the
  legacy document-diff path, which had discarded preview-only changes.
- Verification evidence: `238 passed` for `tests/test_chart_editor.py`,
  `120 passed` for the remaining focused Origin-like editor/layout/workflow
  matrix, `66 passed` for the generated drag/geometry/render/core matrix;
  Ruff, compileall, and `git diff --check` passed. The prescribed structured
  verifier is the final repository gate for this checkpoint.
- Task card: `docs/agent/tasks/2026-07-20-origin-like-editor-mainline-integration.md`.

## Chart editor workflow completion — completed 2026-07-20

- Completed the remaining editor workflow slice on
  `codex/origin-editor-usable-controls`: structured corrupt/unsupported
  document diagnostics, undoable horizontal/vertical distribution and
  visibility, a hierarchical layer tree with legacy row compatibility, context
  menus and scoped shortcuts, data-free chart templates, format painter,
  previewed atomic batch editing, side-by-side chart comparison, working-vs-
  published revision diff, and named export presets.
- Focused editor/core/gallery regression command passed with `354 passed`.
- Structured verifier passed:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-20-editor-workflow-completion.md --changed --types`.
  Default verifier also passed:
  `python scripts/verify.py --changed --types`; quality-gate focused tests
  passed (`282`) and preprocessing optimization tests passed (`103`).
- Known limitation: the revision comparison UI presents normalized document
  and asset-count differences; it does not perform a pixel-level image diff.

## Current checkpoint

- Worktree lifecycle manager added on 2026-07-20. Agent-owned worktrees can be
  registered, marked pending cleanup only after a clean Git state, archived into
  replayable WIP bundles, and removed only after branch/HEAD checks and a
  one-hour cooldown. Existing unregistered worktrees are intentionally retained.

- Unified GUI worktree launcher completed on 2026-07-20. The desktop launch path
  now uses `scripts/launch_gui.py` from the canonical `D:\PolyNexus`
  worktree; the launcher validates the imported package path, exposes branch
  and commit diagnostics, and preserves explicit worktree selection without
  guessing among isolated worktrees. Task card:
  `docs/agent/tasks/2026-07-20-unified-gui-worktree-launcher.md`. Focused
  launcher tests pass (6); the task-scoped verifier passes, including Ruff,
  compile, core quality (281), preprocessing optimization (103), memory, and
  whitespace checks; both system and bundled Python diagnostics resolve to
  `D:\PolyNexus\polynexus\__init__.py`.
- Final goal audit on 2026-07-19: the prescribed default verifier
  `python scripts/verify.py --changed --types` passes after all checkpoints;
  memory, compile, core quality gate (281), preprocessing optimization gate
  (103), and whitespace checks are green. The broader
  `python scripts/verify.py --changed --types --full --boundary` was attempted
  and timed out after 244 seconds without emitting a failure diagnostic; this
  remains a verification limitation, not evidence of a pass.
- Editor tool shortcuts and complete alignment surface completed on 2026-07-19.
  Canvas-scoped V/T/L/A/R/Del shortcuts avoid intercepting text fields, while
  window-scoped save, project export, undo, and redo remain available. All six
  alignment modes are reachable from the selection-aware batch controls.
  Shortcut/layout/editor suite passes (249). Task card:
  `docs/agent/tasks/2026-07-19-editor-shortcuts-and-alignment-surface.md`.
- Editor icon toolbar and one-command drag transactions completed on
  2026-07-19. Toolbar actions now use deterministic vector icons with
  translated tooltips. Generated drag motion is preview-only while a session
  is active; release commits one `ReplaceObjectCommand`, then persists the
  result, while Escape restores the original snapshot. Full focused
  toolbar/transaction/drag/editor slice passes (252). Task card:
  `docs/agent/tasks/2026-07-19-editor-toolbar-and-drag-transactions.md`.
- Chart gallery search, sorting, batch export, and revision status completed on
  2026-07-19. Active gallery cards can be filtered by title/id/status, sorted
  by title or working/published revision, checked for selected batch export,
  and show working/published revision badges. The manifest-only boundary is
  unchanged. Focused chart gallery/viewer suite passes (26). Task card:
  `docs/agent/tasks/2026-07-19-chart-gallery-search-sort-batch.md`.
- Undoable batch alignment and grouping completed on 2026-07-19. The core now
  supports left/center/top alignment plus group/ungroup as one `EditSession`
  command each, preserving geometry dimensions and rejecting locked or
  unsupported selections before mutation. ChartEditor exposes compact actions
  only for multi-selection. Focused batch/core/layout suite passes (31); the
  task-scoped verifier passes. Task card:
  `docs/agent/tasks/2026-07-19-batch-alignment-and-grouping.md`.
- Object tree search, multi-selection state, and locking completed on
  2026-07-19. The object tree now filters by id/name/type while retaining the
  background row, uses extended selection, and exposes ordered selected ids
  with the first id preserved for existing Inspector/canvas routes. Locking is
  an undoable `SetLockCommand`; locked objects continue to be selectable but
  existing capability gates reject normal edits. Focused object-tree/core
  selection suite passes (27). Task card:
  `docs/agent/tasks/2026-07-19-object-tree-selection-and-locking.md`.
- Editor safety and self-contained project export completed on 2026-07-19.
  `ChartEditor.closeEvent()` now offers Save/Discard/Cancel, keeps dirty state
  on failed or exceptional saves, and does not prompt for clean editors. The
  core `figure_project_bundle` service creates an atomic relocatable
  `.pnproject.zip` containing the normalized document, figure assets, resolved
  sources, and SHA-256 manifest; it refuses existing destinations and rejects
  missing or run-root-escaping sources. Focused close/package/editor-export
  suite passes (28). Task card:
  `docs/agent/tasks/2026-07-19-editor-safety-and-project-export.md`.
- Chart viewer provenance and historical recovery completed on 2026-07-19.
  `ChartViewer` now consumes selected figure entry/document context and a
  figure-specific data resolution, with raw-data compatibility only when no
  persisted source metadata exists. Run-relative CSV sources resolve through
  the entry run root; missing sources produce an explicit warning while the
  image preview remains usable. The recovery action now uses `ChartGallery`,
  preserving the active manifest gallery. Focused provenance/viewer/recovery
  suite passes (43); the task-scoped verifier passes, including quality gate
  (281) and preprocessing optimization gate (103). Task card:
  `docs/agent/tasks/2026-07-19-chart-data-provenance-and-recovery.md`.
- Chart gallery visual polish completed on 2026-07-19: the three-column layout remains, `ChartThumbnail` now has a unified card surface, and the blue border follows hover while selection uses a low-emphasis theme focus color. Task card: `docs/agent/tasks/2026-07-19-chart-gallery-visual-polish.md`; focused suite: 17 passed. The verifier tooling is restored and the prescribed changed/type command passes.
- Chart gallery header polish completed on 2026-07-19: the plots page now has a localized gallery title/count, grouped recovery action, and a theme-aware toolbar container; the focused chart/gallery/startup slice passes 21 tests. The verifier tooling is restored and the prescribed changed/type command passes.
- Follow-up fix completed on 2026-07-19: `ChartGallery.retranslate()` now updates filters, actions, badges, and card labels after language changes, removing the mixed Chinese/English gallery state. Focused chart/gallery/startup slice passes 25 tests; restart is required for an already-running GUI process.
- OriginLab integration is implemented and locally merged into `main`. The
  ChartEditor top export menu exposes Origin, and run-relative generated-figure
  CSV sources resolve through the gallery `run_root`; native export now shows
  and activates the Origin graph when available; capability probing also reads
  the Windows user environment registry when the running GUI has a stale
  `os.environ`; object documents retain the editable Origin mode while static
  documents retain visual-fidelity fallback, and native layers rescale after
  plots are added; all series now reuse one native Graph; source axis scales
  are forwarded, including logarithmic Y; see decisions `0010` and `0011`.
- The local `main` fast-forward merge is `583709ad`; the branch is not pushed.
- The focused Origin/editor verification currently passes: 44 Origin-related
  tests plus the new 16-test source/style fidelity slice, 3 GUI-startup checks,
  and 238 ChartEditor regression tests. The
  prescribed verifier command passes after restoring the workflow scripts and
  normalizing the legacy decision metadata; the evidence is recorded in the
  current verifier-restoration checkpoint.
- A live style smoke export through the configured OriginPro installation
  returned `success/originpro` for a synthetic five-plot document and was
  inspected in-process: one Graph, five plots, logarithmic Y, document colors,
  five 1.2-point display line widths, 0.8-point `x/x2/y/y2` frame axes, five
  source sheets, and five sample names. The generated native `.opju` remains
  owned by Origin until that application closes; no user-owned Origin process
  was closed.
- Native multi-series export now binds each plot through `data_ref` instead of
  reusing the last imported dataframe; axis labels fall back to the first
  object-document panel, and plot presentation uses Origin's LabTalk width
  units. The task card is
  `docs/agent/tasks/2026-07-19-origin-single-graph-fidelity.md`.
- Follow-up Origin label polish converts Matplotlib mathtext to Origin-safe
  Unicode (`q (nm⁻¹)`, `I (a.u.)`) at the native adapter boundary; the focused
  Origin suite is now 18 passed. The task card is
  `docs/agent/tasks/2026-07-19-origin-label-display-polish.md`.
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

- HTML presentation recording controls are now implemented on the current
  branch. The deck has a browser Fullscreen API button with F11 fallback, a
  clean recording view that hides presentation chrome while keeping keyboard
  navigation and captions, and a presenter mode opened from the main deck as
  `?presenter=1`. The presenter window receives current-slide state through
  `BroadcastChannel` with `postMessage` fallback and shows current/next slide
  previews, notes, slide index, and an elapsed timer. Presenter arrow keys and
  previous/next buttons now send a single reverse command to the main deck, so
  both windows stay synchronized without double-advancing. The slideshow
  window can be shared alone in Tencent Meeting. Focused presentation tests
  pass (`7 passed`) and the repository verifier passes with quality `297` and
  preprocessing `106`. Visual browser inspection remains limited by the
  in-app browser localhost policy. The related files are
  `docs/presentations/polynexus-overview.html` and
  `tests/test_html_presentation.py`.

- The presenter view now uses the full 46-page narration array for both the
  private notes panel and the `N` notes panel. Its three-column layout gives
  the on-air slide a 2.3fr share, keeps the next slide as a compact .48fr
  preview, and reserves 320px for notes and controls. This is tuned for
  sharing only the slideshow window in Tencent Meeting; direct browser
  preview remains the final visual check.

- PolyNexus HTML presentation deepening is implemented on the current branch.
  The 46-slide deck now explains the SAXS input and preprocessing chain,
  q-conversion dependencies, background/normalization, smoothing and mask
  boundaries, simulated ideal/problem curves, six SAXS methods, independent
  quality states, and partial sasmodels coverage. The AI chapter now shows
  LLM API + RAG (Chroma / BM25) + structured JSON + deterministic orchestrator,
  SAXS `PreprocessIntent`, candidate replay, physical/quality gates, shadow and
  confirm-only review, user confirmation, and offline mock degradation. Focused
  presentation tests pass (`6 passed`) and inline JavaScript parses; real
  browser preview was attempted but the in-app browser blocks localhost URLs.
  The local preview server is available at
  `http://127.0.0.1:8765/docs/presentations/polynexus-overview.html` while the
  current process remains active. See
  `docs/superpowers/plans/2026-08-03-polynexus-presentation-saxs-ai-depth.md`.

- SAXS Guinier source-index integrity is verified and ready for its local
  checkpoint on 2026-07-28. Duplicate, negative, and non-integral source
  mappings now remain explicit and force diagnostic sequence evidence; valid
  temperature sorting such as `[1, 0]` remains Trend and records reordered
  provenance. TDD RED was `4 failed`; the sequence/temperature propagation
  matrix passed `25`. Structured verification passed with quality `287` and
  preprocessing `106`; storage dry-run reported `490` artifacts, `0` eligible,
  `490` protected, and `0` removed. The exact SAXS matrix timed out after `124`
  seconds without a summary and is not claimed as passed. The pre-existing
  full/boundary verifier was left untouched. See
  `docs/agent/tasks/2026-07-28-saxs-guinier-source-index-integrity.md`.

- SAXS anisotropy non-finite input fail-closed is verified and ready for its
  local checkpoint on 2026-07-28. The
  normalization boundary now rejects non-finite values in `I_2d`, `q`, `chi`,
  `q_1d`, or `I_1d` with `orientation_input_nonfinite`; no repair, inference,
  or rescue is performed, and the existing orientation evidence path degrades
  to strict JSON-safe `Unusable`. TDD RED reproduced `15 failed, 10
  deselected`; GREEN passed `15 passed, 10 deselected`. The focused 2D/strain/
  batch matrix passed `69 passed`. Structured verification passed with quality
  `287` and preprocessing `106`; Ruff, compile, type baseline, whitespace, and
  task checks also passed. Storage dry-run reported `484` artifacts, `100`
  eligible, `384` protected, and `0` removed. The exact SAXS matrix timed out
  after `124` seconds without a pytest summary and is not claimed as passed.
  The explicit allowlist checkpoint contains only this task's source, test,
  task, spec, plan, and active-work files. See
  `docs/agent/tasks/2026-07-28-saxs-anisotropy-nonfinite-fail-closed.md`.

- SAXS real Static/Temperature/Strain acceptance-audit surface consistency is
  checkpointed. The Figure/Manifest provenance audit is refreshed from the
  final validation audit, while the Temperature validation failure remains
  diagnostic and unchanged. Current focused real replay is `3 passed`; the
  structured verifier is green with quality `287` and preprocessing `106`.
  Storage reporting remains dry-run only (`460` artifacts, `49` eligible,
  `411` protected, `0` removed). See
  `docs/agent/tasks/2026-07-28-saxs-real-acceptance-audit-surfaces.md`.

- SAXS real static/temperature/strain Workbench acceptance is automated-green
  on 2026-07-27. The current-HEAD full/boundary verifier passed `2662` tests
  with `10` warnings, including quality `282`, preprocessing `103`, compile,
  whitespace, and boundary checks. External real bundles remain outside the
  repository and all three register `quality_evidence.json`. Rendered main
  figures were inspected for basic rendering; the strain heatmap appears
  close to saturation and the temperature bundle retains its validation error.
  These are explicit scientific-review signals, not sign-off. The next action
  is restarted-GUI review plus expert review of temperature/strain meaning;
  AI model calls, candidate reruns, calibration, and publication authorization
  remain disabled/open. See
  `docs/agent/tasks/2026-07-27-saxs-real-workbench-acceptance.md`.

- NMR real-engine evaluation bridge is implemented on the current worktree. The
  EvalRunner now recognizes `nmr.liquid_h`, `nmr.liquid_c`, `nmr.solid_h`, and
  `nmr.solid_c`, applies scoped config aliases, and emits peak shifts, peak
  counts, SNR, Xc/assignment status, fit quality, and engine/submodule
  provenance. The bridge regression and the existing IR/DSC/SAXS/WAXS eval /
  publication matrix pass (`12 passed`); task-scoped verifier passed and the
  atomic checkpoint is `4721b16`. The repository still lacks a registered NMR
  vendor/real regression source, so this is not scientific real-data
  acceptance. See `docs/agent/tasks/2026-07-25-nmr-real-eval-bridge.md`.
- History restore now rehydrates the manifest-only Gallery after restoring a
  run's `output_dir`; a real IR FigurePipeline manifest is visible with its run
  and figure IDs after restore. Focused history/persistence/editor matrix passed
  (`32 passed`); task-scoped verifier passed with quality gate `282` and
  preprocessing gate `103`. Atomic checkpoint is `5ad3ac9`. See
  `docs/agent/tasks/2026-07-25-history-gallery-restore.md`.
- Export bundles now declare `figure_runs: metadata/runs` and
  `active_figure_run: metadata/active_run.json`; the source active pointer is
  copied when present and README names the manifest-backed run section. Focused
  export/GUI matrix passed (`15 passed`); task verifier passed with quality gate
  `282` and preprocessing gate `103`. Atomic checkpoint is `254b849`. See
  `docs/agent/tasks/2026-07-25-export-figure-run-provenance.md`.
- IR temperature-2D figure data now preserves numeric `temperature_C` and
  `time_min` columns and recipe-level label/stage/estimated-time/order-source
  metadata; missing numeric conditions remain NaN and no axis or role semantics
  changed. The 15-test IR provider/temperature matrix and task verifier passed
  with quality gate `282` and preprocessing gate `103`. Atomic checkpoint is
  `02f0b56`. See
  `docs/agent/tasks/2026-07-25-ir-temperature-frame-provenance.md`.
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

## SAXS tensile-aligned long-period tracking - checkpointed 2026-08-08

- Explicit `tensile_axis_deg` now drives diagnostic q/L tracking along the
  tensile axis and its transverse axis without replacing total `L_nm` or the
  fixed meridional/equatorial fields. Missing axis, canonical 2D payload, or
  support fails closed with explicit status/reason fields.
- Arbitrary-axis sectors use support and fractional chi-bin overlap weights,
  then the same normalization/smoothing stages as existing fixed sectors.
  Exact 90/0-degree sector matches reuse the fixed profiles after canonical
  validation, preventing discretized 36-bin chi maps from silently widening a
  requested 30-degree sector.
- Focused batch/result/orientation tests passed `175`; a read-only five-frame
  EDF smoke run with `q_bragg_max=1.0` showed exact tensile-to-meridional and
  transverse-to-equatorial equality at the configured 90-degree axis. The
  final structured verifier passed with quality `297` and preprocessing `157`.
  Independent review is `0 Critical / 0 Important`; the explicit allowlist was
  checkpointed locally with no push or merge.
- Task card:
  `docs/agent/tasks/2026-08-08-saxs-tensile-aligned-peak-tracking.md`.

## Suggested next candidates

- SAXS I(q)q² gallery label regression is fixed on 2026-08-04. The public
  figure polish helpers previously converted specialized `I(q) q^2` labels to
  generic `$I$ (a.u.)`, making the new Kratky previews look like raw intensity.
  Both static/shared and public provider polish paths now preserve an explicit
  `I(q)q^2` label; source objects remain bound to `intensity_q2`. Focused SAXS
  figure/document/evidence tests pass (`85 passed`, 4 pre-existing font
  warnings). A new run is required to regenerate historical preview assets.
  See `docs/agent/tasks/2026-08-04-saxs-iq2-axis-polish-regression.md`.

- Editor legend-box task completed on 2026-07-24 at `10d4c61`: generated
  legends now retain their rendered layout on selection, expose a transient
  non-exported Origin-style box with four handles, persist corner-resize W/H
  through one undoable style transaction, and surface the same geometry in the
  inspector. Evidence: task card
  `docs/agent/tasks/2026-07-24-editor-legend-box.md`; focused matrix `272
  passed`, changed-file verifier plus quality gates `282 passed` and `103
  passed` using a dedicated pytest base temp directory.

1. Add incremental Ruff checks for changed files, then ratchet toward full-repo
   cleanliness.
2. Add a small index or search adapter for memory entries only after the Markdown
   source of truth is being maintained consistently.
3. If the startup target must improve beyond the current approximately 2.7-second fresh-process probe, separately evaluate scientific-stack packaging and lazy technique-registry loading.

## Update protocol

Every active task should record its status, blocker, next action, and evidence
link here when that information will matter to a later agent.

## Project technique adapters V2 - checkpointed 2026-08-13

- Registered `project.technique.single.v1` routes one IR, WAXS, or SAXS input
  through existing engines and emits validated ARS evidence packages.
- External PA6 FTIR, WAXS, and SAXS inputs were replayed read-only through
  project-local raw junctions. SAXS retains `background_unknown`; all three
  packages remain `review_required`.
- Replay plans bind indexed source hashes; IR aliases and directory source
  hashing are covered; duplicate derived figure names are disambiguated.
- Acceptance: `docs/acceptance/2026-08-13-project-technique-adapters-v2.md`.
- V3 remains open for multi-file series and cross-technique package relations.

## Project technique series V3 - checkpointed 2026-08-13

- Registered `project.technique.series.v1` executes same-technique IR/WAXS/SAXS
  files as deterministic ordered steps. Each step binds an `artifact_index` and
  source order; mixed techniques and one-file series requests fail closed.
- Agent workflow execution now resolves indexed artifacts instead of collapsing
  same-technique artifacts to the last file.
- Packages add conservative `run_part_of_request` relations when no explicit
  relations are supplied. No sample, batch, formulation, or cross-technique
  identity is inferred.
- Real PA6 FTIR replay used a read-only raw junction and three CSV files;
  plan was `ready`, run/package `review_required`, and three evidence items were
  produced. Acceptance: `docs/acceptance/2026-08-13-project-technique-series-v3.md`.
- V4 remains open for cross-technique package assembly and retry/resume.

## Project workflow recovery V4 - checkpointed 2026-08-13

- `ProjectWorkflowService.resume(run_id)` validates persisted request/plan
  manifests and current source hashes before replaying the same plan.
- `approve_context_correction()` creates a new request with explicit approval,
  approver, and correction metadata; raw inventory facts remain unchanged.
- Writing-input includes approved corrections as provenance metadata only.
- Focused recovery/project matrix passed `28`; acceptance:
  `docs/acceptance/2026-08-13-project-workflow-recovery-v4.md`.
- Final cross-technique ARS integration and local mainline closeout remain open.

- Multi-run packaging now projects `cross_technique_evidence_set` or
  `technique_series_evidence_set` relations from explicit package membership;
  it never infers sample identity.

## AI-native project entrypoint - checkpointed 2026-08-14

- `project-workflow analyze-project` now provides one AI/ARS-facing route from
  a project directory and question to runs, figures/tables, and an evidence
  package; callers no longer orchestrate inspect/plan/run/package manually.
- Output separates `computation`, `data_quality`, and `publication`, retaining
  raw reason codes and review limits for machines while avoiding a misleading
  single "failed" state for users.
- Header-based FTIR discovery recognizes `Wavenumber`/`Absorbance` files where
  the folder name lacks `IR`; same-stem SPC/SPA companion files are skipped to
  avoid duplicate analysis.
- Acceptance: `docs/acceptance/2026-08-14-ai-native-project-entrypoint.md`.

## AI project candidate groups - checkpointed 2026-08-14

- Mixed project directories now produce filename-derived candidate groups before
  unscoped analysis. Questions that uniquely identify a group select it; other
  questions return `candidate_group_selection_required` without starting a
  provider run.
- Real PA6 FTIR discovery found PA6 JW (22 CSV), PA6 SW (23 CSV), and PA6 250 C time
  (3 CSV) candidates through the read-only junction. All candidate semantics
  remain `inferred_from_filename`, not verified laboratory identity.
- Acceptance: `docs/acceptance/2026-08-14-ai-project-candidate-groups.md`.

## ARS-selected FTIR group figure candidates - checkpointed 2026-08-14

- ARS can supply one or two candidate group IDs and a figure intent to
  `analyze-project`; invalid selection blocks before any provider execution.
- The V1 FTIR renderer produces an overlay only for selected sources, returns
  no more than two main figure candidates, and produces an `Xc_pct` trend only
  when every condition has an explicit finite, method-bearing provider value.
- Candidate metadata and assets are copied into the immutable evidence package;
  provider single-file outputs remain traceable internal evidence.
- A three-file PA6 JW read-only render smoke produced an inspected overlay;
  the trend correctly remained absent because no provider metrics were run.
- Acceptance: `docs/acceptance/2026-08-14-ars-selected-group-figure-candidates.md`.

Post-review repair: comparison is now best-effort. Two selected FTIR groups run
their providers and produce a comparison overlay when usable spectra exist;
unmatched conditions suppress only difference output. Comparison trends retain
provider methods and mark method differences as limitations. Package candidate
paths are rewritten to package-relative paths; provider single-file figures
remain excluded when candidate figures are supplied.

Flexible comparison extension is verified on 2026-08-14: two-group overlays,
condition-matched difference plots, unmatched-condition warnings, and mixed
metric-method limitations are covered by the project workflow matrix (`63
passed`) and structured gates (`303` quality, `157` preprocessing).

## Cross-technique project evidence index - checkpointed 2026-08-14

The AI-facing project package now writes `techniques.json` and a matching
`manifest.json` projection. It indexes explicit run IDs, evidence counts,
statuses, and limitations by technique for mixed IR/WAXS/SAXS/DSC packages;
it does not infer sample identity or scientific conclusions. Focused entrypoint
and package coverage passed `15`.

Read-only PA6 FTIR+WAXS replay completed in
`D:\PolyNexus-pa6-cross-technique-smoke-20260814`: three IR files and one WAXS
file produced one `review_required` package with explicit cross-technique
membership. Provider limitations remain; no scientific merge was inferred.

## ARS writing evidence handoff - checkpointed 2026-08-14

Packages now emit `writing-evidence.json` and a technique-grouped writing
section. The handoff preserves observed results, source runs, figures, tables,
supported interpretations, disallowed conclusions, and limitations without
drafting scientific prose or adding cross-technique claims.

Writing evidence now rewrites copied figure/table references to package-relative
paths and exposes finite scalar `observed_metrics` alongside full observed
results. This was verified with the project writing/figure matrix (`32 passed`)
and structured gates (`303` / `157`).

## Dual-entry workbench contract - checkpointed 2026-08-13

- Product direction is now explicit: PolyNexus is one AI-controllable and
  independently usable polymer research workbench, not an AI-only tool or a
  GUI-only application.
- AI/Codex and GUI operate on the same project, run, chart, evidence, and
  export objects. Future shared-object changes require focused producer and
  affected-consumer verification; the full GUI or repository matrix is not the
  default proof for a scoped task.
- Workflow assets are `docs/agent/workflow.md`, `definition-of-done.md`,
  `task-template.md`, and `testing-matrix.md`. Task card:
  `docs/agent/tasks/2026-08-13-dual-entry-workbench-contract.md`.

## Unified canonical evidence provenance - checkpointed 2026-08-13

- The project workflow now requires a replayable canonical template for DSC,
  IR, SAXS, and WAXS.  DSC keeps its existing isothermal converter; IR/SAXS/
  WAXS use deterministic source-content envelope converters and do not change
  existing provider algorithms.
- Removed/tampered templates make the route invalid and source changes fail
  replay before the provider can execute.  Supported IR directory inputs use a
  deterministic directory content envelope.
- Package-wide workflow limits now stay in `limitations.json`; individual
  technique writing items retain only their own step reasons and
  `human_review_required`, preventing cross-technique limitation leakage.
- External PA6 four-technique replay wrote
  `D:\PolyNexus-pa6-four-technique-smoke-20260814\.polynexus\evidence\canonical-provenance-replay-v001`.
  All four techniques are `review_required` and include template/conversion
  provenance.  Verification and scientific boundaries are recorded in
  `docs/acceptance/2026-08-13-unified-canonical-evidence-provenance.md`.

## Writing metric provenance - checkpointed 2026-08-13

- Project evidence packages now write `citation-metrics.json`, a deterministic
  numerical ledger linking each documented provider value to its evidence item,
  run, raw-source hash, method, source locator, package-relative assets, status,
  and writing eligibility.  `writing-evidence.json` links metric IDs back to
  each technique evidence item, while `writing-input.md` directs ARS to the
  ledger.
- Real PA6 four-technique replay is recorded in
  `docs/acceptance/2026-08-13-writing-metric-provenance.md`.  DSC values are
  Results candidates but remain review-required; FTIR crystallinity stays an
  uncalibrated index, while SAXS and low-support WAXS metrics remain diagnostic.
- This adds no scientific calculation and makes no publication conclusion.

## ARS Results/Discussion handoff - checkpointed 2026-08-13

- Packages now emit and validate `ars-writing-input.json`.  It is a versioned
  evidence map with technique sections, source/run/evidence links, Results
  candidate metric IDs, Discussion-only diagnostic IDs, figures/tables,
  prohibited conclusions, package limitations, and mandatory human review.
- Real PA6 four-technique replay is recorded in
  `docs/acceptance/2026-08-13-ars-writing-handoff.md`: 42 Results candidates,
  54 diagnostic values, and 6 review items across DSC/FTIR/SAXS/WAXS.
- This is an ARS preparation contract, not an automatic manuscript writer;
  literature, narrative, and final scientific review remain in ARS/human scope.

## Evidence package view model - checkpointed 2026-08-13

- `EvidencePackageView` now loads the immutable package into technique-neutral
  DTOs for package status, technique membership, evidence rows, metric
  provenance, package-relative assets, limitations, and human-review actions.
  The GUI adapter reads only this DTO.
- Loader validation requires writing evidence, citation metrics, and ARS
  Results/Discussion metric partitions to agree exactly, preventing a
  diagnostic metric from reaching a Results presentation path.
- Real PA6 package loading is recorded in
  `docs/acceptance/2026-08-13-evidence-package-view.md`.

## Evidence package dialog - checkpointed 2026-08-13

- `EvidencePackageDialog` provides read-only Overview, Evidence, Metrics, and
  Review tabs directly from the technique-neutral `EvidencePackageView` DTO.
  It cannot invoke provider analysis or modify package JSON.
- The final four-technique PA6 package opened with 96 metric rows and six
  human-review rows. Acceptance:
  `docs/acceptance/2026-08-13-evidence-package-dialog.md`.

## PA6 AI-native loop final audit - 2026-08-13

- Fresh real PA6 replay to `final-pa6-e2e-audit-v001` proves the complete
  project route: DSC/FTIR/SAXS/WAXS canonical replay, immutable package,
  citable provenance ledger, ARS Results/Discussion handoff, and technique-
  neutral GUI view loading.  Full evidence is in
  `docs/acceptance/2026-08-13-pa6-ai-native-e2e-audit.md`.
- Final project-focused matrix passed 62 and package-boundary matrix passed 11.
  The structured quality/preprocessing gates passed 303/157.
- Full repository boundary test run is not green: 3907 passed, 31 failed, 21
  skipped. Remaining failures are unrelated GUI/SAXS historical paths; no
  claim of release-wide green status is made until that separate backlog closes.

## Agent-native PA6 project evidence loop - checkpointed 2026-08-12

- The project-local workflow now supports `inspect`, `plan`, `run`, and
  `package` through JSON-safe contracts and the CLI command
  `polynexus project-workflow ...`.
- The DSC vertical slice creates immutable `.polynexus/evidence` snapshots,
  preserves provider review limits, validates source/run hashes, and never
  copies raw inputs.
- External PA6 `PA6-DWJJ.txt` replay passed through a read-only project `raw`
  junction. Acceptance evidence is recorded in
  `docs/acceptance/2026-08-12-agent-native-pa6-project-evidence-loop.md`.
- FTIR/SAXS/WAXS adapters remain separate follow-up work; the current workflow
  reports `converter_unregistered` instead of fabricating analysis.
