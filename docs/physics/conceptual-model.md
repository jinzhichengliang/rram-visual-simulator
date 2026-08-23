# Physics Assumptions (Conceptual Model)

> Placeholder for S00. Fill in specific assumptions when implementing Teaching Model in S02.

## Current Status

This phase (S00) does not contain any RRAM physics logic. The following is only a conceptual framework record for subsequent development.

## To Be Defined (S02+)

- State transition rules for F0 teaching model
- NMOS simplified model (ON/OFF gating)
- Threshold conditions for Forming / SET / RESET / READ
- Compliance current limiting behavior
- Sense amplifier decision logic

## Principles

1. All physics assumptions must be written into DeviceProfile, not hardcoded
2. Schematic parameters separated from process parameters, always label fidelity level
3. Each model version must record the source of state equations
