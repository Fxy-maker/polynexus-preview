---
task_id: 2026-07-30-nmr-solid-c-readiness
status: verified-checkpoint-pending
date: 2026-07-30
---

# NMR Solid-C Readiness

This slice makes existing NMR solid-13C assignment and ppm-axis boundaries
visible to shared evidence and Results review. It does not assign peaks,
calculate Xc, reinterpret JEOL metadata, calibrate an axis, or promote a
figure.

## Evidence

| Check | Result |
| --- | --- |
| `tests/test_analysis_evidence.py -k nmr` | `13 passed, 129 deselected`, exit 0 |
| `tests/test_results_review_service.py -k nmr` | `1 passed, 28 deselected`, exit 0 |
| changed-file Ruff | passed, exit 0 |
| `tests/test_nmr_figure_provider.py` | `6 passed`, exit 0 |
| `tests/test_nmr_figure_document.py` | `5 passed`, exit 0 |
| solid-C lifecycle shard | `1 passed, 3 deselected in 148.24s`, exit 0 |
| NMR engine shard | `19 passed in 112.93s`, exit 0 |
| full NMR lifecycle shard | tool-level timeout, no pytest summary |

The full lifecycle row is deliberately classified as a tool-level timeout
because it produced no pytest summary. It is not treated as a full-suite pass.

## Boundary

`assignment_readiness` projects the pre-existing `Xc_assignment_status` and
sample/nucleus context. `axis_evidence` remains the existing source of axis
provenance. Missing or limited assignment remains fail-closed, and no human
scientific review or final release approval is implied.

## Remaining

Task-scoped verification passed with quality `292` and preprocessing `106`;
Ruff, compile, memory/task, whitespace, boundary audit, and `git diff --check`
also passed. The explicit allowlist checkpoint is the remaining handoff action.
