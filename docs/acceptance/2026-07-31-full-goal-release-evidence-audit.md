# Full-goal release evidence audit acceptance

Task: `docs/agent/tasks/2026-07-31-full-goal-release-evidence-audit.md`

## Audit result

The software implementation has broad automated and structural coverage across
SAXS, DSC, WAXS, IR, NMR, Joint, and the shared Results Workbench. That result
does not equal final scientific or publication approval. The current project
disposition remains **conditional**.

## Evidence sources

- Overall requirements and module coverage:
  `docs/agent/tasks/2026-07-29-full-goal-requirements-audit.md`
- Decision fields and conditional release policy:
  `docs/agent/tasks/2026-07-29-release-decision-packet.md`
- IR official vendor semantics and Results provenance:
  `docs/agent/tasks/2026-07-30-ir-mapping-results-provenance.md` and
  `docs/acceptance/2026-07-30-ir-thermo-mapping-semantics.md`
- NMR solid-C readiness:
  `docs/agent/tasks/2026-07-30-nmr-solid-c-readiness.md`
- Joint conflict evidence:
  `docs/agent/tasks/2026-07-28-joint-evidence-weighted-conflicts.md`
- SAXS post-Workbench real boundary:
  `docs/agent/tasks/2026-07-31-saxs-post-workbench-real-boundary.md` and its
  acceptance record, after the parallel thread's final update.

## Safe publication consequences

- IR mapping without source-matched native coordinates/calibration remains
  `review_required` and diagnostic-only.
- NMR solid-C without assignment truth and calibrated ppm axis remains
  `assignment_limited`; Xc cannot be promoted.
- Joint with unresolved scientific conflicts remains diagnostic-only; no
  technique receives automatic scientific priority.
- Automated GUI route coverage is structural evidence only. A restarted-GUI
  walkthrough and owner acceptance are still required.
- The final release packet remains conditional until the human and
  source-specific gates close.

## Latest evidence amendment (2026-08-01)

- SAXS 2D reviewer context is checkpointed at `a9e0743` and projects existing
  detector, geometry/mask, beam-center, orientation, gate, and scientific-review
  evidence without recalculation or publication promotion.
- Independent focused compatibility coverage passed `58`; the complete SAXS
  file matrix passed `700 passed, 6 warnings in 530.15s`, exit `0`.
- The latest formal full/boundary verifier reached its 40-minute tool bound,
  returned exit `124`, and emitted no complete pytest summary. The managed
  child manifest recorded exit `3` at the timeout/reap boundary; this remains
  incomplete tool evidence, not a test pass or product failure.
- The release disposition remains conditional. IR mapping remains
  `review_required`/diagnostic-only, NMR solid-C remains assignment-limited,
  unresolved Joint conflicts remain diagnostic-only, and restarted-GUI plus
  owner scientific/release approval remain open.

## Verification record

The commands below were run after the three audit files were complete. Their
real exit codes and summaries are recorded here; a missing summary or tool
timeout is classified as incomplete, never as pass.

```powershell
python scripts/boundary_audit.py --root D:\PolyNexus --json
python scripts/verify.py --task docs/agent/tasks/2026-07-31-full-goal-release-evidence-audit.md --changed --types
git diff --check
```

Observed outcomes:

- `boundary_audit.py --root D:\PolyNexus --json` exited `0`.
- The task-scoped verifier exited `0`; task/memory checks, Ruff, compile,
  type-baseline, whitespace, quality `297 passed`, and preprocessing
  `106 passed` all passed.
- `git diff --check` exited `0`.
- A first verifier attempt hit a pre-existing Windows permission error while
  compiling `tests/_tmp_phase3`; the immediate rerun completed successfully.
  No production or test source was changed by this audit.

## Checkpoint boundary

Only the audit task, plan, and acceptance files may be included in this
task's explicit allowlist checkpoint. Parallel memory, SAXS, pytest, and test
storage changes remain untouched.
