# FTIR No-Auto-Material Identification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stop FTIR from inferring a polymer identity when no material hint is supplied.

**Architecture:** Gate database assignment on explicit `polymer_name`; preserve generic provider outputs.

---

### Task 1: Regression tests

- [ ] Add no-material test and observe failure.

### Task 2: Minimal provider fix

- [ ] Remove automatic peak-based polymer selection.
- [ ] Keep explicit-material path unchanged.

### Task 3: Verification and checkpoint

- [ ] Run focused and structured verification.
- [ ] Record acceptance and checkpoint.
