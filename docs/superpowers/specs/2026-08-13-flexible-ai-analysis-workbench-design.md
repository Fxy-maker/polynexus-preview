# Flexible AI Analysis Workbench Design

## Decision

PolyNexus is one polymer research workbench with two equal entry modes:

1. **Quick Analysis** is the human default. A researcher can drop one file,
   select a folder, or select a temporary series, accept automatic technique
   detection, run a deterministic analysis, inspect/edit charts, adjust a
   bounded setting, rerun, and export.
2. **Project and Evidence** is the AI/Codex/ARS enhancement path. It scopes a
   research question to selected files or candidate groups, runs multiple
   techniques, and produces an immutable evidence package for writing.

Both paths use the same `Project`, `Run`, `Chart`, `EvidencePackage`, and
`Export` contracts. A quick run may be attached to a project later; it must not
become a private GUI-only result.

The GUI does not collect a mandatory manuscript question. ARS/Codex may pass a
question or analysis intent to the project service. A GUI-only request is
operational (selected files, technique, metrics, and figures) and does not
pretend to define a scientific conclusion.

## Goals

- Make the existing quick flow easy to find without rewriting its algorithms.
- Replace unconstrained AI parameter tuning with explainable, bounded adaptive
  analysis.
- Make every AI-assisted decision frozen and replayable.
- Let GUI, CLI, and ARS consume the same result and provenance objects.
- Preserve automatic detection, folder batch selection, NMR processing, and
  Origin/chart editing.
- Complete one real PA6 DSC/FTIR/SAXS/WAXS evidence-to-writing handoff.

## Non-goals

- Removing RAG, Joint, Sample Hub, convergence diagnostics, or Origin in this
  change.
- Letting an LLM write arbitrary numeric parameters into a provider.
- Automatic sample identity, batch identity, or causal scientific conclusions.
- Making every instrument format or every technique publication-ready at once.
- Turning the GUI into a manuscript editor or research-question intake form.

## Surface model

```text
Quick Analysis (default human path)
  file/folder/temporary series
  -> auto-detect dialog or manual technique
  -> deterministic analysis
  -> result/chart inspection
  -> bounded adjustment or robustness check
  -> export or attach to project

Project and Evidence (AI/Codex/ARS enhancement)
  ARS question + selected paths/groups
  -> discovery and canonical conversion
  -> per-technique deterministic runs
  -> shared evidence package
  -> citation metrics, figures, limitations, review actions
  -> ARS Results/Discussion input

Advanced tools (contextual)
  AI diagnostics, plan comparison, Joint relation review,
  convergence details, specialist adapters, optional Origin export
```

The sidebar and home screen should expose Quick Analysis first. Project and
Evidence is a prominent secondary route for multi-file work. Advanced tools
appear from a run, selected project data, or an explicit expert action; they do
not become separate competing workflows.

## Shared AnalysisPlan contract

`AnalysisPlan` is the public, versioned description of one deterministic run
or one bounded adaptive decision. It is produced by GUI, CLI, or ARS through a
shared service and consumed by the deterministic runner, history, evidence
packaging, and replay UI.

Required fields:

```text
plan_version
plan_id
parent_run_id / replan_of (nullable)
source_files: path, sha256, byte_size, source_order
scope: project_id, group_id, technique, selected_ranges
analysis_intent (nullable ARS/Codex text)
requested_metrics, requested_figures
canonical_template_id + conversion_version
algorithm_id + algorithm_version
default_config
candidate_configs[]: config, generation_rule, score, rejection_reasons
protected_metrics, scientific_constraints, review_thresholds
ai_context: provider, model_version, input_hash, prompt_hash,
            output_hash, decision_hash (nullable for non-AI runs)
random_seed
selected_candidate_id
approval: state, actor, timestamp, note
replay: status, source_manifest_hash, replayed_from_run_id
```

The runner validates source hashes, template versions, algorithms, candidate
legality, and protected metrics before execution. A frozen plan replays without
calling an AI model. Asking AI to reconsider creates a new `replan` run and
leaves the prior run immutable.

## Adaptive analysis behavior

The default configuration runs first. The result exposes deterministic symptoms
such as baseline drift, peak instability, noisy frames, discontinuous trends,
or cross-technique disagreement. AI may classify symptoms, select a method
family to inspect, prioritize checks, and explain trade-offs. It may not invent
provider values or optimize a single cosmetic score.

The deterministic robustness service generates a finite legal candidate set and
computes comparable metrics: protected peak/area retention, peak shift,
baseline residual, trend continuity, physical constraints, uncertainty, and
runtime cost. Candidates are labeled `stable`, `sensitive`, or `unusable` with
machine-readable reasons. The user or an approved policy selects a candidate;
the selected plan and rejected alternatives remain in provenance.

GUI labels should be “分析建议”, “稳健性检查”, and “比较处理方案”. The CLI
route should be `evaluate-analysis-plans`. Existing `ai-tune` remains a
compatibility wrapper until the new plan route is proven.

## Module disposition

| Capability | New role | Immediate action |
| --- | --- | --- |
| DSC/IR/SAXS/WAXS/NMR | deterministic technique producers | retain existing paths |
| Automatic detection | quick-flow gate | retain popup and manual override |
| Folder batch | quick/project scope selector | retain, never merge unrelated groups by default |
| Origin | chart editing/export context | retain optional adapters and standard fallback |
| Sample Hub | contextual project metadata/history | remove mandatory database-first ceremony |
| Joint | AI/Codex cross-technique relation and conflict check | GUI shows summary and review actions |
| Convergence view | adaptive-analysis diagnostics | open from a run, not main navigation |
| Plan evaluation | bounded robustness/sensitivity comparison | replace “best-looking AI tuning” narrative |
| RAG | optional adviser dependency candidate | freeze expansion; decide after plan workflow evidence |
| Polymer reference tables | deterministic support data | retain independently of RAG |

No module is deleted by this design. Retirement requires a separate task card,
consumer audit, focused regression coverage, and human architecture review.

## Data flow and evidence boundary

```text
raw file(s)
  -> discovery/group selection
  -> canonical template conversion
  -> AnalysisPlan
  -> deterministic provider run(s)
  -> Chart/Table/Metrics + provenance
  -> EvidencePackage
  -> citation-metrics + writing-evidence + ars-writing-input
```

Cross-technique membership is explicit. Filename or notes may create a
candidate association, but the package records it as inferred or user-approved;
instrument files are never claimed to prove formulation, batch, or causal
identity. Diagnostics stay Discussion-only or review-required according to the
existing scientific policy.

## Failure and review rules

- Ambiguous mixed directories require a selected path/group before provider
  execution.
- Missing, changed, or tampered sources fail replay before analysis.
- Invalid canonical conversion or illegal candidate configuration blocks the
  run with a machine-readable reason.
- A provider may complete computation while the package remains
  `review_required`; computation, data quality, and publication status stay
  separate.
- Human review is required for source grouping corrections, candidate approval
  when thresholds are crossed, scientific interpretation, and final writing.

## Staged implementation

1. Quick Analysis navigation/entry convergence; no algorithm changes.
2. `AnalysisPlan` schema, validation, hashing, and replay contract.
3. Frozen-plan replay and immutable replan lineage.
4. AI symptom diagnosis plus deterministic robustness candidate service.
5. Shared GUI/CLI/ARS DTOs and plan/evaluation views.
6. Sample Hub simplification and quick-run project attachment.
7. Joint, convergence, and plan evaluation contextual migration.
8. RAG optionalization/removal assessment after replacement evidence.
9. Real PA6 end-to-end replay and ARS handoff acceptance.

Each stage has a task card, focused regression test, producer/consumer proof,
and an allowlisted checkpoint. Architecture/schema/scientific stages remain
human-review-required before merge.

## Acceptance definition

The redesign is successful when a researcher can complete a quick analysis in a
short path, while ARS/Codex can select a PA6 group and execute DSC/FTIR/SAXS/WAXS
through the same contracts to an immutable package containing figures, citable
metrics, evidence limits, and writing inputs. Replaying the frozen plan must
produce the same deterministic result without asking AI again.
