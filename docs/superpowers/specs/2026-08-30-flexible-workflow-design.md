# Flexible Workflow and Routing Design

## Goal

减少 PolyNexus 多技术项目入口中的僵硬路由判断，让合法输入由 canonical
转换结果决定是否继续，同时保留科学有效性、来源哈希和审查边界。

## Decisions

- 删除 `TechniqueSeriesAdapter` 基于路径片段名称的技术不匹配拦截。
- 删除 `MixedTechniqueAdapter` 对 IR 温度目录文件数量的重复预判；目录路由
  统一交给 IR canonical converter，转换器仍负责至少两个有效帧和温度轴解析。
- 保留单输入/序列/目录各自的科学语义；只抽取 manifest、artifact 和
  canonical conversion 的最小共享 helper。
- 保留 NMR 四模式显式子模块、IR 二维最少帧、探测器二维 shape、源文件哈希
  绑定，以及 `review_required`/`diagnostic_only` 状态。
- CLI、GUI、AI 继续消费同一 `AnalysisRecipe`、`ComputeRun`、evidence DTO，
  不新增私有表示。

## Acceptance

1. 合法但目录名含其他技术词的系列输入不再因路径命名被阻断。
2. 混合入口不再复制 IR 文件数量判断；无效目录仍由 canonical converter 返回
   明确原因并阻断，不能伪造二维结果。
3. 重复 helper 被合并后，单输入、序列、IR 温度和混合 recipe 的序列化、哈希
   绑定和 ComputeRun 回归测试保持通过。
4. 科学约束和四类 NMR 显式模式行为不变。
