---
kind: design
status: approved
date: 2026-07-20
title: Legacy worktree adoption
---

# Legacy worktree adoption

## Goal

Make old Superpowers worktrees visible to the current lifecycle manager without
making a bulk deletion decision implicitly.

## Behavior

`worktree_manager.py adopt-legacy` scans only unregistered worktrees whose path
is inside the user-level PolyNexus Superpowers directory and whose branch starts
with `codex/`. It excludes the current repository worktree and all paths outside
that directory.

The default is a JSON report/dry-run. With `--apply`, clean candidates are
registered as agent-owned `pending_cleanup` records with a fresh one-hour
cooldown. Dirty candidates are archived into the existing structured WIP archive
and registered as `legacy_dirty`; they are never made cleanup-eligible.

The command never deletes worktrees or branches. A later `clean --apply` may
remove only clean, matching, agent-owned candidates after the cooldown.

## Safety boundary

Adoption is explicit and opt-in. The path and branch filters prevent a bulk
operation from claiming the canonical runtime worktrees or arbitrary user
worktrees. Git state remains authoritative for every later deletion decision.
