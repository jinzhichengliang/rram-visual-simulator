# RRAM Visual Simulator

一个教学优先的交互式 RRAM/1T1R 可视化仿真平台，用于学习和理解 RRAM 存储器的工作原理。

## 功能特性

### 核心视图
- **Device View**: 展示 RRAM 器件两端的电压、电流和状态
- **1T1R Cell View**: 展示 BL/WL/SL 如何控制单个存储单元
- **Array View**: 4×4 阵列可视化，展示单元选择机制
- **Filament View**: 导电细丝的可视化（支持 F0/F1 模型）
- **Circuit View**: 外围电路（Decoder/Driver/Sense Amplifier）
- **Waveform View**: 时间维度波形展示

### 高级功能
- **三问解释器**: 每一步操作都回答"施加了什么电压？电流从哪里流？器件内部为什么变化？"
- **故障诊断系统**: 实时检测偏置错误、电流限制、感测失败等问题
- **学习系统**: 预测-操作-解释-自检的主动学习循环
- **模型切换**: 支持 F0（教学模型）和 F1（参数化紧凑模型）
- **时间轴控制**: 逐帧步进、回放、重置

## 技术栈

### 后端
- Python 3.14+
- FastAPI
- Pydantic
- pytest

### 前端
- 纯 HTML/CSS/JavaScript（零依赖）
- SVG 可视化
- Canvas 波形绘制

## 快速开始

### 1. 安装依赖

```bash
# Python 依赖
pip install fastapi uvicorn pydantic pytest

# Node.js 依赖（可选，用于前端开发）
cd apps/web && npm install
```

### 2. 启动 API 服务

```bash
export PYTHONPATH="$PWD/packages:$PWD/apps/api:$PWD"
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

### 3. 打开前端页面

```bash
open apps/web/public/rram-simulator.html
```

## 项目结构

```
rram-visual-simulator/
├── apps/
│   ├── api/              # FastAPI 后端
│   └── web/              # 前端页面
├── packages/
│   └── contracts/        # 数据类型定义
├── simulator/            # 仿真核心
│   ├── core/             # 核心模型
│   ├── models/           # 模型适配器
│   ├── array/            # 阵列模型
│   ├── fault_injection.py
│   ├── disturb_model.py
│   ├── debug_console.py
│   ├── learning_engine.py
│   └── learning_manager.py
├── tests/                # 测试用例
└── docs/                 # 文档
```

## 版本历史

- **V1.0**: 统一前端集成，所有功能可视化
- **V0.9**: 学习系统（预测-操作-解释-自检）
- **V0.8**: 参数校准和配置版本管理
- **V0.7**: 多模型支持和 SPICE 桥接
- **V0.6**: 故障注入和诊断系统
- **V0.5**: 导电细丝可视化和全局时间轴
- **V0.4**: 参数化紧凑模型（F1）
- **V0.3**: 外围电路模型
- **V0.2**: 4×4 阵列支持
- **V0.1**: 单单元仿真核心

## 测试

```bash
# 运行所有测试
PYTHONPATH="$PWD/packages:$PWD/apps/api:$PWD" pytest tests/

# 运行前端测试
cd apps/web && npm test
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请通过 GitHub Issues 联系。
