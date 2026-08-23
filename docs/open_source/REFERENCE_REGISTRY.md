# Open-Source Reference Registry

> Verification date: 2026-08-20. This table is used for engineering selection and reuse governance, does not constitute legal advice.

## Reuse Levels

- **A** = Can be selectively reused directly after meeting notice/attribution and other license requirements
- **B** = Preferably accessed through Adapter/independent dependencies
- **C** = Reference architecture, interfaces, papers/behavior or used for comparison verification, not directly copied to core code

## Project List

| Project | Most Worth Learning | Reuse Level | License/Boundaries |
|---------|---------------------|-------------|-------------------|
| MemristorLab | Interactive Web teaching/UI, current-flow, 1T1R vs sneak path | A | MIT |
| rram_multilevel_driver | 1T1R/1R programming, MLC writing, post-simulation | A/B | MIT; external models may have other restrictions |
| RRAM_COMPILER | 1T1R array, decoder, write driver, sense/peripheral | C | GPL-3.0 |
| MemTorch | Device model, crossbar, non-idealities | B/C | GPL-3.0 |
| memristor-models-4-all | Classic memristor model collection, Verilog-A/SPICE | C | Mixed sources |
| MASTODON | Multi-layer memory simulator, ModelAdapter/hierarchy decoupling | A/B | MIT |
| CrossSim | Crossbar non-idealities, parasitic wire resistance, programming error | A/B | BSD-3-Clause |
| DNN+NeuroSim | device→circuit→chip hierarchy | C | CC BY-NC 4.0 |
| vlsi_memristor_compact_model | Physical RRAM compact SPICE | B/C | GPL-3.0 |
| OpenRRAM | OpenRAM-based RRAM compiler | A/B | BSD-3-Clause |

## Usage Rules

1. Make Build-vs-Reuse Decision before coding each Sprint
2. GPL/CC BY-NC projects default to reference-only or external adapter
3. Must record commit/tag + license + attribution before third-party code enters repo
4. Reuse does not lower acceptance standards
