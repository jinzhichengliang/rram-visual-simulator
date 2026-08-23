# Architecture Guardrails

> S00 建立。任何新增功能前必须阅读本文件。

## 第一原则：Single Source of Truth

六个视图（Device、1T1R Cell、Array、Circuit、Waveform、Filament）+ Explanation + Waveform cursor 全部只消费同一个不可变 FrameState。任何视图、selector、动画组件都不得自行决定 SET/RESET、R、gap、sense decision。

## 因果顺序（固定）

```
Operation Intent → Decoder/Driver → WL/BL/SL Bias → Access Transistor
→ V_RRAM → I_RRAM / Compliance → Device Internal State → R_RRAM
→ Sense Result → Logic State / Verify Decision
```

任何代码不得跳过或颠倒这个顺序。

## 架构红线

1. **View 不写状态** — View/selector/animation 不得创建或修改 rram.state、R、gap、formingDone、sense decision。
2. **V_RRAM 来自 Core** — 不得在 UI 用 BL−SL 临时替代实际器件端电压。
3. **极性可配置** — SET/RESET 极性、logic map 来自 DeviceProfile，不得硬编码"BL 正压=SET"。
4. **Filament 不造物理** — 动画只消费 model observable，不得成为第二物理模型。
5. **Array 不复制模型** — 每个 array cell 实例化统一 ModelAdapter，不在 Array 内重新实现 cell 逻辑。
6. **随机默认关闭** — 所有随机源使用 seeded RNG，FrameState 记录 seed。
7. **Profile 版本化** — 参数变更必须版本化，golden scenario 显式 pin profile version。

## 物理可信度分层

| 层级 | 含义 | 展示方式 |
|------|------|----------|
| F0 | 教学模型 | 明确标注 "Conceptual" |
| F1 | 参数化 compact | 显示状态变量和模型版本 |
| F2 | SPICE/Verilog-A | 经适配器展示，标注数据来源 |
| F3 | TCAD/实验校准 | 用于对照，不与实时模拟混淆 |

## 何时不算 S00 完成

- 存在任何 RRAM 状态转移代码
- 存在假波形/假动画数据
- View 内有业务物理逻辑
- 没有 health endpoint 或 CI 不绿
