# RRAM Visual Simulator

An interactive, teaching-first visualization and simulation platform for RRAM (Resistive Random Access Memory) and 1T1R (One Transistor, One Resistor) memory technology.

## 🌐 Online Demo

**Try it now**: https://jinzhichengliang.github.io/rram-visual-simulator/

No installation required - runs entirely in your browser!

## Features

### Core Views
- **Device View**: Visualize voltage, current, and state across the RRAM device
- **1T1R Cell View**: Understand how BL/WL/SL control a single memory cell
- **Array View**: 4×4 array visualization with cell selection mechanism
- **Filament View**: Conductive filament visualization (supports F0/F1 models)
- **Circuit View**: Peripheral circuits (Decoder/Driver/Sense Amplifier)
- **Waveform View**: Time-domain waveform display

### Advanced Features
- **Three-Question Explainer**: Every operation answers "What voltage is applied? Where does current flow? Why does the device change internally?"
- **Fault Diagnosis System**: Real-time detection of bias errors, current limiting, sense failures
- **Learning System**: Active learning loop with predict-operate-explain-self-check cycle
- **Model Switching**: Support for F0 (teaching model) and F1 (parameterized compact model)
- **Timeline Control**: Frame-by-frame stepping, playback, and reset

## Tech Stack

### Backend
- Python 3.14+
- FastAPI
- Pydantic
- pytest

### Frontend
- Pure HTML/CSS/JavaScript (zero dependencies)
- SVG visualization
- Canvas waveform rendering

## Quick Start

### 1. Install Dependencies

```bash
# Python dependencies
pip install fastapi uvicorn pydantic pytest

# Node.js dependencies (optional, for frontend development)
cd apps/web && npm install
```

### 2. Start API Server

```bash
export PYTHONPATH="$PWD/packages:$PWD/apps/api:$PWD"
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

### 3. Open Frontend

```bash
open apps/web/public/rram-simulator.html
```

Or visit the online demo: https://jinzhichengliang.github.io/rram-visual-simulator/

## Project Structure

```
rram-visual-simulator/
├── apps/
│   ├── api/              # FastAPI backend
│   └── web/              # Frontend pages
├── packages/
│   └── contracts/        # Data type definitions
├── simulator/            # Simulation core
│   ├── core/             # Core models
│   ├── models/           # Model adapters
│   ├── array/            # Array model
│   ├── fault_injection.py
│   ├── disturb_model.py
│   ├── debug_console.py
│   ├── learning_engine.py
│   └── learning_manager.py
├── tests/                # Test cases
└── docs/                 # Documentation
```

## Version History

- **V1.0**: Unified frontend integration, all features visualized
- **V0.9**: Learning system (predict-operate-explain-self-check)
- **V0.8**: Parameter calibration and profile versioning
- **V0.7**: Multi-model support and SPICE bridge
- **V0.6**: Fault injection and diagnostic system
- **V0.5**: Conductive filament visualization and global timeline
- **V0.4**: Parameterized compact model (F1)
- **V0.3**: Peripheral circuit models
- **V0.2**: 4×4 array support
- **V0.1**: Single-cell simulation core

## Testing

```bash
# Run all tests
PYTHONPATH="$PWD/packages:$PWD/apps/api:$PWD" pytest tests/

# Run frontend tests
cd apps/web && npm test
```

## License

MIT License

## Contributing

Issues and Pull Requests are welcome!

## Contact

For questions, please use GitHub Issues.
