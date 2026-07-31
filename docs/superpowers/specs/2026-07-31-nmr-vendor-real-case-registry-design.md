# NMR Vendor Real-Case Registry Design

## Goal

Register the four existing NMR vendor inputs as real-engine evaluation cases
without inventing scientific ground truth or changing assignment/Xc policy.

## Scope

- add four JSON case descriptors for liquid H/C and solid H/C;
- add the explicit provenance value `vendor_unreviewed` to the EvalCase schema;
- run each registered input through the real NMR engine with output redirected
  to an external temporary directory;
- preserve source identity and assignment-limited status in the evaluation
  output.

## Non-goals

- do not edit the files under `测试数据/NMR`;
- do not add peak assignments, Xc ranges, ppm calibration, or reviewer scores;
- do not change NMR analysis, figure roles, Results review, Joint policy, or
  publication promotion;
- do not use test-storage `--apply`.

## Safety boundary

`vendor_unreviewed` is a provenance category, not an acceptance category. A
case with empty `ground_truth` may exercise parsing, engine dispatch, output
provenance, and fail-closed readiness, but it must not be reported as an
expert-reviewed scientific pass.
