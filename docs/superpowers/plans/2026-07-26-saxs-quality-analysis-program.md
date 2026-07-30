# SAXS Quality and Analysis Program Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Each atomic task must keep its own task card, focused evidence, verifier output, and explicit allowlist checkpoint.

**Goal:** Turn the approved SAXS quality-and-analysis design into a traceable,
stage-gated delivery route from temperature Guinier evidence through method,
2D, rescue, AI, and publication consumers.

**Architecture:** Use the existing evidence contracts as the vertical spine.
Each stage consumes the previous stage's public result/evidence DTOs and adds
only the smallest new contract needed at that boundary. Deterministic
re-analysis, existing physical indicators, and quality gates remain the final
authority; AI remains candidate/replay/confirm-only. Missing frames and failed
measurements stay explicit and are never interpolated, copied, or silently
promoted.

**Tech Stack:** Python, Pytest, Ruff, strict JSON DTOs, SAXS result/figure
contracts, `scripts/verify.py`, `scripts/auto_commit.py`, and Markdown task/spec
artifacts.

---

## 1. Delivery contract

Every behavior-changing slice follows this order:

1. Read `AGENTS.md`, the SAXS module docs, the route spec, and durable memory.
2. Define one task card, one design/spec, and one implementation plan entry.
3. Write focused RED tests for the new public behavior.
4. Implement the smallest deterministic change; keep GUI code as a consumer of
   result/evidence DTOs.
5. Run the focused matrix, the exact SAXS matrix, and the task-scoped verifier
   with an isolated basetemp when the shared Windows pytest directory is locked.
6. Record the actual result, limitations, and pre-existing files, then create
   one `scripts/auto_commit.py` checkpoint with an explicit allowlist.

This route-audit task is documentation-only. It does not add production
behavior or a new scientific threshold, so no new TDD regression is required;
the existing stage regressions and current-head SAXS matrix are the evidence
being indexed here.

### Non-negotiable scientific and safety boundaries

- `Quantitative`, `Trend`, `Diagnostic`, and `Unusable` describe evidence
  strength, not a promise that a model is scientifically applicable.
- `qRg < 1.3` is used only inside the Guinier applicability contract; it is not
  a universal polymer-SAXS validity rule.
- A missing, invalid, or failed frame remains missing at its original position.
  No interpolation, neighbor copy, synthetic curve, or silent deletion is
  permitted.
- Rescue and AI outputs are candidates until deterministic re-analysis,
  data-preservation checks, existing physical gates, and sequence evidence
  pass. No automatic acceptance is implied by a plausible candidate.
- Figure roles and publication eligibility consume emitted evidence; they do
  not infer scientific validity from a rendered image.

## 2. Stage traceability matrix

The following matrix is the route of record. A stage is considered automated-
ready only when its linked card records focused tests, task-scoped verifier
evidence, and an explicit allowlist checkpoint. The matrix does not turn
synthetic or contract evidence into real-detector or human scientific sign-off.

| Stage | Delivery slice | Task card | Design / implementation plan | Current evidence and status |
|---|---|---|---|---|
| 0 | Quality DTOs, reason codes, levels, strict JSON, fault fixtures | `docs/agent/tasks/2026-07-27-saxs-quality-contracts-stage0.md` | `docs/superpowers/specs/2026-07-26-saxs-quality-analysis-program-design.md`; `docs/superpowers/plans/2026-07-26-saxs-quality-contracts.md` | Focused `7 passed`; task evidence records quality `282`, preprocessing `103`, and checkpoint `556f006`. **Automated-ready.** |
| 1A | Temperature 1D frame-level Guinier fit and metric evidence | `docs/agent/tasks/2026-07-27-saxs-temperature-guinier-evidence.md`; `docs/agent/tasks/2026-07-27-saxs-temperature-guinier-metric-evidence.md`; `docs/agent/tasks/2026-07-27-saxs-temperature-frame-fail-closed.md` | `docs/superpowers/specs/2026-07-27-saxs-temperature-guinier-metric-evidence-design.md`; `docs/superpowers/specs/2026-07-27-saxs-temperature-frame-fail-closed-design.md`; `docs/superpowers/plans/2026-07-27-saxs-temperature-guinier-evidence.md`; `docs/superpowers/plans/2026-07-27-saxs-temperature-guinier-metric-evidence.md`; `docs/superpowers/plans/2026-07-27-saxs-temperature-frame-fail-closed.md` | Cards record focused frame/metric/fail-closed regressions, strict level propagation, preserved failures, and explicit checkpoints (`17dcb0b`, `3324b2e`, plus the fail-closed card). **Automated-ready; real scientific applicability remains open.** |
| 1B | Temperature sequence Guinier trend and conservative continuity evidence | `docs/agent/tasks/2026-07-27-saxs-guinier-sequence-evidence.md`; `docs/agent/tasks/2026-07-27-saxs-temperature-guinier-sequence-transport.md` | `docs/superpowers/specs/2026-07-27-saxs-guinier-sequence-evidence-design.md`; `docs/superpowers/plans/2026-07-27-saxs-guinier-sequence-evidence.md`; `docs/superpowers/plans/2026-07-27-saxs-temperature-guinier-sequence-evidence.md` | Focused sequence/transport evidence is recorded in the cards; the transport slice records `311 passed` and checkpoint `b7bad1c`. No interpolation, frame fabrication, or automatic phase-change decision. **Automated-ready as diagnostic evidence.** |
| 2 | Porod, Kratky, invariant, and lamellar evidence using the shared contract | `docs/agent/tasks/2026-07-27-saxs-1d-method-evidence.md`; `docs/agent/tasks/2026-07-27-saxs-static-1d-evidence.md` | `docs/superpowers/specs/2026-07-27-saxs-1d-method-evidence-design.md`; `docs/superpowers/specs/2026-07-27-saxs-static-1d-evidence-design.md`; `docs/superpowers/plans/2026-07-27-saxs-1d-method-evidence.md`; `docs/superpowers/plans/2026-07-27-saxs-static-1d-evidence.md` | Method card records focused `5` plus `34` regression tests, exact SAXS `242 passed`, quality `282`, preprocessing `103`, and allowlist checkpoint. Static real-bundle evidence remains Diagnostic. **Automated-ready; publication promotion remains gated.** |
| 3 | Static, temperature, and strain evidence propagation, aligned-batch resilience, and condition-axis provenance | `docs/agent/tasks/2026-07-27-saxs-mode-evidence-propagation.md`; `docs/agent/tasks/2026-07-27-saxs-batch-evidence-mode-resilience.md`; `docs/agent/tasks/2026-07-27-saxs-series-metric-position-evidence.md`; `docs/agent/tasks/2026-07-27-saxs-series-metric-evidence-rollup.md`; `docs/agent/tasks/2026-07-27-saxs-temperature-condition-axis-evidence.md`; `docs/agent/tasks/2026-07-27-saxs-condition-axis-figure-provenance.md`; `docs/agent/tasks/2026-07-27-saxs-condition-axis-workbench-visibility.md`; `docs/agent/tasks/2026-07-27-saxs-condition-axis-export-history-audit.md` | `docs/superpowers/specs/2026-07-27-saxs-mode-evidence-propagation-design.md`; `docs/superpowers/specs/2026-07-27-saxs-series-metric-position-evidence-design.md`; `docs/superpowers/specs/2026-07-27-saxs-series-metric-evidence-rollup-design.md`; `docs/superpowers/specs/2026-07-27-saxs-temperature-condition-axis-evidence-design.md`; `docs/superpowers/specs/2026-07-27-saxs-condition-axis-figure-provenance-design.md`; `docs/superpowers/specs/2026-07-27-saxs-condition-axis-workbench-visibility-design.md`; `docs/superpowers/specs/2026-07-27-saxs-condition-axis-export-history-audit-design.md`; `docs/superpowers/plans/2026-07-27-saxs-mode-evidence-propagation.md`; `docs/superpowers/plans/2026-07-27-saxs-series-metric-position-evidence.md`; `docs/superpowers/plans/2026-07-27-saxs-series-metric-evidence-rollup.md`; `docs/superpowers/plans/2026-07-27-saxs-temperature-condition-axis-evidence.md`; `docs/superpowers/plans/2026-07-27-saxs-condition-axis-figure-provenance.md`; `docs/superpowers/plans/2026-07-27-saxs-condition-axis-workbench-visibility.md`; `docs/superpowers/plans/2026-07-27-saxs-condition-axis-export-history-audit.md` | Current cards record per-position evidence, source-index preservation, missing/diagnostic axes, aligned-batch boundaries, and Export/History transport. Latest audit checkpoint is `fac9c8d`; position checkpoint is `bd7c3fd`. **Automated-ready; no new physical interpretation was added.** |
| 4 | 2D detector quality, EDF azimuthal source, Herman orientation, and automatic axis | `docs/agent/tasks/2026-07-27-saxs-2d-evidence-propagation.md`; `docs/agent/tasks/2026-07-27-saxs-2d-detector-orientation-evidence.md`; `docs/agent/tasks/2026-07-27-saxs-edf-herman-source.md`; `docs/agent/tasks/2026-07-27-saxs-strain-herman-table.md`; `docs/agent/tasks/2026-07-27-saxs-auto-orientation-axis.md` | `docs/superpowers/specs/2026-07-27-saxs-2d-evidence-propagation-design.md`; `docs/superpowers/specs/2026-07-27-saxs-2d-detector-orientation-evidence-design.md`; `docs/superpowers/specs/2026-07-27-saxs-edf-herman-source-design.md`; `docs/superpowers/specs/2026-07-27-saxs-strain-herman-table-design.md`; `docs/superpowers/specs/2026-07-27-saxs-auto-orientation-axis-design.md`; `docs/superpowers/plans/2026-07-27-saxs-2d-evidence-propagation.md`; `docs/superpowers/plans/2026-07-27-saxs-2d-detector-orientation-evidence.md`; `docs/superpowers/plans/2026-07-27-saxs-edf-herman-source.md`; `docs/superpowers/plans/2026-07-27-saxs-strain-herman-table.md`; `docs/superpowers/plans/2026-07-27-saxs-auto-orientation-axis.md` | Cards record focused 2D/orientation matrices, complete SAXS regressions, and allowlist checkpoints. **Contract-ready only:** raw detector/geometry and mask-propagation scientific acceptance still require real-data review. |
| 5 | Candidate-only sequence rescue and replay/calibration audit | `docs/agent/tasks/2026-07-27-saxs-sequence-rescue.md`; `docs/agent/tasks/2026-07-27-saxs-candidate-replay-calibration.md` | `docs/superpowers/specs/2026-07-27-saxs-sequence-rescue-design.md`; `docs/superpowers/specs/2026-07-27-saxs-candidate-replay-calibration-design.md`; `docs/superpowers/plans/2026-07-27-saxs-sequence-rescue.md`; `docs/superpowers/plans/2026-07-27-saxs-candidate-replay-calibration.md` | Existing `lc` path is exposed as deterministic candidates; hard, physical, sequence, and data-preservation gates remain explicit. Candidate/replay card records DTO checkpoint `b23e6c4`, orchestrator/export checkpoint `320774a`, and calibration checkpoint `8caf4f7`. **Automated-ready as candidate-only; no automatic rescue.** |
| 6 | AI bridge, prompt protection, orchestrator handoff, confirmed rerun, and GUI confirmation route | `docs/agent/tasks/2026-07-27-saxs-ai-rescue-bridge.md`; `docs/agent/tasks/2026-07-27-saxs-ai-prompt-protection-contract.md`; `docs/agent/tasks/2026-07-27-saxs-ai-orchestrator-handoff.md`; `docs/agent/tasks/2026-07-27-saxs-ai-confirmed-rerun-safety.md`; `docs/agent/tasks/2026-07-27-saxs-ai-confirmation-ui-acceptance.md` | `docs/superpowers/specs/2026-07-27-saxs-ai-rescue-bridge-design.md`; `docs/superpowers/specs/2026-07-27-saxs-ai-prompt-protection-contract-design.md`; `docs/superpowers/specs/2026-07-27-saxs-ai-orchestrator-handoff-design.md`; `docs/superpowers/specs/2026-07-27-saxs-ai-confirmed-rerun-safety-design.md`; `docs/superpowers/specs/2026-07-27-saxs-ai-confirmation-ui-acceptance-design.md`; `docs/superpowers/plans/2026-07-27-saxs-ai-rescue-bridge.md`; `docs/superpowers/plans/2026-07-27-saxs-ai-prompt-protection-contract.md`; `docs/superpowers/plans/2026-07-27-saxs-ai-orchestrator-handoff.md`; `docs/superpowers/plans/2026-07-27-saxs-ai-confirmed-rerun-safety.md`; `docs/superpowers/plans/2026-07-27-saxs-ai-confirmation-ui-acceptance.md` | Cards record candidate/replay/confirm boundaries, negative/fault gates, and the real offscreen confirmation route (`2 passed`). Current UI route does not bypass existing `apply_pending`/rerun safety. **Automated route-ready; human release approval remains open.** |
| 7 | Workbench, Figure, Manifest, Export, History, real bundle replay, and release evidence | `docs/agent/tasks/2026-07-27-saxs-figure-evidence-binding.md`; `docs/agent/tasks/2026-07-27-saxs-quality-export-provenance.md`; `docs/agent/tasks/2026-07-27-saxs-workbench-series-evidence-visibility.md`; `docs/agent/tasks/2026-07-27-saxs-real-workbench-acceptance.md` | `docs/superpowers/specs/2026-07-27-saxs-figure-evidence-binding-design.md`; `docs/superpowers/specs/2026-07-27-saxs-quality-export-provenance-design.md`; `docs/superpowers/specs/2026-07-27-saxs-workbench-series-evidence-visibility-design.md`; `docs/superpowers/specs/2026-07-27-saxs-real-workbench-acceptance-design.md`; `docs/superpowers/plans/2026-07-27-saxs-figure-evidence-binding.md`; `docs/superpowers/plans/2026-07-27-saxs-quality-export-provenance.md`; `docs/superpowers/plans/2026-07-27-saxs-workbench-series-evidence-visibility.md`; `docs/superpowers/plans/2026-07-27-saxs-real-workbench-acceptance.md` | Current-head exact SAXS matrix: `364 passed, 4 warnings in 31.08s`; real walkthrough `3 passed, 12 deselected`; Workbench/figure profiles `29 passed`; launcher diagnosis resolved the canonical worktree. **Automated acceptance slice ready; restarted-GUI visual review, real scientific meaning review, and release/publication approval remain open.** |

## 3. Execution order for remaining work

The implementation order is intentionally incremental. A future worker should
take one row's unfinished task card at a time and must not skip directly from
AI suggestions to publication output.

### Task A: Keep the evidence spine stable

Files are limited to the linked task card, its spec/plan, the affected core
contract, focused tests, and durable memory. Before changing a public DTO,
write a regression that asserts strict JSON, source positions, and failure
reasons. Run the task-scoped verifier and checkpoint only the allowlist.

Expected invariant:

```text
raw input -> deterministic preprocessing -> frame evidence
           -> sequence evidence -> result DTO -> consumer projections
```

### Task B: Extend methods without inventing a second quality language

For each new 1D method, reuse `MetricEvidence` and the existing four levels.
Add method-specific applicability and diagnostic reasons in the method's core
service, then test quantitative/trend/diagnostic/unusable cases and a broken
input case. Do not place method branching in GUI event handlers. The existing
static 1D task explicitly keeps GUI algorithm logic out of scope.

### Task C: Treat sequence rescue as an audit trail

When a frame is weak, emit a candidate with original frame position, source
index, original and proposed parameters, and preservation metadata. Re-run
deterministically before any acceptance decision. A candidate may be displayed
or exported as a candidate, but missing frames and failed primary evidence must
remain visible as such.

### Task D: Bind consumers only to emitted evidence

Workbench, Figure, Manifest, Export, and History may project levels, reasons,
positions, and provenance. They must not recompute SAXS algorithm state or
promote a Diagnostic/Unusable metric because a plot rendered successfully.
Figure roles remain fail-closed when evidence is absent or vetoed.

### Task E: Close real and human gates separately

Use external temporary roots for real replay and retain validation errors in
the result. The current real bundle evidence is intentionally conservative:

- Static: overall quality `Trend`; Guinier, Porod, Kratky, invariant, and
  lamellar evidence `Diagnostic`.
- Temperature: four `Quantitative` frames, one `Diagnostic` frame, and
  sequence Guinier `Unusable` with `guinier_sequence_no_valid_frames`.
- Strain: five `Trend` frame records; the heatmap is near saturation.

These facts must be reviewed by a human scientist. A restarted GUI visual pass,
real temperature/strain meaning review, raw 2D detector/geometry review, and
final release/publication approval are separate gates and cannot be checked off
by this plan's automated tests.

## 4. Verification matrix

For each implementation slice, run the command from its task card and report
the exact output. For this route audit, run:

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-07-26-saxs-quality-analysis-program.md
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_route_audit_verify_20260727'
python scripts/verify.py --task docs/agent/tasks/2026-07-26-saxs-quality-analysis-program.md --changed --types
git diff --check
```

The historical/current-head evidence indexed above is not replaced by a
timeout or an incomplete tool summary. In particular, a full repository run
that has no final pytest summary must be reported as timeout/unknown, never as
pass. The exact SAXS file matrix recorded for the current head is the separate
`364 passed, 4 warnings` result above.

## 5. Checkpoint and review protocol

The route-audit checkpoint allowlist is:

- `docs/superpowers/plans/2026-07-26-saxs-quality-analysis-program.md`
- `docs/agent/tasks/2026-07-26-saxs-quality-analysis-program.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`

After verification, create exactly one local checkpoint:

```powershell
python scripts/auto_commit.py `
  --message "docs(saxs): map quality analysis program evidence" `
  --files docs/superpowers/plans/2026-07-26-saxs-quality-analysis-program.md `
          docs/agent/tasks/2026-07-26-saxs-quality-analysis-program.md `
          docs/agent/memory/active-work.md `
          docs/agent/memory/current-state.md
```

Do not stage or commit existing untracked pytest directories, `.superpowers/`,
GUI/editor drafts, `tests/_tmp_phase3/`, or any parallel task files. Do not
push, merge, deploy, or claim scientific release approval from this checkpoint.

## 6. Self-review checklist

- [x] Every route stage is mapped to an existing task card and linked
  spec/plan; the current matrix names the actual focused/verifier evidence.
- [x] The plan contains no new physics threshold, interpolation policy, rescue
  automation, GUI algorithm branching, or publication promotion rule.
- [x] Current real-bundle limitations and human gates are explicit.
- [x] The verification commands and checkpoint allowlist are exact.
- [ ] Human scientific and restarted-GUI review; these are external gates and
  intentionally not completed by this documentation task.

## 7. Current-state reconciliation addendum (2026-07-30)

This addendum indexes later atomic SAXS evidence without rewriting the
historical stage records above. The linked task cards remain the authoritative
source for individual commands and allowlists.

| Area | Current classification | Evidence boundary |
|---|---|---|
| Temperature 1D Guinier frame and sequence evidence | Automated-ready as diagnostic evidence | Frame/sequence contracts, missing-frame preservation, quality levels, condition/source facts, and the source-mapping trust boundary are covered by the 2026-07-27 cards and the 2026-07-30 source-mapping card. No interpolation, phase decision, or scientific promotion is implied. |
| Series Porod/Kratky/invariant/lamellar source integrity | Automated-ready as conservative evidence | `2026-07-30-saxs-series-metric-source-index-integrity.md` and its Figure/Manifest/Export projection card cover valid, reordered, invalid, duplicate, and length-mismatched mappings. Metric recalculation and physical meaning remain unchanged. |
| Static/temperature/strain dirty-data projections | Automated-ready at the tested consumer boundaries | The 2026-07-28 and 2026-07-29 dirty-input, partial-frame, source-provenance, and projection cards preserve positions and diagnostics. A rendered Figure is not a scientific promotion signal. |
| Raw detector, geometry, mask, and orientation | Contract-ready, scientific acceptance open | Existing raw-detector provenance is transported through results, DataFrame/CSV, Figure, and Workbench surfaces. `validity=not_assessed` remains explicit; calibration, mask validity, beam-center meaning, and real-detector interpretation require instrument-aware review. |
| Candidate rescue and AI | Automated route-ready as candidate/replay/confirm-only | Existing rescue/AI cards require deterministic rerun, data preservation, existing physical gates, sequence evidence, identity/hash checks, and post-gate audit. No provider call or automatic acceptance is claimed here. |
| Workbench/Figure/Manifest/Export/History | Automated transport-ready | Consumer cards cover explicit evidence projection, provenance, partial/dirty data degradation, and export/history boundaries. Consumers do not recompute SAXS state or promote Diagnostic/Unusable evidence. |
| Full software release gate | Open | Current-head SAXS matrices are recorded in their task cards, but a full/boundary pass requires a complete pytest summary and boundary result. Historical Qt crashes/timeouts and unrelated shared-worktree failures are not counted as passes. |
| Real-data and human gates | Open | Restarted-GUI visual review, temperature/strain scientific meaning, raw 2D detector review, and final publication/release authorization remain external gates. |

Current task checkpoints include the 2026-07-30 Guinier source-mapping
implementation (`b47f84e`) and its documentation closure (`09bf6cc`). This
route addendum itself has a separate documentation-only allowlist; it does not
modify `active-work.md`, `current-state.md`, NMR, Joint, or scratch files.
