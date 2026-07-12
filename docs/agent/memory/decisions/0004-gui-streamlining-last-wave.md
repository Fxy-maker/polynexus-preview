---
kind: decision
status: active
date: 2026-07-12
title: Use contextual ownership for the final GUI streamlining wave
---

## Decision

GUI streamlining is the final large UI wave. The approved interaction baseline
converges on five stable workspaces—Data, Config, Results, Plots, and History—
with Sample Library and Joint Analysis remaining contextual workflows. Code
changes are applied in slices, and duplicate routes are removed only after a
tested replacement exists.

## Retention boundary

Scientific modules, raw evidence, result tables, history, samples, joint
analysis, manifest-backed plots, explicit legacy recovery, export contracts,
theme/language, logs, and keyboard/accessibility behavior remain. Only duplicate
routes may become removal candidates, and only after a tested contextual
replacement exists.

## Sequencing boundary

The later implementation must proceed in slices: workspace ownership, Results
and History review, Plots preview/view/edit ownership, Sample/Joint routing, and
only then duplicate-route cleanup. No slice may silently alter scientific
semantics or delete historical data.

## Source of truth

The complete interaction baseline is recorded in
`docs/superpowers/specs/2026-07-12-gui-streamlining-interaction-plan.md`.
