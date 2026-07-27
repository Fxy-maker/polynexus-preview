# SAXS 质量证据导出任务卡

## Goal

让 SAXS 导出包携带与分析结果一致的质量、序列救援、2D 和 AI bridge provenance。

## Non-goals

- 不改变 SAXS 算法、原始数据、Figure 角色或 Workbench 主结论。
- 不执行候选、不调用模型、不推断缺失证据。

## Affected boundaries

- `polynexus/core/saxs_export_bundle.py`
- `tests/test_saxs_export_bundle.py`
- `docs/superpowers/specs/2026-07-27-saxs-quality-export-provenance-design.md`

## Implementation plan

1. 写失败回归，锁定 `quality_evidence.json`、静态/温度/应变证据和 AI 审计字段。
2. 在 Export Bundle 边界构造只读 JSON-safe quality snapshot，并加入 bundle manifest 文件索引。
3. 运行 SAXS export/provider/lifecycle、完整 SAXS 和结构化 verifier，创建 allowlist checkpoint。

## Acceptance criteria

- [x] `quality_evidence.json` 在成功导出中生成并登记到 bundle manifest。
- [x] 静态/温度/应变已有质量证据、序列证据和救援候选被保留，缺失项不伪造。
- [x] 可选 AI plan/decision 只被审计导出，`apply_allowed` 等状态不被改变。
- [x] 现有导出、Figure、Manifest、Workbench 回归保持通过。
- [x] focused、完整 SAXS、task verifier 和 quality/preprocessing gates 有实际证据。

## Verification

```powershell
python -m pytest tests/test_saxs_export_bundle.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-quality-export-provenance.md --changed --types
```

## Verification evidence (2026-07-27)

- Focused export bundle tests: **4 passed**; provider/document/result export
  slice: **27 passed, 4 warnings**.
- Complete PowerShell-expanded SAXS matrix: **260 passed, 4 warnings**. The
  warnings remain the existing Arial CJK glyph warnings.
- `quality_evidence.json` is registered in `bundle_manifest.files` and keeps
  static evidence plus optional AI plan/decision as audit-only data.

## Known limitations

本任务只关闭导出 provenance；重启 GUI 视觉审查、真实数据科学 sign-off 和最终发布政策仍开放。

## Changed-file allowlist

- `polynexus/core/saxs_export_bundle.py`
- `tests/test_saxs_export_bundle.py`
- this task card
- `docs/superpowers/specs/2026-07-27-saxs-quality-export-provenance-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-quality-export-provenance.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
