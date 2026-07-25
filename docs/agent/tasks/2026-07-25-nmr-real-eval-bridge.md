# NMR real-engine evaluation bridge

## Goal

让 NMR 的 liquid/solid H/C 分区进入现有 `EvalRunner` 的真实 engine 路径，
并保留 `engine`、`submodule`、峰位、峰数、SNR、Xc 和拟合质量等评测输出。

## Non-goals

- 不改变 NMR 峰检测、assignment gate、Xc 科学语义或 GUI 行为。
- 不伪造 NMR real-data fixture；本卡只修复 engine bridge contract，真实数据源仍需单独注册。

## Affected boundaries

- `tests/eval/runner.py` 的 real-engine dispatch、配置覆盖、参数提取。
- `tests/eval/test_runner_real_nmr.py` 的 bridge regression。

## Acceptance criteria

- [x] 四个 NMR submodule 可被 `_uses_real_engine` 识别。
- [x] real path 调用 `get_engine("nmr", submodule_id=...)`，并输出峰位与 provenance。
- [x] AI/off 或缺省配置时仍走确定性 engine path，不依赖 AI。
- [ ] focused eval、Ruff、结构化 verifier 均通过。

## Implementation plan

1. 先添加 NMR real bridge regression，观察现有 allowlist 的预期失败。
2. 扩展 `EvalRunner` 的 NMR dispatch、配置 alias、参数提取和 plain-value 序列化。
3. 运行 NMR 与既有四技术评测矩阵，再运行结构化 verifier 和 atomic checkpoint。

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_nmr_eval_bridge'
python -m pytest tests/eval/test_runner_real_nmr.py tests/eval/test_runner_real_ir.py tests/eval/test_runner_real_dsc.py tests/eval/test_runner_real_saxs.py tests/eval/test_waxs_publication_real_data.py tests/eval/test_dsc_publication_real_data.py -q
python -m ruff check tests/eval/runner.py tests/eval/test_runner_real_nmr.py
python scripts/verify.py --task docs/agent/tasks/2026-07-25-nmr-real-eval-bridge.md --changed --types
```

## Known limitation

仓库目前没有已登记的 NMR vendor/real regression source；本卡的 real bridge
contract test 使用 temporary table path 和 engine double，不能替代科学人员对
真实仪器数据的 acceptance。
