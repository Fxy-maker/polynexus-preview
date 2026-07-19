# Known Issues

## Process and tooling

| Issue | Impact | Workaround | Follow-up |
| --- | --- | --- | --- |
| CI workflow is newly added and has not run in this local workspace | Provider-specific dependency or Qt issues may still surface | Run the same command locally with `QT_QPA_PLATFORM=offscreen` | Monitor first PR runs |
| Full-repo Ruff check has existing findings | Lint cannot yet be a clean global gate | Start with changed-file or error-class checks | Ratchet Ruff in stages |
| Full `python scripts/verify.py --full` exceeds 10 minutes without a reported failure in this workspace | Full-suite completion cannot currently be used as a timely handoff gate | Use the passing boundary, focused, and feature-specific suites; continue investigating suite runtime separately | Profile the slowest full-suite partitions and add runtime budgets |
| Project-wide Pyright is not yet enabled | Type regressions outside the agent tooling baseline may escape checks | Run `python scripts/verify.py --changed --types` | Expand the baseline by module |
| Large GUI, service, and test files exist | Boundary changes are harder to review | Prefer new focused modules and tests | Split one boundary at a time |
| Local generated outputs coexist with source | Broad recursive scans can be noisy or slow | Use tracked/source paths and maintenance scripts | Improve artifact isolation |

## Memory hygiene

- Runtime `work_memory` and analysis history are product data, not substitutes for
  repository agent memory.
- Do not treat generated RAG indexes as canonical project decisions.
