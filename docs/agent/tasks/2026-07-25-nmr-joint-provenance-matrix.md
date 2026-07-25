# NMR and Joint published-run provenance matrix

## Goal

把 NMR 四分区共享 Figure provider 和 Joint hub 的真实发布 run 接到同一条
Manifest → active Gallery → document/data provenance 验收路径，并锁定失败/诊断
figure 不会悄悄变成 Main 结论。

## Non-goals

- 不改变 NMR peak、assignment、Xc 或 Joint 冲突的科学算法。
- 不把 assignment-limited Xc 变成确定性结论。
- 不替代真实数据和重启 GUI 的人工科学/视觉 review。

## Affected boundaries

- `polynexus/core/nmr.py`、`polynexus/core/joint/` 的发布入口。
- `polynexus/core/figures/manifest.py`、`polynexus/gui/plot_gallery_service.py`。
- NMR/Joint focused lifecycle tests and acceptance notes.

## Acceptance criteria

- [x] NMR synthetic published run has ready Manifest entries, active Gallery entries,
  object-editing capability, and run-relative document/data sources.
- [x] Joint published run has the same Gallery/provenance evidence and preserves
  main/SI/diagnostic roles.
- [x] Diagnostic/failure entries remain visible in the Manifest with their role and
  status; no silent omission or promotion occurs.
- [x] Focused matrix and structured verifier are recorded; checkpoint commit is the final handoff step.

## Implementation plan

1. Add failing NMR/Joint published-run Gallery/provenance tests using existing DTOs.
2. Run the tests red, then make only the smallest lifecycle adapter changes required.
3. Re-run the focused NMR/Joint and shared Manifest/Gallery matrix.
4. Run the task verifier, update acceptance/memory, and create an allowlisted checkpoint.

## Verification

```powershell
python -m pytest tests/test_nmr_joint_provenance_matrix.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-25-nmr-joint-provenance-matrix.md --changed --types
```
