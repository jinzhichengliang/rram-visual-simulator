# Physics Assumptions (Conceptual Model)

> S00 占位。S02 实现 Teaching Model 时填充具体假设。

## 当前状态

本阶段（S00）不包含任何 RRAM 物理逻辑。以下仅为后续开发的概念性框架记录。

## 待定义（S02+）

- F0 教学模型的状态转移规则
- NMOS 简化模型（ON/OFF gating）
- Forming / SET / RESET / READ 的阈值条件
- Compliance 限流行为
- Sense amplifier 判决逻辑

## 原则

1. 所有物理假设必须写入 DeviceProfile，不硬编码
2. 示意参数与工艺参数分离，始终标注 fidelity level
3. 每个模型版本必须记录状态方程来源
