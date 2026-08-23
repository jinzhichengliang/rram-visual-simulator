# Decision Log

> 持续维护。每次涉及架构/物理/契约的决策都记录在此。

| 决策项 | 当前值 | 变更日期 | 变更原因 |
|--------|--------|----------|----------|
| Device orientation | BL–RRAM–NMOS–SL；WL→Gate | S00 | 默认教程基线 |
| V_RRAM sign | V(top_electrode) − V(bottom_electrode)，top = BL 侧 | S00 | 与 profile 一致 |
| Polarity profile | SET: V_RRAM > 0; RESET: V_RRAM < 0; LRS=1, HRS=0 | S00 | 双极性教学基线 |
| Fidelity level | N/A (S00 无模型) | S00 | — |
| State equations | N/A (S00 无模型) | S00 | — |
| Sense rule | N/A (S00 未实现) | S00 | — |
| Array bias policy | N/A (S00 未实现) | S00 | — |
| Tolerance | N/A (S00 未实现) | S00 | — |
| Golden versions | N/A (S00 未实现) | S00 | — |
| Known limitations | S00 不含任何 RRAM 物理逻辑 | S00 | Bootstrap 阶段 |
