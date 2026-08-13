# ARS Writing Handoff Acceptance

## Scope

Each immutable evidence package now contains `ars-writing-input.json`, a
versioned claim/evidence map for ARS Results and Discussion preparation.  It
does not draft prose or make scientific conclusions.

## Real PA6 replay

Read-only replay completed with the four selected source types and package:

```text
D:\PolyNexus-pa6-four-technique-smoke-20260814\.polynexus\evidence\ars-writing-handoff-replay-v001
```

The handoff declares `dsc`, `ir`, `saxs`, and `waxs` sections.  It contains 42
`results_candidate` metric IDs, 54 diagnostic/Discussion-only metric IDs, and
6 mandatory human-review items.  The package remains `review_required`.

## Contract boundaries

- Results IDs are derived only from citation metrics whose eligibility is
  `results_candidate`.
- Diagnostic values remain available to Discussion planning and audit, with
  provider reason codes, but cannot enter the Results list.
- FTIR uncalibrated crystallinity remains an index, not `%` crystallinity.
- SAXS applicability gates and WAXS peak-support limitations remain visible.
- Cross-technique sample/batch identity and causal mechanism are explicitly
  prohibited until user-confirmed context and human scientific review exist.

## Verification

```text
python -m pytest -p no:cacheprovider -q tests/test_project_ars_writing_handoff.py tests/test_project_writing_metrics.py tests/test_project_workflow_package.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py
34 passed in 4.01s
```

No raw PA6 source was modified or copied into the package.
