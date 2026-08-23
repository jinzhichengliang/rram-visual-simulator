# ADR-0001: Single Source of Truth — FrameState

## Status
Accepted (S00)

## Context
RRAM Visual Simulator needs six views (Device, 1T1R Cell, Array, Circuit, Waveform, Filament) + Explanation Engine to work together. If each view maintains its own state, it will lead to inconsistent values, broken causality chains, and misleading teaching content.

## Decision
Adopt a single immutable FrameState as the only source of truth for all views and explanation modules.

- Generate an immutable FrameState object at each simulation time point
- All views read from FrameState through pure selector functions, never write to it
- All state transitions are determined by Simulation Core, frontend does not decide SET/RESET
- Waveform data is generated from FrameState history sequence, not a separate waveform
- Explanation is generated from OperationSpec + FrameState + DeviceProfile + CheckResult

## Consequences

### Positive
- Six views are naturally consistent, no manual synchronization needed
- Can replay any historical frame (scrub)
- Cross-view tests can be automated
- Model replacement (Teaching → Compact → SPICE) does not change UI

### Negative
- Every state change requires generating a complete FrameState (performance concern)
- Need to strictly define schema and synchronize between Python/TS

## References
- docs/architecture/guardrails.md
- Development Design Document V1.1, Chapter 3
