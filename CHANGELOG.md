# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0-v1.0] — 2026-08-23

### Added
- **Unified Frontend Integration** (S31)
  - Circuit View: Display peripheral circuit info (WL/BL/SL drivers, sense amplifier)
  - Diagnostics Panel: Real-time fault detection and health monitoring
  - Learning System Panel: Progress tracking, achievement badges, scenario loading
  - Model Switching: F0/F1 model toggle in UI
  - All V0.3-V0.9 backend features now visible in frontend

### Changed
- API version: 0.9.0 → 1.0.0
- Frontend version: V0.2 → V1.0 Unified
- Integrated all subsystems into single cohesive interface

### Test Results
- Python: 289 tests passed
- Frontend: 73 tests passed
- All API endpoints operational

## [0.9.0-v0.9] — 2026-08-23

### Added
- **Learning Engine** (S29)
  - Prediction-Operation-Explanation-Self-check learning loop
  - Error attribution system (polarity, threshold, transistor, current path)
  - Learning scenarios with hints and difficulty levels
  - Progress tracking and weak area identification
  - 16 new tests
- **Learning Manager** (S30)
  - User progress tracking with accuracy history
  - Note-taking system for scenarios
  - Scenario save/load functionality
  - Achievement badges system
  - File-based persistence
  - 16 new tests

### Test Results
- Python: 289 tests passed (32 new)
- Frontend: 73 tests passed

## [0.8.0-v0.8] — 2026-08-23

### Added
- **Calibration Workspace** (S27)
  - Parameter calibration with grid search optimization
  - Reference data import and error calculation
  - Calibration report generation
  - 14 new tests
- **Profile Versioning & Promotion Workflow** (S28)
  - Draft/Candidate/Published/Deprecated status management
  - Version tracking with parent-child relationships
  - Rollback support
  - Change history tracking
  - 18 new tests

### Test Results
- Python: 257 tests passed (32 new)
- Frontend: 73 tests passed

## [0.7.0-v0.7] — 2026-08-23

### Added
- **Model Adapter Protocol** (S24)
  - Unified ModelAdapter interface for all model backends
  - TraceReplayAdapter for experimental data playback
  - TracePoint and TraceData structures
  - 12 new tests
- **SPICE/Compact Model Bridge** (S25)
  - SPICEParser for CSV format parsing
  - SPICEModelAdapter for SPICE simulation results
  - VerilogAModelAdapter for Verilog-A model results
  - Column mapping configuration
  - 14 new tests
- **Multi-Model Regression System** (S26)
  - MultiModelRunner for parallel model execution
  - ModelComparison for difference analysis
  - RegressionTest and RegressionTestSuite for automated testing
  - Configurable tolerances for V/I/R/state matching
  - 12 new tests

### Test Results
- Python: 225 tests passed (38 new)
- Frontend: 73 tests passed

## [0.6.0-v0.6] — 2026-08-23

### Added
- **Fault Injection Framework** (S21)
  - Detect wrong bias polarity
  - Detect WL not enabled
  - Detect missing compliance
  - Detect sense failure
  - Detect over-forming
  - 22 new tests
- **Read/Write Disturb Model** (S22)
  - Read disturb simulation with voltage, count, and temperature effects
  - Write disturb simulation with coupling and distance effects
  - Read endurance estimation
  - Safe write distance estimation
  - 15 new tests
- **Debug Console & Diagnostic System** (S23)
  - Diagnostic context and report generation
  - Fault detection and attribution
  - Disturb assessment
  - Recommendation generation
  - Diagnostic history tracking
  - 13 new tests

### Test Results
- Python: 187 tests passed (50 new)
- Frontend: 73 tests passed

## [0.5.0-v0.5] — 2026-08-23

### Added
- **Filament View** (S18)
  - Visualizes conductive filament based on gap_nm and filament_proxy
  - F0 mode: Conceptual visualization (connected/disconnected)
  - F1 mode: Parameterized visualization (gap size, filament width, temperature)
  - Color gradient: green (LRS) → yellow (intermediate) → red (HRS)
  - Gap visualization for F1 mode
  - 10 new tests
- **Global Scrub** (S19)
  - Timeline scrubber for frame-by-frame navigation
  - Step forward/backward buttons
  - Reset timeline button
  - All views sync to same frame
- **Cross-view Hardening** (S20)
  - All 6 views read from same FrameState
  - Consistent state across Device, Cell, Array, Filament, Waveform, Explanation

### Changed
- Grid layout updated to 4 columns (Device, Cell, Array, Filament)
- Waveform and Explanation span 2 columns
- Filament View integrated into HTML simulator

### Test Results
- Python: 137 tests passed
- Frontend: 73 tests passed (10 new)

## [0.4.0-v0.4] — 2026-08-23

### Added
- **ParamCompactAdapter (F1)** (S14)
  - Continuous gap_nm state variable instead of discrete states
  - R = R_0 * exp(gap / gap_0) monotonic resistance mapping
  - Filament proxy derived from gap
  - Temperature tracking
  - 13 new tests
- **Pulse Dynamics** (S15)
  - Gap evolution proportional to (V - V_th) * dt
  - Gradual SET/RESET with multiple pulses
  - Pulse amplitude and width affect gap change
  - 7 new tests
- **Stochastic Hooks** (S16)
  - Optional random variation in gap evolution (disabled by default)
  - Seeded RNG for reproducibility
  - Temperature effect tracking
  - 8 new tests
- **F1 Calibration Gate** (S17)
  - Calibrate R_LRS/R_HRS by adjusting gap_min/gap_max
  - Calibrate V_SET/V_RESET thresholds
  - Generate calibration report
  - 8 new tests

### Changed
- F1 model uses continuous gap state instead of discrete states
- Frame output includes gap_nm, filament_proxy, temperatureK observables
- Model fidelity reports "F1" instead of "F0"

### Test Results
- Python: 137 tests passed (36 new)
- Frontend: 63 tests passed

## [0.3.0-v0.3] — 2026-08-23

### Added
- **Peripheral Circuit Models** (S10)
  - RowDecoder / ColumnDecoder — address decoding
  - WLDriver / BLDriver / SLDriver — voltage drivers with compliance
  - PeripheralCircuit — orchestrates decoder + drivers + sense
  - 14 new tests
- **Sense Amplifier** (S11)
  - SenseAmplifier — compares read current with reference
  - Reference current calculation from HRS/LRS midpoints
  - Margin calculation and verification
  - G-06: Sense Margin tests (6 tests)
- **Program-and-Verify Controller** (S12)
  - ProgramAndVerifyController — iterative programming with verification
  - ProgrammingSessionManager — tracks programming sessions
  - VerifyStatus: PASS / FAIL / INCOMPLETE
  - G-07: Program Verify Retry tests (14 tests)
- **API Integration** (S13)
  - Peripheral circuit info in frame responses
  - Driver states (WL/BL/SL voltages, selected lines, active status)
  - Sense amplifier info (reference, margin, decision)
  - Program-and-verify metadata in state endpoint

### Changed
- API version: 0.6.0-s06 → 0.3.0-v0.3
- Frame responses now include `peripheral` field with driver/sense info
- State endpoint includes peripheral metadata

### Test Results
- Python: 101 tests passed (34 new)
- Frontend: 63 tests passed

## [0.2.1-bugfix] — 2026-08-23

### Fixed
- **Explanation Engine 严重 bug** — 解释器现在基于实际状态差异而非操作类型猜测
  - **根因**：旧版用 `operation + phase` 猜测状态变化（如 `phase === "ACTIVE"` 就认为状态变了），完全不看前后帧的实际状态
  - **修复**：selector 新增 `prevFrame` 参数，通过 `prevState !== currentState` 检测真实状态转移
  - **影响**：Physics Card 现在只在状态真正改变时才显示 "PRISTINE → LRS" 等转换信息
  - **新增测试**：验证状态相同时不显示转换信息

### Changed
- `selectExplanation(frame)` → `selectExplanation(frame, prevFrame)` — 签名变更
- App.tsx 传递 `prevFrame` 给解释器

## [0.2.0-v0.2] — 2026-08-23

### Added
- **Array Domain Model** — 4×4 1T1R Array with decoder and bias policy
  - ArrayState: manages per-cell device state independently
  - ArrayDecoder: decodes target (row, col) into node voltage arrays
  - ArrayOrchestrator: orchestrates operations on array using shared model
  - Single TeachingModelAdapter shared by all cells (no duplicate models)
- **Array View Selector** — Extract array presentation data from FrameState
  - 4×4 grid with selected cell highlighting
  - WL/BL/SL voltage display
  - Current flow animation (only for selected cell)
- **Array View Component** — SVG visualization of 4×4 array
  - Cell grid with state colors (LRS/HRS/PRISTINE)
  - Selected cell highlight with WL/BL/SL lines
  - Current path animation
  - Click to select cell
- **INV-010: Array Conservation** — Port current = sum of branch currents
- **G-05: Array Selection** — Only selected cell changes state
- **Array Validation Tests** — 10 new tests
  - INV-010 port current verification
  - G-05 selection correctness
  - Unselected cell protection
  - Array reset functionality
- **Array Selector Tests** — 12 new tests
  - Grid extraction
  - Selected cell highlighting
  - Voltage display
  - Current flow conditions

### Changed
- App layout: 3-column grid (Device, Cell, Array)
- executeOperation uses selectedCell state
- Cell click handler updates selectedCell

### Constraints
- Every cell uses the SAME TeachingModelAdapter
- Array only handles topology, selection, bias distribution
- Unselected cells remain unchanged during operations

## [0.6.0-s06] — 2026-08-23

### Added
- **Simulation API** — FastAPI endpoints for frontend-backend communication
  - POST /api/operation — Execute simulation operation (FORMING/READ/SET/RESET)
  - POST /api/reset — Reset simulation to initial state
  - GET /api/frames — Get all frames from history
  - GET /api/state — Get current device state
- **Global Store** — React hook for managing simulation state
  - Frame history management
  - Current frame cursor
  - Running/paused state
- **Control Panel Component** — Global simulation controls
  - Operation buttons (Forming, Read, Set, Reset)
  - Playback controls (Step, Play/Pause, Reset All)
- **Integrated App Component** — V0.1 Release Gate application
  - Integrates all views (Device, Cell, Waveform, Explanation)
  - Timeline scrubber for frame navigation
  - Real-time state updates
  - Full Golden Tutorial support

### Changed
- Updated API from S00 bootstrap to S06 full simulation
- App component now integrates all selectors and views

### Constraints
- All views read from same FrameState (single source of truth)
- No physics calculations in frontend
- All explanations state-driven

## [0.5.0-s05] — 2026-08-23

### Added
- **Waveform View Selector** — Pure function to extract time-series waveform data from FrameState history
  - Extracts V_RRAM, I_RRAM, R_RRAM over time
  - Tracks current frame cursor position
  - No physics calculations, only data extraction
- **Explanation Engine Selector** — State-driven explanation generator
  - Generates four explanation cards:
    1. Voltage Card — What voltage is applied?
    2. Current Card — Where does current flow?
    3. Physics Card — Why does the device change (or not)?
    4. Sense Card — How do we know the operation succeeded?
  - All explanations derived from FrameState, not hardcoded
- **Waveform View Component** — SVG visualization of time-domain waveforms
  - Displays V_RRAM, I_RRAM, R_RRAM waveforms
  - Current frame marker with cursor sync
  - Phase labels and time axis
  - Legend with color coding
- **Explanation View Component** — React component for explanation cards
  - Four-card grid layout
  - State-driven content from selector
- **Waveform + Explanation Tests** — 22 new tests
  - Waveform selector time-series extraction
  - Explanation selector state-driven generation
  - Cursor sync verification
  - Explanation token assertions
  - G-04 polarity reversal text tests

### Constraints
- Waveform data comes from FrameState history, not recalculated
- Explanations generated from state, not hardcoded strings
- Cursor sync ensures all views show same frame
- Polarity reversal changes explanation text automatically

## [0.4.0-s04] — 2026-08-23

### Added
- **Device View Selector** — Pure function to extract Device View presentation data from FrameState
  - Extracts V_RRAM, I_RRAM, resistance, state, polarity, current flow, compliance
  - No physics calculations, only data extraction
- **1T1R Cell View Selector** — Pure function to extract Cell View presentation data from FrameState
  - Extracts node voltages (WL/BL/SL), transistor state, current path direction
  - No physics calculations, only data extraction
- **Device View Component** — SVG visualization of RRAM device
  - Displays electrodes, switching layer, filament (conceptual)
  - Shows V_RRAM polarity, I_RRAM magnitude/direction, R value
  - Current flow animation with direction indication
  - Compliance indicator
- **1T1R Cell View Component** — SVG visualization of 1T1R cell structure
  - Displays BL/WL/SL lines with voltages
  - Shows RRAM element and NMOS transistor
  - Current path animation (BL→SL or SL→BL)
  - Transistor ON/OFF state indicator
- **Cross-View Consistency Tests** — 6 tests verifying Device and Cell selectors return same values
  - V_RRAM, I_RRAM, state, resistance, current flow, compliance
- **Selector Unit Tests** — 20 tests covering all selector functionality
  - PRISTINE/LRS/HRS state extraction
  - Current direction detection
  - Compliance detection
  - Error handling

### Constraints
- Views do NOT modify state
- Views do NOT perform physics calculations
- All data comes from FrameState via selectors
- No BL-SL voltage difference calculated in frontend

## [0.3.0-s03] — 2026-08-20

### Added
- **Physics Invariants (INV-001 ~ INV-009)** — Automated checks for every FrameState:
  - INV-001: V_RRAM node consistency
  - INV-002: Transistor gating (current ≈ 0 when OFF)
  - INV-003: Current direction matches voltage polarity
  - INV-004: Compliance limiting during FORMING/SET
  - INV-005: READ non-destructive (state/R unchanged)
  - INV-006: State windows (LRS/HRS within configured ranges)
  - INV-007: Forming prerequisite (SET/RESET require forming)
  - INV-008: No spontaneous switching (state changes only in ACTIVE/HOLD)
  - INV-009: Sense consistency (decision matches I_read vs reference)
- **Golden Scenarios (G-01 ~ G-04)** — Canonical test cases:
  - G-01: Basic 1T1R cycle (Pristine → Forming → HRS → Read0 → Set → Read1 → Reset → Read0)
  - G-02: Read non-destructive (multiple reads don't change state)
  - G-03: Compliance protection (current limited even with high drive)
  - G-04: Polarity reversal (reversed profile works correctly)
- **Check Engine** — Integrated into orchestrator, runs all invariants on each frame
- **FrameState checks** — Every frame now carries invariant check results
- **Unit tests**: 14 new tests for validation system

### Changed
- Teaching model now only performs state transitions during ACTIVE/HOLD phases
- Orchestrator integrated with CheckEngine for automatic validation

### Constraints
- No UI changes
- No array support yet
- All invariants must pass for golden scenarios

## [0.2.0-s02] — 2026-08-20

### Added
- **Teaching Model Adapter (F0)** — Deterministic, interpretable RRAM model:
  - Transistor state computation (NMOS gating)
  - V_RRAM computation from node voltages
  - I_RRAM computation (Ohm's law)
  - Compliance current limiting
  - State transitions (PRISTINE → FORMING → HRS/LRS)
  - Sense amplifier logic
- **Simulation Orchestrator** — Operation state machine:
  - Phase sequence management (PREPARE → BIAS_RAMP → ACTIVE → ... → COMPLETE)
  - Frame generation at each phase
  - Event emission (OPERATION_STARTED, BIAS_APPLIED, etc.)
  - State persistence across operations
  - Reset functionality
- **Causal chain enforcement**: Bias → Transistor → V_RRAM → I_RRAM → State → R → Sense
- **Polarity parametrization**: SET/RESET polarity from DeviceProfile
- **Determinism**: Same seed produces identical results
- **Unit tests**: 25 new tests covering model and orchestrator

### Constraints
- No UI implementation
- No array support (single cell only)
- No gradual transitions (discrete states)
- No random variation (F0 teaching model)

## [0.1.0-s01] — 2026-08-20

### Added
- **Canonical data contracts** (JSON Schema + Pydantic + TypeScript):
  - `FrameState` — immutable simulator state snapshot
  - `OperationSpec` — operation specification
  - `DeviceProfile` — device configuration with versioning
  - `CheckResult` — physics invariant check result
  - `SimulatorEvent` — semantic event
- **Schema fixtures**: valid/invalid test cases for cross-language validation
- **Schema tests**: Python (18 tests) + TypeScript (8 tests)
- **Unit naming convention**: fields include units (timeNs, currentUa, voltageV)
- **Profile versioning**: DeviceProfile requires id + version for golden regression

### Constraints
- No state transition logic implemented
- No UI physics logic
- All contracts are backward-compatible by design

## [0.0.0-s00] — 2026-08-20

### Added
- Project bootstrap: directory structure, CI, ADR, Decision Log
- FastAPI health endpoint (`GET /health`)
- React + TypeScript + Vite minimal shell
- Architecture guardrails document
- ADR-0001: Single Source of Truth
- Open-Source Reference Registry
- Unified Makefile commands
- Test scaffolding (unit, invariant, golden, cross-view, e2e)

### Constraints
- No RRAM physics implemented
- No views or animations
- No state transition logic
