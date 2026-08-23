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

### Test Results
- Python: 137 tests passed (32 new)
- Frontend: 73 tests passed

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

### Test Results
- Python: 105 tests passed (36 new)
- Frontend: 73 tests passed

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
  - 6 new tests
- **Program-and-Verify Controller** (S12)
  - ProgramAndVerifyController — iterative programming with verification
  - ProgrammingSessionManager — tracks programming sessions
  - VerifyStatus: PASS / FAIL / INCOMPLETE
  - 14 new tests

### Test Results
- Python: 69 tests passed (34 new)
- Frontend: 73 tests passed

## [0.2.0-v0.2] — 2026-08-23

### Added
- **Array Domain Model** (S07)
  - ArrayState: manages per-cell device state independently
  - ArrayDecoder: decodes target (row, col) into node voltage arrays
  - ArrayOrchestrator: orchestrates operations on array using shared model
  - Single TeachingModelAdapter shared by all cells
  - 10 new tests
- **Array View** (S08)
  - 4×4 cell grid with state colors
  - Selected cell highlight with WL/BL/SL lines
  - Current path animation
  - 12 new tests
- **Array Validation** (S09)
  - INV-010: Array Conservation (port current = sum of branch currents)
  - G-05: Array Selection (only selected cell changes)
  - Unselected cell protection
  - 10 new tests

### Test Results
- Python: 35 tests passed (30 new)
- Frontend: 73 tests passed

## [0.1.0-v0.1] — 2026-08-23

### Added
- **Teaching Model Adapter (F0)** (S02)
  - Deterministic, interpretable RRAM model
  - Transistor state computation (NMOS gating)
  - V_RRAM / I_RRAM computation
  - State transitions (PRISTINE → FORMING → HRS/LRS)
  - 17 new tests
- **Physics Invariants** (S03)
  - INV-001 ~ INV-009: Automated checks for every FrameState
  - Golden Scenarios G-01 ~ G-04
  - Check Engine integrated into orchestrator
  - 14 new tests

### Test Results
- Python: 5 tests passed (5 new)
- Frontend: 73 tests passed

## [0.0.0-s00] — 2026-08-23

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
