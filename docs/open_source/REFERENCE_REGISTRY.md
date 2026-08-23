# Open-Source Reference Registry

> 核验日期：2026-08-20。此表用于工程选型与复用治理，不构成法律意见。

## 复用等级

- **A** = 可在满足 notice/attribution 等许可要求后选择性直接复用
- **B** = 优先通过 Adapter/独立依赖接入
- **C** = 参考架构、接口、论文/行为或用于对照验证，不直接复制到核心代码

## 项目列表

| 项目 | 最值得借鉴 | 复用等级 | 许可证/边界 |
|------|-----------|----------|-------------|
| MemristorLab | 交互式 Web 教学/UI、current-flow、1T1R vs sneak path | A | MIT |
| rram_multilevel_driver | 1T1R/1R 编程、MLC 写入、post-simulation | A/B | MIT；外部模型可能另有限制 |
| RRAM_COMPILER | 1T1R array、decoder、write driver、sense/peripheral | C | GPL-3.0 |
| MemTorch | 器件模型、crossbar、non-idealities | B/C | GPL-3.0 |
| memristor-models-4-all | 经典 memristor 模型集合、Verilog-A/SPICE | C | 混合来源 |
| MASTODON | 多层 memory simulator、ModelAdapter/层级解耦 | A/B | MIT |
| CrossSim | crossbar 非理想性、寄生线阻、programming error | A/B | BSD-3-Clause |
| DNN+NeuroSim | device→circuit→chip 分层 | C | CC BY-NC 4.0 |
| vlsi_memristor_compact_model | 物理型 RRAM compact SPICE | B/C | GPL-3.0 |
| OpenRRAM | 基于 OpenRAM 的 RRAM compiler | A/B | BSD-3-Clause |

## 使用规则

1. 每个 Sprint 编码前先做 Build-vs-Reuse Decision
2. GPL/CC BY-NC 项目默认 reference-only 或 external adapter
3. 第三方代码进入 repo 前必须记录 commit/tag + license + attribution
4. 复用不降低验收标准
