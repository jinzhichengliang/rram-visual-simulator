# ADR-0001: Single Source of Truth — FrameState

## Status
Accepted (S00)

## Context
RRAM Visual Simulator 需要六个视图（Device、1T1R Cell、Array、Circuit、Waveform、Filament）+ Explanation Engine 协同工作。如果每个视图各自维护状态，将导致数值不一致、因果链断裂、教学误导。

## Decision
采用单一不可变 FrameState 作为所有视图和解释模块的唯一事实来源。

- 每个仿真时间点生成一个不可变 FrameState 对象
- 所有视图通过 selector 纯函数读取 FrameState，不得写入
- 所有状态转移由 Simulation Core 判定，前端不决定 SET/RESET
- 波形数据由 FrameState 历史序列生成，不画第二套波形
- Explanation 由 OperationSpec + FrameState + DeviceProfile + CheckResult 组合生成

## Consequences

### Positive
- 六视图天然一致，无需手动同步
- 可回溯任意历史帧（scrub）
- 跨视图测试可自动化
- 模型替换（Teaching → Compact → SPICE）不改 UI

### Negative
- 每次状态变化都要生成完整 FrameState（性能需关注）
- 需要严格定义 schema 并在 Python/TS 间同步

## References
- docs/architecture/guardrails.md
- 《开发设计文档 V1.1》第 3 章
