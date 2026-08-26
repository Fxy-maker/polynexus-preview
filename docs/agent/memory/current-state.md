---

## Finite capability execution checkpoint (2026-08-26)

The shared canonical layer now has a finite capability registry/executor for
1-D spectrum/scattering measurements and `ComputeRun.capability_items` for
immutable item results. This is an additive skeleton: existing providers and
entry points still execute as before. The next boundary is routing canonical
templates through the executor, then adding DSC `thermal_program.v1`; do not
remove legacy paths until consumer migration and six-sample replay are green.
Task: `docs/agent/tasks/2026-08-26-capability-execution.md`.

## Shared ComputeRun canonical routing checkpoint (2026-08-27)

The common Quick Analysis/single-file CLI `ComputeRunService` now carries
generic IR/SAXS/WAXS canonical templates and finite capability items. Generic
mapping ambiguity blocks before provider execution; vendor formats continue
through compatibility envelopes. Batch, GUI persistence, generic file-backed
Agent/Codex workflow steps, and registry-driven DSC file runs now migrate new
runs through the shared `ComputeRun` projection. DSC keeps the old template ID
as a compatibility alias.

## AI-tuning bootstrap ComputeRun checkpoint (2026-08-27)

The initial run for a valid AI-tuning source now uses `ComputeRunService`,
retains the in-memory engine for controlled candidate rounds, and publishes a
JSON-safe `compute_run` projection in the final report. Empty output strings
remain analysis-only at the provider boundary. Missing synthetic paths remain
compatibility-only; ambiguous canonical mappings fail closed. Legacy candidate
round adapters and full-boundary release review remain open.
AI-tune CLI persistence also stores this projection alongside the legacy
summary fields.

## Agent prevalidated-template reuse checkpoint (2026-08-27)

Agent/Codex replay-validated canonical templates are now reused directly by
`ComputeRunService`, avoiding a second conversion before capability execution.
The Agent `InputArtifact` identity algorithm is aligned with Compute's
`RawArtifact` identity, so source-bound templates no longer false-block when
crossing the shared boundary. Hash, technique, and template validation remain
mandatory; directory compatibility adapters and legacy fields remain
unchanged.

## AI-tune plan canonical-link checkpoint (2026-08-27)

When a valid AI-tuning report contains a shared `ComputeRun` canonical
template, the generated adaptive `AnalysisPlan` now references that same
template identity and conversion version, with source/content hashes retained
when present. Reports without a usable projection continue to use the legacy
compatibility template; candidate-round execution remains unchanged.

## Product contract (2026-08-13)

PolyNexus is an AI-controllable polymer research workbench that users can also
operate independently. AI/Codex and GUI entry points share project, run, chart,
evidence, and export objects. Canonical conversion and deterministic analysis
own scientific values and provenance; AI and GUI are consumers or authorized
editors of public contracts, not alternate analysis systems. See
`docs/agent/workflow.md` and `docs/agent/definition-of-done.md`.

## Token-efficient agent policy (2026-08-13)

Agents begin with concise task/memory indexes, public contracts, and scoped
searches, then expand source or logs only when required by evidence. Passing
command output is summarized, not copied into memory. This policy does not
reduce required verification or constrain broader inspection for architecture,
security, scientific semantics, release work, or repeated failures. See
`docs/agent/workflow.md` and `docs/agent/testing-matrix.md`.

## GUI import and AI-panel performance (2026-08-09)

The import work-memory refresh now uses compact sample/batch counts and the
latest run header, with narrow projections and ordering indexes. It no longer
enumerates all batch runs; only one selected run is hydrated if metric text is
needed. The Results comparison selector uses bounded run headers and preserves
same-sample priority through relational header fields. Opening comparison
hydrates only the selected baseline. Structured verification passed quality
`303` and preprocessing `157`; the broad persistence suite retains 12
pre-existing header-only History assertion failures outside this scope.
Task card: `docs/agent/tasks/2026-08-09-gui-import-ai-panel-performance.md`.

## GUI performance recovery (2026-08-09)

The current worktree contains a scoped responsiveness checkpoint in progress:
history lists read indexed headers instead of hydrating every run JSON, selected
records/comparison/export hydrate on demand, GUI logs are timer-batched and
bounded to 500 blocks, completion defers only the History redraw, and SAXS
records load/preprocess/analyze/plot durations for diagnostics. Focused and
structured verification are green; the local checkpoint commit is pending.
The intentional comparison-header cap is 500 records per batch.

Task card: `docs/agent/tasks/2026-08-09-gui-performance-recovery.md`.

## SAXS AI tuning and stability decision repair (2026-08-08)

The AI-tuning button now projects one confirmation-only SAXS stability flow:
action-specific symptoms select candidate dimensions, deterministic seeded LHS
plus bounded refinement evaluates only effective perturbations, and the GUI
shows platform, perturbation intervals, cross-frame continuity, and orientation
coverage. SAXS never applies a stability candidate unattended.

Confirmation identity now rejects undeclared selected-config changes, truthy
non-boolean safety fields, and conflicting canonical modes. Background scale is
excluded until production owns real background q/I arrays; mask dilation is
active only for a non-empty consumed mask. Out-of-range numeric baselines fail
closed. Continuity allows smooth strong curvature but rejects internal and
endpoint isolated jumps, including sign reversals. Missing orientation metrics
in any plateau trial contribute zero aggregate coverage.

Fresh cumulative coverage passed `257` tests with 7 existing geometry warnings.
Structured verification passed Ruff/compile/whitespace, quality `297`, and
preprocessing `156`. Bayesian optimization, unattended SAXS acceptance,
absolute calibration inference, and scientific merge approval remain outside
this checkpoint. Task card:
`docs/agent/tasks/2026-08-07-saxs-ai-stability-decision-repair.md`.

## SAXS orientation evidence projection (2026-08-08)

Per-frame strain rows now publish axis/source, harmonic strength/significance,
effective bins, azimuthal coverage, `orientation_cos2_avg`, and isotropic
baseline in Diagnostics. These remain detector-plane diagnostics; effective
tensile-axis Herman gating is unchanged. See
`docs/agent/tasks/2026-08-08-saxs-orientation-evidence-projection.md`.

## SAXS frame and orientation-tracking row separation (2026-08-07)

SAXS strain result presentations now build tabular rows only from real
`_batch_data` frames plus the existing batch summary. Flattened detached
orientation-track observations remain in the payload and nested diagnostic
evidence but no longer repeat strain values as fake frame rows with unavailable
file/L/q fields. Row counts remain dynamic for arbitrary sequence lengths.

Focused result-table coverage passed `59`; workbench/transport coverage passed
`29`; the read-only EDF 8 replay produced 5 primary rows and 6 detail/diagnostic
rows including the summary. Structured verification passed quality `297` and
preprocessing `107`. Acceptance is recorded in
`docs/acceptance/2026-08-07-saxs-results-frame-row-separation.md`.

## SAXS strain feature tracking closure (2026-08-06)

The strain series now owns one authoritative core result per frame and tracks
one credible total-profile lamellar peak with a hard 25% adjacent-q limit.
Once tracking is lost, later frames cannot restart it; failed/unseeded/lost
frames publish no authoritative L/lc/la/phi_c or feature-local orientation.
Orientation and detector-coordinate sector diagnostics share the accepted
total q. New strain outputs use `invariant_Q*`; history and stability readers
normalize legacy `Q_star*` inputs without republishing them. Explicit tensile
axis evidence is still required before an effective Herman factor is exposed.

Focused evidence is recorded in
`docs/acceptance/2026-08-06-saxs-strain-feature-tracking-closure.md`.

## SAXS sparse sector orientation boundary (2026-08-06)

The strain orientation path preserves sparse detector sector maps. Empty q/chi
bins are represented as NaN with zero support and are excluded from azimuthal
weights; a NaN in a supported bin is still an invalid canonical payload. A
successful raw Herman diagnostic does not imply a publishable/effective Herman
factor: explicit tensile-axis and orientation reliability gates remain required.

## SAXS stability map and scientific correctness - current checkpoint (2026-08-05)

- Implementation is complete under task card
  `docs/agent/tasks/2026-08-05-saxs-stability-map-scientific-correctness.md`.
- The stability service uses seeded Latin-hypercube exploration, bounded local
  refinement, typed config cloning, cache keys, plateau/bootstrap evidence, and
  per-candidate cross-frame continuity. The GUI preserves the candidate-only
  boundary until `PreprocessTransactionService` confirmation/finalization.
- Focused evidence is `94 passed, 6 warnings`; structured verification passed
  quality `297` and preprocessing `107`. The complete SAXS matrix returned
  `916 passed, 2 skipped, 14 failed` in 235.91s, with failures concentrated in
  real-data audit/EDF fixtures and legacy positive-only dirty-input assertions.
  Scientific review limits are calibration/contrast, lamellar interpretation,
  signed-source fixture semantics, auto-accept threshold policy, and
  publication promotion.

## SAXS scientific correctness repair - current checkpoint (2026-08-05)

- The 2026-08-04 SAXS repair task is implemented and has final acceptance
  evidence in `docs/acceptance/2026-08-04-saxs-scientific-correctness-repair.md`.
- Full SAXS verification passed `916 passed, 2 skipped, 15 warnings` in
  `575.81s`; focused repair/closure passed `30`, and the changed-contract
  matrix passed `177`.
- The implementation preserves signed source profiles, uses positive-only
  derived fits, enforces q-unit provenance, isolates frame geometry, rejects
  ambiguous HDF5 datasets, and labels detector-plane orientation as projected
  2D diagnostics.
- Absolute contrast/calibration, lamellar interpretation, publication
  promotion, and historical figure regeneration remain human-review limits.

## SAXS scientific correctness closure - current checkpoint (2026-08-04)

- Documentation checkpoint `0f7bf06f` records the approved design, task card,
  and implementation plan for the 14 SAXS findings.
- The current worktree implements unit-invariant Porod crystallinity, correct
  Cooling phase semantics and acquisition order, signed corrected profiles,
  explicit positive-only fitting, total-profile strain metrics, declared I/O
  parity with typed HDF5/Nexus errors, explicit batch limits/provenance,
  evidence-gated figure eligibility, and diagnostic-only relative Q-star/void
  GUI fields.
- Fresh evidence so far: closure tests `9 passed`; focused SAXS/GUI/strain
  matrix `159 passed, 3 warnings`; quality gate `297 passed`; preprocessing
  gate `106 passed`; Ruff/compile/whitespace passed.
- Task verification is green. Fresh full/boundary reached pytest but timed out
  after 3600 seconds (`124`) without a summary, so it is not claimed as pass.
  Human scientific review remains open. Historical generated figures require
  regeneration after acceptance.

## Full-goal release evidence refresh (2026-08-01)

- The authoritative acceptance ledger records the SAXS 2D reviewer-context
  checkpoint `a9e0743` and independent full SAXS matrix `700 passed, 6
  warnings in 530.15s`, exit `0`.
- The latest full/boundary verifier remains incomplete after a 40-minute tool
  timeout (`124`, no pytest summary; child manifest `exit_code=3`). The project
  remains conditional because IR mapping, NMR solid-C, Joint, restarted-GUI,
  and owner release gates are not closed.
- Documentation checkpoint: `e295ad2`.

## SAXS 2D review context projection (2026-08-01)

- Checkpoint `a9e0743` adds a detached review DTO for existing 2D detector,
  geometry/mask, beam-center, orientation, gate, and scientific-review data;
  raw q/I, detector pixels, source paths, and unknown fields are excluded.
- Fresh focused coverage passed `58`; the complete SAXS matrix passed `700
  passed, 6 warnings in 530.15s`, exit `0`.
- This is evidence-context transport only; it preserves diagnostic and
  review-required states and does not authorize scientific or publication
  promotion.

## Historical test-storage name discovery (2026-07-31)

- `scripts/test_storage.py` now discovers the observed `full_boundary*`,
  `native_*_basetemp`, `gallery_*`, `saxs_*_matrix`, and `Saxs*` historical
  test directory families while rejecting `测试数据`, archive, review,
  evidence, and baseline names before cleanup planning.
- Focused storage coverage passed `39 passed, 1 skipped`; structured verifier
  passed quality `297` and preprocessing `106`, with task/memory/Ruff/compile/
  type-baseline/whitespace checks passing.
- The reviewed clean dry-run found `241` artifacts and `26,825,556,265`
  eligible bytes, removed `0`, with `0` protected-name candidates eligible.
- Explicit allowlist checkpoint: `a43e70e`; no `--apply` cleanup was run here.
- Separate authorized follow-up apply removed `98` historical test
  directories. A post-apply dry-run found `143` artifacts,
  `32,242,122,672` bytes total, and `19` remaining eligible zero-byte paths
  blocked by Windows `PermissionError`; no protected-name path was eligible.
  D: now reports about `120.15 GB` free.

## Results evidence wrap readability (2026-07-31)

- `WrappedEvidenceLabel` now retains Qt `heightForWidth` after the Results
  shrink policy is applied, while preserving exact source text and all
  evidence content.
- Focused Results/Workbench coverage passed `52`; structured quality and
  preprocessing gates passed `297`/`106`; native NMR solid-H/solid-C route
  recheck passed `2` with exit code `0`.
- The explicit six-file checkpoint is `5f737c2`; parallel memory and scratch
  changes remain outside that checkpoint.
- This is a presentation/layout checkpoint only. IR mapping remains
  diagnostic-only, NMR solid-C remains assignment-limited, Joint remains
  blocked pending scientific conflict review, and overall release remains
  conditional pending owner approval.

## SAXS strain dirty-frame post-processing (2026-07-28)

- `analyze_strain_series()` now routes only the reference/per-frame 1D
  invariant, strain phase, and void consumers through detached
  `sanitize_1d_profile()` survivors; original q/I still reach `analyze_single()`
  and retain raw quality actions.
- Focused strain/method matrix passed `9` tests; exact SAXS passed `428 passed,
  6 warnings`; task-scoped verification passed with quality `283` and
  preprocessing `106`. The fresh full/boundary result passed `2869 passed, 17
  skipped, 12 warnings` in `1686.81s`, exit code `0`; boundary audit passed.

## SAXS temperature dirty-frame post-processing (2026-07-28)

- `analyze_temperature_series()` now uses the existing deterministic sanitized
  q/I auxiliary profile for reference invariant/Bragg, per-frame invariant,
  and peak-intensity tracking. `analyze_single()` still receives original
  arrays, so `invalid_pairs_dropped`/`q_sorted` quality provenance remains
  attached to the frame.
- Focused dirty/empty regression is `2 passed`; exact SAXS is `425 passed, 6
  warnings`; task-scoped quality/preprocessing gates are `283`/`106` with
  Ruff/compile/type, memory/task, and whitespace passing. Fresh full/boundary
  verification passed `2869 passed, 17 skipped, 12 warnings` in `1686.81s`,
  exit code `0`; boundary audit passed.

## Fresh native all-mode route acceptance (2026-07-29, post Joint identity fix)

- The current checkout passed the Windows-native Qt route harness with `17
  passed, 15 warnings in 358.71s`, exit code `0`. It covered DSC `3`, SAXS `3`,
  WAXS `3`, IR `2`, NMR `4`, synthetic Joint `1`, and synthetic IR mapping `1`.
- The fresh post-fix capture directory
  `D:\PolyNexus_native_all_routes_capture_20260729_post_joint` contains 68 images (four
  surfaces per case). Each case exercised the real Editor Export action with
  the no-Origin PackageExporter fallback.
- Representative images show native Results/Gallery/History/Editor routes and
  live labels. Joint now shows the restored `PA6-A` identity while the
  synthetic route still has `No data loaded`; crowded NMR solid-C labels,
  synthetic IR mapping, and SAXS diagnostic /
  validation states remain explicit review limitations. Human visual,
  scientific, and final release gates remain open.

## Joint real-data transport acceptance (2026-07-29)

- Real DSC standard, SAXS static, and WAXS static engine outputs now have a
  focused acceptance test covering engine -> SampleDB -> Joint dataset/report
  -> Figure Manifest publication. The fresh test returned `1 passed, 1 warning
  in 14.86s`, exit code `0`.
- The focused Joint/NMR matrix returned `23 passed, 2 warnings in 14.83s`, exit
  code `0`. The task-scoped verifier returned exit code `0`, with quality `283`
  and preprocessing `106` passing, Ruff/compile/memory/task/whitespace checks
  passing, and no changed type-baseline targets selected.
- This proves real-data transport and source-run provenance only. Joint value
  interpretation, scientific conflict review, restarted-GUI review, and final
  publication/release approval remain open. Task card:
  `docs/agent/tasks/2026-07-29-joint-real-data-lifecycle.md`.

## SAXS Static publication gate binding (2026-07-28)

- Static `main` role assignment now consumes the existing explicit
  `paper_figure_candidate` gate. Missing authorization is SI; explicit
  rejection or analysis error remains Diagnostic. This strict parameter is
  Static-only so temperature/strain role behavior is unchanged.
- When Static has no Main definition, the provider preserves measured profile
  and diagnostic figures and records
  `no_publication_ready_figure=True` with reason
  `static_frame_publication_authorization_missing` in recipe parameters.
- Evidence: TDD RED covered missing and reliability-only authorization;
  focused `29 passed, 1 warning`; SAXS `423 passed, 8 warnings`; real
  walkthrough `3 passed, 12 deselected, 2 warnings`; final structured quality
  `283` and preprocessing `106` passed after the reliability-only ordering
  correction, with Ruff/compile/type/memory/whitespace checks passed. Fresh
  isolated full/boundary verification passed `2856 passed, 17 skipped, 14
  warnings` in `1365.15s`; quality `283`, preprocessing `106`, and boundary
  audit also passed. Implementation checkpoint is `63059d5`.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-static-publication-gate.md`,
  `docs/superpowers/specs/2026-07-28-saxs-static-publication-gate-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-static-publication-gate.md`.


## SAXS Workbench review evidence readability (2026-07-28)

- `build_saxs_results_presentation()` now keeps the existing risk and next-step
  section order but joins non-empty sections with newlines instead of spaces.
  This makes metric, Guinier, detector, data-quality, rescue, and condition
  evidence separately auditable while preserving the string consumer contract.
- The change is presentation-only: evidence content/reason codes, levels,
  physical gates, AI/rescue behavior, persistence, Figure/Manifest/Export, and
  input immutability are unchanged. RED was `1 failed`; focused consumers were
  `104 passed`; exact SAXS was `419 passed, 6 warnings`.
- Post-change full/boundary verification passed: `2851 passed, 17 skipped,
  12 warnings` in 1567.25s. Quality `283`, preprocessing `106`, compile,
  whitespace, and boundary audit passed. Task verifier also passed with Ruff,
  memory/task, and whitespace checks; explicit allowlist checkpoint:
  `6fe3128`.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-workbench-review-readability.md`,
  `docs/superpowers/specs/2026-07-28-saxs-workbench-review-readability-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-workbench-review-readability.md`.

## SAXS invalid temperature-time values fail-closed (2026-07-28)

- `analyze_temperature_series()` now converts a correctly-sized supplied
  `times` list elementwise through `_coerce_optional_float()`. Numeric strings
  remain valid; malformed or non-finite values no longer abort the frame
  analysis. All temperature frames and source indices remain aligned.
- When any supplied time is invalid, Avrami is explicitly recorded as strict
  JSON-safe `valid=False` with reason
  `temperature_time_axis_invalid_values`, and fitting is skipped. The existing
  `temperature_time_axis_length_mismatch` reason remains higher priority.
- No interpolation, positional-index substitution, physical threshold,
  rescue, AI, or publication-role behavior was introduced. RED was `1 failed`;
  focused GREEN was `25 passed`; exact SAXS was `418 passed, 6 warnings`.
- Structured verifier passed with quality gate `283`, preprocessing gate `106`,
  Ruff, compile, memory/task, and whitespace checks. Explicit allowlist
  checkpoint: `c07d49a`. Full/boundary verification is not claimed.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-temperature-invalid-time-values-fail-closed.md`,
  `docs/superpowers/specs/2026-07-28-saxs-temperature-invalid-time-values-fail-closed-design.md`,
  and
  `docs/superpowers/plans/2026-07-28-saxs-temperature-invalid-time-values-fail-closed.md`.

## SAXS mismatched temperature time axis fail-closed (2026-07-28)

- `analyze_temperature_series()` now detects a supplied `times` length mismatch
  before sorting. It keeps all temperature frames, uses an all-NaN internal
  time alignment only to prevent indexing errors, and records strict JSON-safe
  Avrami status `valid=False` with reason
  `temperature_time_axis_length_mismatch`. Positional frame indices are never
  treated as synthetic time values.
- Absent/correctly-sized time paths and temperature/Guinier analysis remain
  unchanged. RED was `1 failed`; focused GREEN was `24 passed`; exact SAXS was
  `417 passed, 6 warnings`.
- Invalid time elements and full/boundary repository verification remain open;
  structured verifier and checkpoint are to be recorded after the final docs
  update.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-temperature-time-axis-fail-closed.md`,
  `docs/superpowers/specs/2026-07-28-saxs-temperature-time-axis-fail-closed-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-temperature-time-axis-fail-closed.md`.

## SAXS invalid temperature-axis fail-closed boundary (2026-07-28)

- `analyze_temperature_series()` now converts each temperature through the
  existing `_coerce_optional_float()` helper. Numeric strings remain numeric;
  invalid or non-finite values become NaN while their frames/source indices
  remain present for existing sequence evidence to mark the axis invalid.
- No condition inference, interpolation, frame deletion, new threshold,
  physical gate, rescue, AI, or non-invalid path change was introduced. RED was
  `1 failed`; focused GREEN was `23 passed`; exact SAXS was `416 passed, 6
  warnings`.
- The separate mismatched-`times` `IndexError` is a known next boundary.
  Structured verifier and checkpoint remain to be recorded after the final
  documentation update; full/boundary verification is not claimed.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-temperature-invalid-axis-fail-closed.md`,
  `docs/superpowers/specs/2026-07-28-saxs-temperature-invalid-axis-fail-closed-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-temperature-invalid-axis-fail-closed.md`.

## SAXS empty temperature series fail-closed boundary (2026-07-28)

- `analyze_temperature_series()` now returns an explicit empty
  `TempSeriesResult` after existing length validation when no temperature
  frames are supplied. It initializes empty numeric/status tracks and reuses
  the existing sequence/metric builders, yielding `Unusable` evidence with
  `guinier_sequence_no_valid_frames` and `series_no_frames`.
- No interpolation, frame fabrication, transition inference, rescue, AI,
  threshold, physical-gate, or non-empty path change was introduced. RED was
  `1 failed, 1 passed`; focused GREEN was `22 passed`; exact SAXS was `415
  passed, 6 warnings`.
- Structured verifier and explicit checkpoint remain to be recorded after the
  final documentation update. Full/boundary repository verification is not
  claimed for this scoped task.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-temperature-empty-series-fail-closed.md`,
  `docs/superpowers/specs/2026-07-28-saxs-temperature-empty-series-fail-closed-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-temperature-empty-series-fail-closed.md`.

## SAXS empty-profile fail-closed boundary (2026-07-28)

- `analyze_single()` now returns the existing structured `Unusable` contract
  immediately when deterministic 1D sanitization leaves no q/I observations.
  The branch reuses `build_data_quality_report()` and
  `build_guinier_evidence()`, preserves source/action provenance, and returns
  empty numeric DTO defaults without interpolation, padding, rescue, AI, or
  new thresholds. Non-empty analysis is unchanged.
- TDD RED reproduced the `lorentz_fit_long_period()` empty-array `IndexError`;
  focused GREEN passed `17` tests and the exact SAXS matrix passed `413` tests
  with `6` warnings. The structured verifier passed with quality `283`,
  preprocessing `106`, Ruff, compile/type baseline, memory/task, and
  whitespace checks; `git diff --check` passed.
- Full/boundary repository verification was not run for this scoped task.
  Checkpoint is local-only; no push, merge, rescue, AI, release, or scientific
  publication approval is implied.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-empty-profile-fail-closed.md`,
  `docs/superpowers/specs/2026-07-28-saxs-empty-profile-fail-closed-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-empty-profile-fail-closed.md`.

## Full release-audit recheck (2026-07-28)

- The latest D:-isolated `python scripts/verify.py --changed --types --full
  --boundary` run is green: `2845 passed, 16 skipped, 12 warnings` in
  `1574.30s`, verifier exit code `0`. Compile, quality (`283`), preprocessing
  (`106`), Ruff/type baseline, whitespace, and boundary audit also passed.
- An earlier D:-isolated run returned `2836 passed, 16 skipped, 12 warnings, 2
  failed` with verifier exit code `1`. Both failures were SAXS
  condition-recovery assertions where `path_directory` was expected but
  `unresolved` was returned. They were a real test result, not a timeout, but
  the focused rerun (`2 passed`) and the fresh full run are green; retain that
  result as historical diagnostic evidence rather than current release status.
- Fresh command-level rechecks returned IR published-run `2 passed, 13
  deselected in 84.78s` and NMR solid-C lifecycle `1 passed, 3 deselected in
  126.89s`, both exit code `0`. The automated software routes pass these
  shards, while human GUI/scientific/release gates remain open.
- A later independent recheck captured complete output for the delegated
  commands: IR walkthrough `2 passed, 13 deselected in 88.67s`; NMR walkthrough
  `4 passed, 11 deselected in 132.02s`; and NMR solid-C lifecycle `1 passed, 3
  deselected in 138.00s`. All three returned exit code `0`; process exit without
  a pytest summary is not treated as evidence.
- The D:-isolated 68-capture native matrix was re-inspected: synthetic IR
  mapping Results/Editor are structurally usable, NMR solid-C labels remain a
  scientific/visual policy question, and synthetic Joint diagnostics coexist
  with a `No project` / `No data loaded` header. A direct OS capture of the
  current stale GUI handle returned wallpaper, so it is not restarted-GUI
  evidence. The full development plan now records the automated slices as
  complete while retaining the human gates.
- A fresh GUI process (`PID 39700`) was started from the current worktree and
  captured through Qt-native `QScreen.grabWindow()`. Its default shell and
  SAXS static-to-temperature mode switch are valid fresh-window evidence; the
  process was closed gracefully afterward. All-mode real-data route and human
  release gates remain open.
- A fresh four-partition NMR published-run walkthrough also returned `4
  passed, 11 deselected in 108.37s`, exit code `0`; solid-C assignment remains
  provisional.

## SAXS structure-parameter fail-closed guard (2026-07-28)

- `compute_structure_params()` now initializes its existing `idf_is_artifact`
  default before the tangent decision. Limited-q profiles with no tangent/IDF
  artifact branch no longer raise `UnboundLocalError`; the existing structured
  result and quality/evidence path is allowed to complete.
- No numerical method, threshold, quality level, physical gate, rescue, AI,
  or publication role changed. TDD RED was `1 failed`, focused GREEN was `21
  passed`, and the exact SAXS matrix was `412 passed, 6 warnings`. The
  external-D task verifier passed with quality `283`, preprocessing `106`,
  Ruff, compile/type baseline, memory/task, and whitespace checks. The
  explicit allowlist checkpoint was created locally; no push, merge, release,
  or scientific publication approval is implied.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-structure-params-fail-closed.md`,
  `docs/superpowers/specs/2026-07-28-saxs-structure-params-fail-closed-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-structure-params-fail-closed.md`.

## SAXS 1D quality provenance source binding (2026-07-28)

- The 1D `DataQualityReport` source fields are now bound at the analysis
  boundary when explicit metadata is available. `analyze_single()` accepts
  optional `source_id`/`raw_data_ref`; temperature passes original source
  indices after sorting, and strain remains positional.
- The high-level SAXS engine derives `frame-{index}` plus the exact `_file_list`
  path, and stores a single-file path separately. Missing or length-mismatched
  metadata remains unbound; no source is guessed or copied.
- Existing sanitization actions, quality levels, numerical algorithms,
  thresholds, rescue, AI, publication roles, and consumer DTO projections are
  unchanged. Focused GREEN is `27 passed`; exact SAXS matrix is `411 passed,
  6 warnings`. The external-D task verifier passed with quality `283`,
  preprocessing `106`, Ruff, compile/type baseline, memory, task-card, and
  whitespace checks; `git diff --check` passed. An explicit allowlist
  checkpoint was created locally with the explicit allowlist; no push, merge,
  release, or scientific publication approval is implied.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-1d-quality-provenance-source-binding.md`,
  `docs/superpowers/specs/2026-07-28-saxs-1d-quality-provenance-source-binding-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-1d-quality-provenance-source-binding.md`.

## SAXS deterministic 1D profile sanitization (2026-07-28)

- `analyze_single()` now receives a detached finite/positive q/I analysis copy
  built by `sanitize_1d_profile()`. Invalid pairs are dropped, surviving q
  values are stably sorted, and duplicate q observations are retained rather
  than averaged because no measurement-error model is available.
- The original caller-owned q/I arrays remain unchanged. Existing
  `DataQualityReport` counts and quality levels are preserved, while its
  ordered `actions` field records actual alignment, filtering, sorting, and
  duplicate-retention operations.
- TDD/consumer evidence: focused `20 passed`; exact SAXS `406 passed, 6
  warnings`. An earlier D:-isolated full/boundary run returned `2838 passed,
  16 skipped, 12 warnings`; the later release-audit rerun is the current
  authoritative result and has the two SAXS condition-recovery failures
  recorded above. The first C:-based full attempt hit `No space left on
  device` and is excluded.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-deterministic-1d-profile-sanitization.md`,
  `docs/superpowers/specs/2026-07-28-saxs-deterministic-1d-profile-sanitization-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-deterministic-1d-profile-sanitization.md`.
- Explicit allowlist checkpoint created locally; no push, merge, release, or
  scientific publication approval is implied.

## Native all-mode route evidence after opacity correction (2026-07-28)

- A fresh current-checkout native Windows Qt process returned `17 passed, 15
  warnings in 363.16s`, exit code `0`, with D:-isolated basetemp and capture
  output. It covered the 15 real fixture cases (DSC 3, SAXS 3, WAXS 3 including
  full-2D strain, IR 2, NMR 4) plus synthetic Joint and synthetic IR mapping;
  every case captured Results/Gallery/History/Editor and exercised
  PackageExporter fallback. Captures are under
  `D:\PolyNexus_native_all_routes_capture_20260728_with_ir_mapping`.
- Fresh visual inspection confirms live CJK rendering and opaque Results text.
  The synthetic IR mapping heatmap/ROI/editor route is constructible but does
  not validate vendor-native mapping semantics. NMR solid-C peak-label
  crowding remains a scientific/visual review signal; the synthetic Joint
  fixture shows diagnostics while its header says `No project` / `No data
  loaded`. Final restarted-GUI/scientific approval remains open.
- The D:-isolated native Windows Qt rerun passed `15 passed, 1 deselected,
  15 warnings in 398.02s`, exit code `0`, across DSC `3`, SAXS `3`, WAXS `3`,
  IR `2`, and NMR `4`. Each mode restored populated Results, captured
  Results/Gallery/History/Editor, and exercised the PackageExporter fallback.
- The synthetic Joint route passed `1 passed, 15 deselected in 8.92s`, exit
  code `0`. Captures are under `D:\PolyNexus_native_all_routes_capture_20260728`.
  Visual inspection found live CJK labels and opaque Results text; crowded
  NMR solid-C labels remain a scientific/visual review signal.
- A preceding C:-based attempt ended with `4 passed, 11 failed` because the
  volume was full. It is an environment failure, superseded by the D:-isolated
  run. Three old unreferenced diagnostic directories were moved recoverably to
  `D:\PolyNexus_temp_archive_20260728`; no repository scratch or real data was
  deleted.
- These results strengthen automated route evidence only. Restarted-GUI human
  review, IR vendor mapping/ROI semantics, solid-C assignment, Joint conflicts,
  and final release approval remain open.

## Results Workbench main-Tab opacity correction (2026-07-28)

- Native route diagnosis showed the Light-theme pale Results appearance was
  caused by `MainWindow._on_tab_changed()` installing a full-page
  `QGraphicsOpacityEffect`; the labels already had the correct active theme
  colors.
- The main Tab route now updates context suggestions without applying a page-
  wide opacity effect. Local transient surfaces, including the drop banner,
  retain their explicit animations. This changes presentation timing only;
  Results data, evidence, figures, and scientific semantics are untouched.
- Evidence: focused MainWindow/ResultsTablePanel `23 passed`; native SAXS
  static/temperature/strain route capture `3 passed` in `44.10s`; task-scoped
  verifier passed with quality `283`, preprocessing `106`, Ruff, compile/type,
  memory/task, and whitespace checks using an external basetemp.
- Human restarted-GUI visual review across all techniques and final scientific/
  release approval remain open.

## SAXS parameter quality-evidence reference (2026-07-28)

- Bundle parameter artifacts now reference the authoritative
  `quality_evidence.json` without copying AI rescue or quality payloads into
  CSV. `parameters.json` uses `quality_evidence_file`; each
  `data/parameters.csv` row uses the relative `quality_evidence_ref`.
- Implementation checkpoint: `1608643` (no push). This remains provenance
  traceability, not scientific validity or rescue acceptance.

## Results Workbench Light-theme contrast correction (2026-07-28)

- Results Workbench inline labels now use the active `ThemeTokens` at build time
  and after live theme switches; old dark-only `styles.py` colors no longer
  leak into the Light surface.
- Light `text_muted` is now `#667085`, giving `4.72:1` contrast against the
  Light background `#f7f9fc`. Focused Results/theme evidence is `24 passed`;
  the complete non-Joint native route matrix is `15 passed` after the fix.
- This closes the code-level contrast defect. Activated/restarted-GUI visual
  review, IR vendor mapping/ROI semantics, solid-C NMR assignment, Joint
  scientific conflicts, Origin/COM optional runtime, and final release
  approval remain open.
- Native captures explicitly call `raise_()` and `activateWindow()` first; a
  fresh DSC activation probe passed `1` case in `6.90s` with no deprecated Qt
  activation warning. Gallery text remained pale in the capture, so this is
  still a human visual-review item rather than a basis for another color edit.

## Native Results restore acceptance correction (2026-07-28)

- The native real-route harness now restores each engine run with its existing
  `AnalysisResult.parameters` and `AnalysisResult.to_dict()` payload. The old
  fixture supplied only `data_file` and empty parameters, so Gallery was valid
  while the Results table was empty.
- A regression assertion requires a primary Results section and at least one
  rendered table row. Fresh native Windows Qt shards passed: DSC `3` in
  `23.13s`, SAXS `3` in `48.91s`, WAXS `3` in `85.25s`, IR `2` in `65.91s`,
  and NMR `4` in `111.49s`; every shard exited `0`.
- This is route/harness evidence, not a production GUI contrast fix. Inactive
  `grab()` captures still show pale Results/Gallery body text and require
  restarted-GUI visual review; IR vendor semantics, solid-C NMR assignment,
  Joint scientific conflicts, and final release approval remain open.

## SAXS rescue-candidate Workbench visibility (2026-07-28)

- Existing deterministic temperature `sequence_rescue_candidates` now travels
  through the public temperature parameters payload as a detached nested list.
  Results Workbench shows candidate ID, frame/source, proposed value/mode,
  validation-required state, and existing reasons as advisory review text.
- Malformed or empty candidates remain absent; no candidate is applied,
  accepted, rerun, or promoted. Existing physical, quality, and sequence gates
  remain authoritative, and static/strain paths are unchanged.
- Fresh evidence: focused consumer matrix `97 passed`; exact SAXS file matrix
  `393 passed, 6 warnings`; task verifier exit `0` with quality `283`,
  preprocessing `106`, Ruff, compile/type, memory/task, and whitespace checks.
  Full/boundary verification was not run for this slice.
- Task/spec/plan:
  `docs/agent/tasks/2026-07-28-saxs-rescue-candidate-workbench-visibility.md`,
  `docs/superpowers/specs/2026-07-28-saxs-rescue-candidate-workbench-visibility-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-rescue-candidate-workbench-visibility.md`.
- Implementation checkpoint: `e214d76` (no push).

## SAXS DataQualityReport Workbench visibility (2026-07-28)

- The Results Workbench now shows existing q/I `DataQualityReport` provenance
  as read-only review context for static, temperature, and strain payloads.
  Top-level reports expose level, source and data refs, counts, reasons, and
  actions; batch payloads expose reported-frame coverage, emitted level counts,
  and ordered reason/action summaries.
- Missing or malformed reports remain absent; batch rows are never copied into
  top-level detail, and the presentation does not mutate payloads or change
  cleaning, thresholds, physical gates, rescue, AI, or publication semantics.
- Fresh evidence: focused Workbench/SAXS matrix `59 passed`; the structured
  verifier exited `0` with quality `283`, preprocessing `106`, Ruff,
  compile/type baseline, memory/task, and whitespace checks. Full/boundary
  verification was not run for this slice.
- Task/spec/plan: `docs/agent/tasks/2026-07-28-saxs-data-quality-workbench-visibility.md`,
  `docs/superpowers/specs/2026-07-28-saxs-data-quality-workbench-visibility-design.md`,
  and `docs/superpowers/plans/2026-07-28-saxs-data-quality-workbench-visibility.md`.
- Implementation checkpoint: `fb76039` (no push).

## SAXS DataQualityReport DataFrame and CSV export (2026-07-28)

- Temperature/strain tables and static parameter CSV projections now expose
  the existing q/I report's source refs, level, ordered reasons/actions, defect
  counts, and boolean flags. Missing reports stay empty and nested evidence
  remains authoritative; no quality or physical semantics changed.
- Fresh evidence is focused `21 passed`, exact SAXS `383 passed, 6 warnings`,
  and structured verifier exit `0` with quality `283` and preprocessing `106`.
- The explicit checkpoint is `b0c63d7` (no push). Scientific claim review,
  detector calibration, rescue approval, and publication release remain open.

## SAXS detector provenance DataFrame and CSV export (2026-07-28)

- Temperature/strain DataFrames and static parameter CSV projections now expose
  the existing raw-detector source, quality, reasons, geometry provenance, and
  mask provenance as stable flat fields. Missing reports remain empty and
  `not_assessed` remains a scientific limitation; no analysis, threshold,
  quality, rescue, or publication semantics changed.
- Fresh evidence: focused `21 passed`, exact SAXS matrix `383 passed, 6
  warnings` in four isolated shards, and task verifier exit `0` with quality
  `283`, preprocessing `106`, Ruff, compile/type, memory/task, and whitespace
  checks. The incomplete first unsplit matrix run is explicitly excluded.
- The explicit checkpoint is `4d09085` (no push). Detector calibration,
  beam-center meaning, mask validity, saturation interpretation, and human
  scientific/release approval remain open.

## SAXS Workbench geometry and mask provenance visibility (2026-07-28)

- Workbench review text now shows the existing raw-detector geometry source and
  field-source counts, plus mask source/configuration/shape, without rerunning
  analysis or changing quality semantics. The `not_assessed` marker remains a
  human scientific limitation.
- Raw and sector-map fields remain separate. Automated evidence is
  Workbench/Export/Figure `67 passed`, exact SAXS `380 passed, 6 warnings`,
  and task verifier exit `0` with quality `283` and preprocessing `106`.
- See task card
  `docs/agent/tasks/2026-07-28-saxs-workbench-geometry-mask-provenance.md`.

## SAXS raw detector geometry and mask provenance transport (2026-07-28)

- The raw detector report now transports per-field geometry provenance and
  existing dummy-mask provenance as strict JSON-safe nested mappings. The
  payload records origin only; `validity=not_assessed` preserves the human
  scientific boundary.
- Figure frame/series evidence keeps these fields only on
  `raw_detector_quality_report`; sector-map `detector_quality_report` remains
  source-separated. No threshold, quality level, physical gate, rescue, or
  publication role changed.
- Fresh evidence: raw focused `9 passed, 2 warnings`, consumer matrix `64
  passed`, exact SAXS matrix `377 passed, 6 warnings`, task verifier exit `0`
  with quality `283` and preprocessing `106`. The first verifier attempt was
  blocked by a pre-existing `.pytest_tmp` Windows permission lock; the external
  basetemp rerun is the authoritative task-scoped evidence.
- See task card
  `docs/agent/tasks/2026-07-28-saxs-raw-detector-provenance.md`.

## SAXS Workbench detector evidence visibility (2026-07-28)

- Existing raw-detector and sector-map quality reports are now visible as
  separate, read-only Workbench review context. The formatter shows source,
  level, available frame coverage, coverage fraction, and existing reasons;
  full evidence remains in Diagnostics, History, Figure, and Export payloads.
- Focused Workbench/Export/Figure evidence is `64 passed`; exact SAXS file
  matrix is `374 passed, 5 warnings`. This slice adds no detector threshold,
  geometry/mask inference, quality promotion, rescue, or publication role.
- Geometry calibration, beam-center interpretation, mask scientific validity,
  saturation meaning, restarted-GUI review, and human release approval remain
  open. See task card
  `docs/agent/tasks/2026-07-28-saxs-workbench-detector-evidence-visibility.md`.

## Native Windows Qt DSC route evidence (2026-07-28)

- The current worktree's native Windows Qt visual capture passed
  `1 passed in 5.93s` with external basetemp
  `C:\Temp\PolyNexus_native_gui_route`. DSC Results, Gallery, History, and
  Editor captures at 1600x1000 showed normal CJK glyphs and constructible
  shared routes.
- This is one native DSC route, not all-mode visual or export interaction
  approval. The remaining all-route GUI and scientific/release gates stay
  open.

## Native Windows Qt all-route evidence (2026-07-28)

- `tests/test_native_gui_real_route_capture.py` now includes the regular and
  full-2D real case lists. Native Windows Qt shards passed all 15 modes with
  exit code `0`: DSC `3`, SAXS `3`, WAXS `3`, IR `2`, and NMR `4`.
- The shard durations were DSC `25.44s`, SAXS `49.93s`, WAXS `86.35s`, IR
  `66.72s`, and NMR `114.85s`; each mode captured Results, Gallery, History,
  and Editor under external temp folders. This is automated route evidence,
  not final pixel or Export approval.
- Representative captures show native CJK labels and constructible plots and
  Editor controls, while Results/Gallery body contrast in inactive `grab()`
  captures remains a human review item. IR temperature `neg_fraction` and NMR
  solid-C assignment warnings remain scientific limitations.
- The earlier all-native invocation had a tool-level timeout with no pytest
  summary. The old `waxs.strain` filter returned exit `5` only because the
  harness omitted full-2D cases; it is superseded by the fresh WAXS/IR shards.

## Native Windows Qt all-route package Export evidence (2026-07-28)

- The native harness triggers the actual Chart Editor Export `QAction` for all
  15 real modes and asserts the fallback package artifacts. The matrix passed
  with exit code `0`: DSC `3`, SAXS `3`, WAXS `3`, IR `2`, and NMR `4`.
- Each mode produced `Origin_Export/figure_document.json`, `metadata.json`,
  and `import.ogs` under an external run output. The test injects only the
  existing `PackageExporter`, so it verifies the no-Origin production fallback
  without launching Origin/COM.
- Installed OriginPro/COM behavior remains an optional-runtime/manual gate;
  native screenshot body contrast in inactive grabs remains a visual review
  item. Scientific warnings for IR 2D and solid-C NMR are unchanged.

## Native synthetic Joint route evidence (2026-07-28)

- The existing synthetic `JointCoordinator` report now has a native GUI route
  probe: `1 passed, 15 deselected in 5.94s`, exit code `0`.
- The probe restores `joint.compare`, captures Results/Gallery/History/Editor,
  and verifies package Export artifacts. It remains report-level software
  evidence; real-data Joint behavior and conflict semantics are not closed.

## Fresh current full/boundary release verification (2026-07-27)

- The current working tree completed
  `python scripts/verify.py --changed --types --full --boundary` with an
  external basetemp: `2793 passed, 10 warnings in 1607.00s (0:26:46)` and
  exit code `0`.
- Compile, quality `283`, preprocessing `106`, Ruff/type, whitespace, and the
  boundary audit passed. This supersedes the older `2790` current-head count;
  live GUI, scientific review, and final human release approval remain open.

## Joint route plan reconciliation (2026-07-27)

- `joint.compare` now has current code and lifecycle evidence through
  `JointHubWorker` → `JointCoordinator.publish_hub_report()` → shared
  FigureDefinition/Manifest, with custom Workbench and History restore.
- The focused Joint provider/coordinator/lifecycle/Workbench matrix is
  `14 passed`. The full-software Phase 7 plan was corrected to mark only this
  automated route complete; scientific conflict semantics and real/live
  release review remain open.
- The final task-scoped verifier passed task/memory, Ruff, compile/type,
  quality `283`, preprocessing `106`, and whitespace with exit code `0`.
- See `docs/agent/tasks/2026-07-27-joint-route-plan-reconciliation.md`.

## Qt font runtime acceptance (2026-07-27)

- The real Windows Qt runtime has 399 font families and resolves the
  application font to `Microsoft YaHei UI`; representative Chinese GUI glyphs
  are covered. The declared theme fallback chain is not missing in production.
- Under `QT_QPA_PLATFORM=offscreen`, Qt exposes zero font families and no
  Chinese glyph coverage, so offscreen CJK square placeholders cannot close or
  fail live font acceptance. No production font or Matplotlib style change was
  made.
- Human restarted-GUI, pixel-level, and final release review remain open. See
  `docs/agent/tasks/2026-07-27-qt-font-runtime-acceptance.md`.
- The task-scoped verifier passed task/memory, Ruff, compile/type, quality
  `283`, preprocessing `106`, and whitespace checks with exit code `0` using
  external basetemp `C:\Temp\PolyNexus_qt_font_runtime_verify`.

## Latest SAXS real Workbench acceptance refresh (2026-07-27)

- Current-head launcher diagnosis resolved `D:\PolyNexus`, package under the
  same root, branch `codex/origin-editor-usable-controls`, commit `9fa7b82`.
- Fresh real SAXS walkthrough passed `3` selected cases with `12` deselected;
  the Workbench/figure profile matrix passed `29` cases. External bundle
  reinspection retained the conservative evidence states: static 1D methods
  remain Diagnostic, temperature sequence Guinier is Unusable with no valid
  frames, and strain retains five Trend frame records.
- The strain heatmap saturation and temperature end-of-axis truncation remain
  explicit scientific-review signals. Human restarted-GUI interaction and
  release approval remain open; no scientific threshold or publication role
  was changed.
kind: state
status: active
date: 2026-07-22
title: Current PolyNexus repository state
---

## SAXS real 2D detector evidence transport (2026-07-27)

- The real PAD8 strain route now carries the existing sector-map detector
  report from `herman_from_sector_data` into every strain point and the series
  summary. The report remains `Unusable`/Diagnostic in the real case because
  saturation and beam-center provenance are unavailable and nonpositive pixels
  are present; no raw-detector or Quantitative claim was added.
- Current evidence: focused transport `12 passed`, exact SAXS matrix `365
  passed, 4 warnings`, structured verifier quality `283` and preprocessing
  `106`, and external real replay `validation_passed=True` with five
  `source_kind=sector_map` reports.
- Raw detector mask propagation, geometry/scientific validity review, GUI
  visual review, and final human release approval remain open.

## SAXS quality-analysis route audit (2026-07-27)

- The route-level implementation plan is now recorded at
  `docs/superpowers/plans/2026-07-26-saxs-quality-analysis-program.md` and
  maps the existing Stage 0-7 task/spec/plan evidence without changing SAXS
  production behavior.
- Current-head evidence remains `364 passed, 4 warnings` for the exact SAXS
  file matrix, `3 passed, 12 deselected` for the real SAXS walkthrough, and
  `29 passed` for the Workbench/figure profile matrix.
- Automated evidence closure does not close restarted-GUI visual review,
  real-data scientific review, raw 2D detector/geometry acceptance, or human
  release/publication approval. The conservative real-bundle levels and
  missing-frame policy remain authoritative.

## Latest SAXS AI confirmation UI audit (2026-07-27)

- The real offscreen `MainWindow` plus `SideTuningReportDialog` route is now
  covered by `tests/test_saxs_ai_confirmation_gui_route.py`. Its Apply path
  starts exactly one existing `apply_pending` SAXS transaction; its reject path
  leaves the candidate unapplied. The focused route test returned `2 passed in
  6.30s`.
- The test passed against the existing code, so no production code, SAXS
  threshold, physical gate, or quality gate changed. Automated confirmation is
  now evidenced at the GUI-route boundary; restarted-GUI visual inspection,
  real-data scientific review, and human release approval remain open.

## Latest GUI route evidence (2026-07-27)

- A live canonical-window capture at maximum size shows the sidebar and
  Data/Config/Results/Plots/History shell fitting the Data surface. A
  normal-size capture still leaves a narrow-width right-edge visual review
  item.
- An offscreen restored-real-DSC capture constructed all five tabs and the
  Chart Editor and found one active manifest Gallery entry. The screenshots
  are structural only because offscreen CJK glyphs render as square
  placeholders; live-font, pixel-level, and all-route interaction review are
  not closed.

## Mainline snapshot

- SAXS condition-axis provenance now has an explicit Export/History boundary
  regression. `quality_evidence.json` preserves the existing series axis, and
  History preserves it in both parameters and nested result payloads. The
  generic History JSON normalizer now honors public `to_dict()` DTO contracts,
  preventing `MetricEvidenceSummary` from being stringified. No SAXS algorithm,
  threshold, database schema, or rescue behavior changed. Current evidence is
  focused `29 passed` and isolated SAXS `362 passed, 4 warnings`; task verifier
  passed quality `283`, preprocessing `106`, and scoped checks. The checkpoint
  for task
  `docs/agent/tasks/2026-07-27-saxs-condition-axis-export-history-audit.md`
  is checkpointed at `fac9c8d`; no push was performed and parallel GUI/scratch
  files were intentionally left untouched.

- SAXS condition-axis Figure/Manifest provenance is implemented in the working
  tree: the existing frame and series metric evidence projection now retains
  `condition_axis` with strict JSON-safe, detached values, including diagnostic
  positions and `null` non-finite values. No Figure role, orientation boundary,
  analysis, History, Export, or scientific interpretation changed. Focused
  Figure/Document evidence is `25 passed`; the Figure/provider matrix is `45
  passed`; and the isolated SAXS matrix is `361 passed, 4 warnings`. The
  isolated task verifier passed quality `282` and preprocessing `106`. Task
  card:
  `docs/agent/tasks/2026-07-27-saxs-condition-axis-figure-provenance.md`.

- SAXS condition-axis Workbench visibility is implemented in the working tree:
  existing `metric_evidence[*].condition_axis` defects now appear as advisory
  review hints with metric/axis names, defect counts, and representative frame
  positions. Full nested axis values remain in Diagnostics and existing
  parameter/History/Export payloads are untouched. Ordered axes add no risk
  text; no new threshold, physical interpretation, or strain ordering rule was
  added. Focused Workbench evidence is `16 passed`, consumer evidence is `56
  passed`, and the isolated SAXS matrix is `359 passed, 4 warnings`. The
  isolated task verifier passed quality `282` and preprocessing `106`. Task
  card:
  `docs/agent/tasks/2026-07-27-saxs-condition-axis-workbench-visibility.md`.

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
  final human release approval remain open. Fresh current-head full verification
  retry at `2af4baf` passed `2790` tests with `10` existing warnings in
  `1454.97s`; selected quality (`283`), preprocessing (`106`), and the boundary
  audit passed. The GUI responsive-shell checkpoint is `83083bc`; a fresh canonical
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

## Latest task update (2026-07-29)

Joint history restore now derives a display-only project badge from the
persisted label or report sample rows. Single-sample reports show the sample,
multi-sample reports show the translated Joint workspace title, and empty
reports retain the default label. The focused identity/lifecycle slice passed
`5` tests and the complete MainWindow persistence slice passed `197` tests.
Task card:
`docs/agent/tasks/2026-07-29-joint-history-project-identity.md`. Task-scoped
verification passed; the atomic checkpoint is the allowlisted commit for this
task.

## Latest task update (2026-08-08)

SAXS strain analysis now retains the total long-period peak while adding
diagnostic tensile-axis and transverse-axis q/L fields for explicitly
configured detector-image axes. The directional route requires canonical 2D
intensity/q/chi/support, uses support and fractional chi-bin overlap weights,
and applies the fixed-sector normalization/smoothing stages. Exact configured
fixed-sector matches reuse the existing meridional/equatorial profiles after
canonical validation. Missing scientific inputs fail closed, and the primary
results-table contract is unchanged. Verification evidence is tracked in
`docs/agent/tasks/2026-08-08-saxs-tensile-aligned-peak-tracking.md`.

## Canonical figure assets - checkpointed 2026-08-14

- New evidence runs retain SVG by default.  PNG/PDF are explicit publication
  exports; editor working previews are private interaction artifacts.
- Evidence packages now expose `figure-index.json`, deduplicate SVG/PNG/preview
  siblings by assets directory, and map ARS candidates to package-relative SVG.
  GUI and package readers share the same logical figure DTO; old packages use a
  read-only fallback.
- A real PA6 DSC/IR/SAXS/WAXS replay produced
  `canonical-figure-assets-pa6-v002` with 112 SVG/index entries, zero package
  PNG/PDF files, and intact ARS writing input.  Acceptance:
  `docs/acceptance/2026-08-14-canonical-figure-assets.md`.

## Evidence figure role projection - review required 2026-08-21

- Evidence package indexing now preserves ARS-selected main/supporting
  candidate intent: selected FTIR group SVGs become `manuscript_candidate` or
  `supporting_candidate`, while unselected run output remains `diagnostic`.
  Candidate figures remain `review_only`; this is not a scientific promotion.
- Index technique is no longer copied from the first package evidence item; it
  comes from the producing run or candidate. Candidate group IDs are retained
  only when explicit. Same candidate PNG/SVG siblings deduplicate safely, and
  missing SVGs or role/technique/full-group-set conflicts fail closed. Index
  v1 preserves a single group only; multi-group comparison membership remains
  in the candidate manifest rather than being invented in the index.
- A read-only real PA6 FTIR replay produced
  `pa6-role-projection-smoke-v003` with one `manuscript_candidate / IR` group
  overlay plus 27 diagnostics. Acceptance:
  `docs/acceptance/2026-08-21-evidence-figure-role-projection.md`.
## Universal FTIR metadata preamble - 2026-08-27

The generic `spectrum_1d.v1` converter accepts the real vendor CSV layout with
`XLabel/Wavenumber` and `YLabel/Absorbance` metadata rows before numeric data.
It preserves source physical row locators and remains deterministic; provider
algorithms are unchanged. Six-sample replay v002 confirms all selected FTIR
files convert; three DSC samples remain gated by existing qualification rules.
The full boundary suite is not green (`4133 passed, 38 failed, 25 skipped`),
so legacy producer deletion and release remain open.
