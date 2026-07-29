# Shared scientific review record contract acceptance

Task: `docs/agent/tasks/2026-07-29-scientific-review-record-contract.md`

Status: implemented and verified; checkpoint hash is reported in the task
handoff.

The technique-neutral contract carries reviewer identity, policy version, source
references, scope-specific decisions, and an explicit status. Missing,
malformed, stale, conditional, rejected, or source-mismatched records remain
fail-closed. The contract itself does not choose IR, NMR, Joint, or release
values.

TDD evidence:

- RED: `python -m pytest -q tests/test_scientific_review.py` failed during
  collection because `polynexus.core.scientific_review` did not exist.
- GREEN: the same command returned `7 passed` after the minimal core contract
  and public exports were added.

The focused regression validates pending/accepted serialization, incomplete
records, invalid scope/status, source/scope mismatch, conditional denial, and
non-finite JSON rejection. Existing IR/NMR/Joint result values and figure roles
remain unchanged; their value-specific review integrations require separately
approved scientific records.
