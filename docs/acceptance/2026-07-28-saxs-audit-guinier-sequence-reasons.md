# SAXS acceptance audit Guinier sequence evidence

Status: automated evidence transport recorded; scientific review gates remain
unchanged.

## Recorded evidence

- The existing audit builder now reads the existing
  `guinier_sequence_evidence` mapping without mutating it.
- Real source: `D:\PolyNexus\测试数据\saxs\pa6变温`, five frames at 170--220 °C.
- Real audit evidence now includes
  `evidence_levels.guinier_sequence_evidence=["Unusable"]` and the existing
  `guinier_sequence_no_valid_frames` reason. The spelling in the persisted key
  is the canonical `guinier_sequence_evidence`.
- No Guinier calculation, frame order, missingness, physical threshold, rescue,
  AI, publication, or export decision changed.

## Verification

- RED: `2 failed` with the expected absent sequence evidence key.
- GREEN: `2 passed in 15.35s`.
- Exact SAXS matrix: `441 passed, 6 warnings in 88.00s`.
- Structured verifier:

  ```text
  python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-audit-guinier-sequence-reasons.md --changed --types
  exit 0; task/memory, Ruff, compile, type baseline, quality, preprocessing,
  and whitespace checks passed.
  ```

- `git diff --check` passed. No timeout or historical process is counted.

## Boundary

This is diagnostic evidence transport only. `Unusable` sequence evidence stays
unusable and does not become quantitative or publication-ready.
