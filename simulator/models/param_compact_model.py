"""
ParamCompactAdapter (F1) — Parameterized compact model with continuous state.

V0.4 S14: Introduces gap_nm as continuous state variable.
- State transitions driven by gap evolution
- gap shrinks during SET → LRS
- gap grows during RESET → HRS
- R = f(gap) monotonic mapping

V0.4 S16: Adds optional stochastic hooks.
- Random variation in gap evolution (disabled by default)
- Seeded RNG for reproducibility
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from packages.contracts.types import (
    CellState,
    DeviceProfile,
    DeviceState,
    FidelityLevel,
    FrameState,
    ModelMetadata,
    NodeVoltages,
    OperationPhase,
    OperationType,
    RRAMState,
    TransistorState,
)


@dataclass
class F1ModelState:
    """F1 model internal state."""
    gap_nm: float  # Gap size in nanometers
    filament_proxy: float  # Filament connectivity 0-1
    temperature_k: float  # Local temperature in Kelvin


class ParamCompactAdapter:
    """
    F1 Parameterized Compact Model Adapter.

    Uses continuous gap_nm state variable instead of discrete states.
    R = R_0 * exp(gap / gap_0) monotonic mapping.

    V0.4 S16: Optional stochastic variation (disabled by default).
    """

    def __init__(
        self,
        profile: DeviceProfile,
        seed: int = 42,
        enable_stochastic: bool = False,
    ):
        self.profile = profile
        self.seed = seed
        self.fidelity = FidelityLevel.F1

        # Stochastic hooks (S16)
        self.enable_stochastic = enable_stochastic
        self.rng = random.Random(seed)
        self.stochastic_strength = 0.05  # 5% variation

        # Model parameters (calibrated in S17)
        # Gap parameters
        self.gap_min_nm = 0.1  # Minimum gap (LRS)
        self.gap_max_nm = 10.0  # Maximum gap (HRS)
        self.gap_initial_nm = 5.0  # Initial gap (PRISTINE)

        # Resistance mapping: R = R_0 * exp(gap / gap_0)
        self.r_0_ohm = 1000.0  # Base resistance
        self.gap_0_nm = 1.0  # Gap scaling factor

        # SET/RESET kinetics
        self.v_set_threshold_v = 1.5  # SET threshold voltage
        self.v_reset_threshold_v = -1.5  # RESET threshold voltage
        self.gap_set_rate_nm_per_vs = 0.5  # Gap shrink rate during SET
        self.gap_reset_rate_nm_per_vs = 0.3  # Gap grow rate during RESET

        # Temperature
        self.t_ambient_k = 300.0  # Ambient temperature
        self.thermal_resistance_k_per_w = 1000.0  # Thermal resistance

        # Initial state
        self.state = F1ModelState(
            gap_nm=self.gap_initial_nm,
            filament_proxy=self._gap_to_filament(self.gap_initial_nm),
            temperature_k=self.t_ambient_k,
        )

    def _gap_to_resistance(self, gap_nm: float) -> float:
        """Map gap to resistance: R = R_0 * exp(gap / gap_0)."""
        return self.r_0_ohm * (2.718281828 ** (gap_nm / self.gap_0_nm))

    def _gap_to_filament(self, gap_nm: float) -> float:
        """Map gap to filament connectivity proxy [0, 1]."""
        # filament = 1 when gap is small (LRS), 0 when gap is large (HRS)
        normalized = (gap_nm - self.gap_min_nm) / (self.gap_max_nm - self.gap_min_nm)
        return max(0.0, min(1.0, 1.0 - normalized))

    def _resistance_to_state(self, r_ohm: float) -> DeviceState:
        """Map resistance to discrete state label."""
        r_lrs_mid = (self.profile.ranges.rLrs[0] + self.profile.ranges.rLrs[1]) / 2
        r_hrs_mid = (self.profile.ranges.rHrs[0] + self.profile.ranges.rHrs[1]) / 2

        if r_ohm < r_lrs_mid * 0.5:
            return DeviceState.LRS
        elif r_ohm > r_hrs_mid * 0.5:
            return DeviceState.HRS
        else:
            return DeviceState.HRS  # Default to HRS if in between

    def compute_transistor_state(
        self,
        wl_voltage: float,
        bl_voltage: float,
        sl_voltage: float,
    ) -> TransistorState:
        """Compute access transistor state (same as F0)."""
        VTH = 0.7
        vgs = wl_voltage - sl_voltage
        is_on = vgs > VTH

        if is_on:
            vs = sl_voltage
            vd = bl_voltage
        else:
            vs = sl_voltage
            vd = sl_voltage

        return TransistorState(
            vg=wl_voltage,
            vs=vs,
            vd=vd,
            on=is_on,
            complianceLimitUa=self.profile.complianceUa,
        )

    def compute_v_rram(
        self,
        bl_voltage: float,
        transistor_state: TransistorState,
        sl_voltage: float,
    ) -> float:
        """Compute V_RRAM (same as F0)."""
        if not transistor_state.on:
            return 0.0

        if self.profile.vRramSignConvention == "V(top)-V(bottom)":
            return bl_voltage - sl_voltage
        else:
            return sl_voltage - bl_voltage

    def compute_i_rram(
        self,
        v_rram: float,
        r_rram: float,
        transistor_on: bool,
    ) -> float:
        """Compute I_RRAM (same as F0)."""
        if not transistor_on:
            return 0.0

        if r_rram <= 0:
            raise ValueError("RRAM resistance must be positive")

        i_amps = v_rram / r_rram
        return i_amps * 1e6  # Convert to µA

    def apply_compliance(self, i_rram: float) -> tuple[float, bool]:
        """Apply compliance current limiting (same as F0)."""
        compliance = self.profile.complianceUa
        if abs(i_rram) > compliance:
            limited = compliance if i_rram > 0 else -compliance
            return limited, True
        return i_rram, False

    def update_gap(
        self,
        v_rram: float,
        i_rram: float,
        dt_ns: float,
        operation: OperationType,
    ) -> None:
        """
        Update gap based on voltage/current and operation.

        F1 model: gap evolves continuously based on applied bias.
        """
        dt_s = dt_ns * 1e-9  # Convert to seconds

        # Only update during ACTIVE/HOLD phases
        if operation not in [OperationType.FORMING, OperationType.SET, OperationType.RESET]:
            return

        # Calculate effective voltage across gap
        v_eff = abs(v_rram)

        # SET: gap shrinks when V_RRAM > V_SET_threshold
        if operation in [OperationType.FORMING, OperationType.SET]:
            if v_rram > self.v_set_threshold_v:
                # Gap shrinks proportional to (V - V_th) * dt
                delta_gap = self.gap_set_rate_nm_per_vs * (v_rram - self.v_set_threshold_v) * dt_s

                # S16: Add stochastic variation if enabled
                if self.enable_stochastic:
                    variation = self.rng.gauss(0, self.stochastic_strength)
                    delta_gap *= (1.0 + variation)

                self.state.gap_nm = max(self.gap_min_nm, self.state.gap_nm - delta_gap)

        # RESET: gap grows when V_RRAM < V_RESET_threshold (negative)
        elif operation == OperationType.RESET:
            if v_rram < self.v_reset_threshold_v:
                # Gap grows proportional to (|V| - |V_th|) * dt
                delta_gap = self.gap_reset_rate_nm_per_vs * (abs(v_rram) - abs(self.v_reset_threshold_v)) * dt_s

                # S16: Add stochastic variation if enabled
                if self.enable_stochastic:
                    variation = self.rng.gauss(0, self.stochastic_strength)
                    delta_gap *= (1.0 + variation)

                self.state.gap_nm = min(self.gap_max_nm, self.state.gap_nm + delta_gap)

        # Update filament proxy
        self.state.filament_proxy = self._gap_to_filament(self.state.gap_nm)

        # Update temperature (simplified)
        power_w = abs(v_rram * i_rram) * 1e-6  # µW → W
        self.state.temperature_k = self.t_ambient_k + power_w * self.thermal_resistance_k_per_w

    def compute_frame(
        self,
        frame_id: str,
        time_ns: float,
        operation: OperationType,
        phase: OperationPhase,
        nodes: NodeVoltages,
        selected_cell: Optional[dict[str, int]],
        current_state: DeviceState,
        forming_done: bool,
    ) -> FrameState:
        """
        Compute complete FrameState for given conditions.

        F1 uses continuous gap state instead of discrete states.
        """
        if selected_cell is None:
            raise ValueError("selected_cell is required for single-cell model")

        row = selected_cell["row"]
        col = selected_cell["col"]

        # Get node voltages
        wl_voltage = nodes.wl[row] if row < len(nodes.wl) else 0.0
        bl_voltage = nodes.bl[col] if col < len(nodes.bl) else 0.0
        sl_voltage = nodes.sl[col] if col < len(nodes.sl) else 0.0

        # Step 1: Compute transistor state
        transistor = self.compute_transistor_state(wl_voltage, bl_voltage, sl_voltage)

        # Step 2: Compute V_RRAM
        v_rram = self.compute_v_rram(bl_voltage, transistor, sl_voltage)

        # Step 3: Get current resistance from gap
        r_rram = self._gap_to_resistance(self.state.gap_nm)

        # Step 4: Compute I_RRAM
        i_rram = self.compute_i_rram(v_rram, r_rram, transistor.on)

        # Step 5: Apply compliance
        i_rram_limited, _ = self.apply_compliance(i_rram)

        # Step 6: Update gap during ACTIVE/HOLD phases
        if phase in [OperationPhase.ACTIVE, OperationPhase.HOLD]:
            self.update_gap(v_rram, i_rram_limited, dt_ns=10.0, operation=operation)
            # Recompute resistance after gap update
            r_rram = self._gap_to_resistance(self.state.gap_nm)
            i_rram_limited = self.compute_i_rram(v_rram, r_rram, transistor.on)
            i_rram_limited, _ = self.apply_compliance(i_rram_limited)

        # Step 7: Determine discrete state label from resistance
        new_state = self._resistance_to_state(r_rram)
        new_forming_done = forming_done or (operation == OperationType.FORMING and phase == OperationPhase.ACTIVE)

        # Step 8: Build RRAM state with F1 observables
        rram_state = RRAMState(
            v=v_rram,
            i=i_rram_limited,
            r=r_rram,
            state=new_state,
            formingDone=new_forming_done,
            gapNm=self.state.gap_nm,
            filamentProxy=self.state.filament_proxy,
            temperatureK=self.state.temperature_k,
        )

        # Step 9: Compute sense (only in SENSE phase)
        sense = None
        if phase == OperationPhase.SENSE:
            sense = self._compute_sense(i_rram_limited, new_state)

        # Step 10: Build cell state
        cell = CellState(transistor=transistor, rram=rram_state)

        # Step 11: Build model metadata
        model = ModelMetadata(
            fidelity=self.fidelity,
            profileId=self.profile.id,
            profileVersion=self.profile.version,
            seed=self.seed,
        )

        # Step 12: Build frame
        frame = FrameState(
            frameId=frame_id,
            timeNs=time_ns,
            operation=operation,
            phase=phase,
            selectedCell=selected_cell,
            nodes=nodes,
            cell=cell,
            sense=sense,
            model=model,
            checks=[],
        )

        return frame

    def _compute_sense(self, i_rram: float, state: DeviceState):
        """Compute sense amplifier decision (same as F0)."""
        from simulator.models.teaching_model import TeachingModelAdapter
        # Reuse F0 sense logic
        f0 = TeachingModelAdapter(self.profile, self.seed)
        return f0.compute_sense(i_rram, state)

    def reset(self):
        """Reset to initial state."""
        self.state = F1ModelState(
            gap_nm=self.gap_initial_nm,
            filament_proxy=self._gap_to_filament(self.gap_initial_nm),
            temperature_k=self.t_ambient_k,
        )
