# SAXS Scientific Acceptance Audit Lifecycle Consistency Design

**Date:** 2026-07-28
**Status:** Approved working design for the active SAXS quality goal

## Problem

SAXS parameter construction occurs before the shared post-analysis validation
hook. The temperature and strain branches now attach a read-only scientific
acceptance audit during parameter construction, so a later validation error can
leave only the audit's validation snapshot stale even though the final result
flag is correct.

## Goal

Synchronize an existing SAXS scientific acceptance audit with the final SAXS
validation state without changing the audit contract or any scientific result.

## Design

`SAXSEngine._validate_results()` keeps its current sequence:

1. run the existing superclass validation;
2. publish the existing SAXS result contract;
3. if `result.parameters` is a mapping containing
   `scientific_acceptance_audit`, rebuild only that nested audit with the final
   `result.validation_passed` and the already-published parameters.

The refresh is conditional so static SAXS payloads and legacy payloads without
an audit are byte-for-byte behaviorally unchanged. Temperature and strain both
benefit because they already attach the same builder output.

## Safety boundary

The refresh reads existing validation, quality, provenance, reliability, reason,
and publication fields only. It adds no numerical threshold, does no
interpolation or rescue, does not re-run Guinier or any physical calculation,
and never changes `publication_decision_changed=False`.

## Verification

The regression will first demonstrate the stale cached snapshot, then verify
that the final result and audit agree after `_validate_results()`. An optional
real PA6 temperature run confirms the same boundary on five frames. The exact
SAXS matrix, task-scoped verifier, diff check, and explicit allowlist checkpoint
are required.
