---
kind: lesson
status: active
date: 2026-07-31
title: Synchronize existing SAXS review evidence through the manifest
---

# SAXS existing review sync lesson

The structural Figure manifest is a safe index for refreshing already-published
SAXS document evidence. Updating only the linked document's detached review
provenance preserves Figure IDs, roles, revisions, sources, and manifest
compatibility. A missing or malformed manifest must remain a diagnostic no-op.

For verification, the repository's `--changed` Ruff set includes unrelated
uncommitted files. Run the task's own-file Ruff checks and the type/quality gates
separately, then record the changed-file verifier limitation instead of fixing
or staging parallel baseline work. A long SAXS matrix without a final pytest
summary is a timeout, never a pass.
