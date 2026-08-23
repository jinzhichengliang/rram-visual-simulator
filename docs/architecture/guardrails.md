# Architecture Guardrails

> Established in S00. Must read this file before adding any new features.

## First Principle: Single Source of Truth

Six views (Device, 1T1R Cell, Array, Circuit, Waveform, Filament) + Explanation + Waveform cursor all consume the same immutable FrameState. No view, selector, or animation component may independently decide SET/RESET, R, gap, or sense decision.

## Causality Order (Fixed)

```
Operation Intent → Decoder/Driver → WL/BL/SL Bias → Access Transistor
→ V_RRAM → I_RRAM / Compliance → Device Internal State → R_RRAM
→ Sense Result → Logic State / Verify Decision
```

No code may skip or reverse this order.

## Architecture Red Lines

1. **Views Don't Write State** — View/selector/animation must not create or modify rram.state, R, gap, formingDone, or sense decision.
2. **V_RRAM Comes from Core** — Must not use BL−SL as a temporary substitute for actual device terminal voltage in UI.
3. **Polarity Configurable** — SET/RESET polarity and logic map come from DeviceProfile, must not hardcode "BL positive = SET".
4. **Filament Doesn't Create Physics** — Animation only consumes model observables, must not become a second physics model.
5. **Array Doesn't Copy Model** — Each array cell instantiates a unified ModelAdapter, does not reimplement cell logic within Array.
6. **Randomness Off by Default** — All random sources use seeded RNG, FrameState records seed.
7. **Profile Versioned** — Parameter changes must be versioned, golden scenarios explicitly pin profile version.

## Physical Fidelity Layers

| Level | Meaning | Display Method |
|-------|---------|----------------|
| F0 | Teaching model | Clearly labeled "Conceptual" |
| F1 | Parameterized compact | Show state variables and model version |
| F2 | SPICE/Verilog-A | Displayed via adapter, data source labeled |
| F3 | TCAD/experimental calibration | Used for comparison, not confused with real-time simulation |

## When S00 Is Not Complete

- Any RRAM state transition code exists
- Fake waveform/animation data exists
- Business physics logic exists in View
- No health endpoint or CI is not green
