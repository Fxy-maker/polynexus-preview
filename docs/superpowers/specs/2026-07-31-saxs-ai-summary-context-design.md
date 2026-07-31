---
title: SAXS AI summary-only context contract
date: 2026-07-31
status: approved-provisional
---

# SAXS AI summary-only context contract

## Decision

Introduce one deterministic, strict-JSON context projection for the SAXS AI
prompt. It may contain only existing frame/series quality and physical-evidence
summaries. It must not contain raw q/I arrays, 2D detector pixels, source file
paths, or new scientific thresholds.

The projection is an input contract only. It does not call a model, generate a
preprocess intent, execute a candidate, alter a configuration, or change any
quality level, physical gate, rescue state, publication role, Figure, Manifest,
or Export behavior.

## Data flow

`existing SAXS result evidence -> summary-only context -> PromptBuilder -> model
intent payload -> existing SAXS validator -> existing candidate/decision gates`.

The context reuses `build_saxs_confirmed_rerun_evidence()` and
`assess_saxs_confirmed_rerun()`. These functions already project compact
evidence and apply the existing status checks. The prompt receives the
detached context through an explicit `saxs_ai_context` field on
`current_sample`; callers that do not provide it retain the current prompt.

## Safety contract

- `technique` is always `SAXS`; unsupported modes return an unavailable,
  strict-JSON context rather than inferred evidence.
- The context records `raw_profile_included=False`,
  `raw_detector_data_included=False`, `candidate_only=True`, and
  `physical_validation_required=True`.
- Only the existing compact evidence fields are projected. No interpolation,
  imputation, frame deletion, reordering, threshold, or new physical rule is
  introduced.
- The prompt explicitly tells the model to use the context diagnostically and
  return only the existing preprocess-intent contract. It does not grant the
  model authority to accept, apply, or publish a candidate.

## Acceptance

1. A result with existing evidence produces strict JSON containing quality and
   physical statuses while excluding raw q/I and detector arrays.
2. Unsupported or absent evidence produces an unavailable context with an
   explicit reason and no fabricated values.
3. A SAXS prompt includes the context and its no-raw-data/candidate-only
   boundary when supplied.
4. Existing prompts and all existing validator/decision behavior remain
   unchanged when the optional context is absent.
5. Focused TDD, task verification, exact SAXS matrix, diff check, and an
   explicit changed-file allowlist checkpoint are recorded.
