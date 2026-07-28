# Results Review prefix deduplication implementation plan

> For agentic workers: execute the steps in order and keep the changed-file
> allowlist explicit.

**Goal:** Prevent shared Results Review risk and next-step labels from being
  rendered more than once.

**Architecture:** Keep all technique-specific text producers unchanged. Strip
  leading localized panel decoration at the shared service boundary, then use
  the existing `tr(...)` formatter once.

### Task 1: Prove the regression

- [x] Add direct panel tests for repeated English and Chinese prefixes.
- [x] Add a window fallback test with already-formatted labels.
- [x] Run the focused test file and record RED/GREEN evidence.

### Task 2: Normalize at the shared boundary

- [x] Add a small pure prefix normalizer in `results_review_service.py`.
- [x] Apply it to validation/risk and fallback next-step input only.
- [x] Preserve all non-leading evidence text and existing fallback behavior.

### Task 3: Verify and checkpoint

- [x] Run focused Results Review tests.
- [x] Run the structured changed/type verifier and `git diff --check`.
- [x] Update durable memory and create one explicit allowlist checkpoint.
