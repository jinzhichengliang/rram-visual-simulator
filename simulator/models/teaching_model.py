"""
Teaching Model Adapter (F0) — Deterministic, interpretable RRAM model.

This is the simplest model that demonstrates the complete causal chain:
Bias → Transistor → V_RRAM → I_RRAM → State Transition → R → Sense

F0 uses discrete states (PRISTINE/HRS/LRS) with deterministic thresholds.
No random variation, no gradual transitions — just clear teaching logic.
"""
from __future__ import annotations

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
    SenseState,
    TransistorState,
)


class TeachingModelAdapter:
    """
    F0 Teaching Model — deterministic state machine.

    Responsibilities:
    1. Compute transistor state from WL/BL/SL
    2. Compute actual V_RRAM from node voltages
    3. Compute I_RRAM from V_RRAM and current R
    4. Determine state transitions based on profile thresholds
    5. Apply compliance limiting
    6. Compute sense decision
    """

    def __init__(self, profile: DeviceProfile, seed: int = 42):
        self.profile = profile
        self.seed = seed
        self.fidelity = FidelityLevel.F0

    def compute_transistor_state(
        self,
        wl_voltage: float,
        bl_voltage: float,
        sl_voltage: float,
    ) -> TransistorState:
        """
        Compute access transistor state.

        Simplified NMOS model:
        - ON if Vg (WL) > Vth (assumed 0.7V for teaching)
        - Source = SL side (lower potential)
        - Drain = RRAM side

        For BL-RRAM-NMOS-SL topology:
        - Gate = WL
        - Drain = RRAM bottom electrode
        - Source = SL
        """
        VTH = 0.7  # Teaching threshold voltage
        vth = VTH

        # Determine if transistor is ON
        vgs = wl_voltage - sl_voltage
        is_on = vgs > vth

        # For teaching model, assume ideal switch when ON
        if is_on:
            # When ON, source follows gate minus threshold
            vs = sl_voltage
            vd = bl_voltage  # Simplified: drain at BL potential
        else:
            # When OFF, floating (no current path)
            vs = sl_voltage
            vd = sl_voltage  # No voltage drop

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
        """
        Compute actual voltage across RRAM.

        For BL-RRAM-NMOS-SL topology:
        - When transistor is ON: V_RRAM ≈ BL - SL (ideal switch)
        - When transistor is OFF: V_RRAM = 0 (no current path)

        The sign convention determines the polarity.
        """
        if not transistor_state.on:
            # No current path, no voltage across RRAM
            return 0.0

        if self.profile.vRramSignConvention == "V(top)-V(bottom)":
            # Top electrode at BL, bottom at transistor side (≈ SL when ON)
            return bl_voltage - sl_voltage
        else:
            # Reversed convention
            return sl_voltage - bl_voltage

    def compute_i_rram(
        self,
        v_rram: float,
        r_rram: float,
        transistor_on: bool,
    ) -> float:
        """
        Compute current through RRAM in microamps.

        I = V / R (Ohm's law)
        If transistor is OFF, current is 0 (teaching model ignores leakage).
        """
        if not transistor_on:
            return 0.0

        if r_rram <= 0:
            raise ValueError("RRAM resistance must be positive")

        # I = V/R, convert to microamps
        i_amps = v_rram / r_rram
        return i_amps * 1e6  # Convert to µA

    def apply_compliance(self, i_rram: float) -> tuple[float, bool]:
        """
        Apply compliance current limiting.

        Returns (limited_current, compliance_active).
        """
        compliance = self.profile.complianceUa
        if abs(i_rram) > compliance:
            # Limit current
            limited = compliance if i_rram > 0 else -compliance
            return limited, True
        return i_rram, False

    def determine_state_transition(
        self,
        current_state: DeviceState,
        v_rram: float,
        i_rram: float,
        operation: OperationType,
        forming_done: bool,
    ) -> tuple[DeviceState, bool]:
        """
        Determine if state should change based on operation and conditions.

        Returns (new_state, forming_done).
        """
        # PRISTINE can only transition via FORMING
        if current_state == DeviceState.PRISTINE:
            if operation == OperationType.FORMING:
                # Check if forming condition met
                v_form_min, v_form_max = self.profile.ranges.vForm
                if v_form_min <= abs(v_rram) <= v_form_max:
                    # Forming successful, enter LRS
                    return DeviceState.LRS, True
            # No change
            return current_state, forming_done

        # HRS/LRS transitions
        if operation == OperationType.SET:
            # SET: HRS → LRS
            if current_state == DeviceState.HRS:
                v_set_min, v_set_max = self.profile.ranges.vSet
                # Check polarity
                if self.profile.setPolarity.value == "V_RRAM > 0":
                    condition_met = v_set_min <= v_rram <= v_set_max
                else:
                    condition_met = v_set_min <= -v_rram <= v_set_max

                if condition_met:
                    return DeviceState.LRS, forming_done

        elif operation == OperationType.RESET:
            # RESET: LRS → HRS
            if current_state == DeviceState.LRS:
                v_reset_min, v_reset_max = self.profile.ranges.vReset
                # Check polarity
                if self.profile.resetPolarity.value == "V_RRAM < 0":
                    condition_met = v_reset_min <= v_rram <= v_reset_max
                else:
                    condition_met = v_reset_min <= -v_rram <= v_reset_max

                if condition_met:
                    return DeviceState.HRS, forming_done

        elif operation == OperationType.READ:
            # READ should not change state (non-destructive)
            pass

        # No change
        return current_state, forming_done

    def get_resistance_for_state(self, state: DeviceState) -> float:
        """Get representative resistance for a state (midpoint of range)."""
        if state == DeviceState.PRISTINE:
            # Pristine has very high resistance
            return 1e9  # 1 GΩ teaching value
        elif state == DeviceState.LRS:
            r_min, r_max = self.profile.ranges.rLrs
            return (r_min + r_max) / 2
        elif state == DeviceState.HRS:
            r_min, r_max = self.profile.ranges.rHrs
            return (r_min + r_max) / 2
        else:
            raise ValueError(f"Unknown state: {state}")

    def compute_sense(
        self,
        i_rram: float,
        state: DeviceState,
    ) -> SenseState:
        """
        Compute sense amplifier decision.

        Compare read current with reference (midpoint between HRS/LRS currents).
        """
        # Compute reference current (midpoint)
        r_lrs = self.get_resistance_for_state(DeviceState.LRS)
        r_hrs = self.get_resistance_for_state(DeviceState.HRS)

        # Assume Vread is midpoint of read range
        v_read_min, v_read_max = self.profile.ranges.vRead
        v_read = (v_read_min + v_read_max) / 2

        i_lrs = (v_read / r_lrs) * 1e6  # µA
        i_hrs = (v_read / r_hrs) * 1e6  # µA
        i_ref = (i_lrs + i_hrs) / 2

        # Decision
        if abs(i_rram) > i_ref:
            decision = "LRS"
        else:
            decision = "HRS"

        margin = abs(abs(i_rram) - i_ref)

        return SenseState(
            currentUa=i_rram,
            referenceUa=i_ref,
            decision=decision,
            marginUa=margin,
        )

    def compute_frame(
        self,
        frame_id: str,
        time_ns: float,
        operation: OperationType,
        phase: OperationPhase,
        nodes: NodeVoltages,
        selected_cell: dict[str, int] | None,
        current_state: DeviceState,
        forming_done: bool,
    ) -> FrameState:
        """
        Compute complete FrameState for given conditions.

        This is the main entry point that orchestrates all computations.
        """
        if selected_cell is None:
            raise ValueError("selected_cell is required for single-cell model")

        row = selected_cell["row"]
        col = selected_cell["col"]

        # Get node voltages for selected cell
        wl_voltage = nodes.wl[row] if row < len(nodes.wl) else 0.0
        bl_voltage = nodes.bl[col] if col < len(nodes.bl) else 0.0
        sl_voltage = nodes.sl[col] if col < len(nodes.sl) else 0.0

        # Step 1: Compute transistor state
        transistor = self.compute_transistor_state(wl_voltage, bl_voltage, sl_voltage)

        # Step 2: Compute V_RRAM
        v_rram = self.compute_v_rram(bl_voltage, transistor, sl_voltage)

        # Step 3: Get current resistance
        r_rram = self.get_resistance_for_state(current_state)

        # Step 4: Compute I_RRAM
        i_rram = self.compute_i_rram(v_rram, r_rram, transistor.on)

        # Step 5: Apply compliance
        i_rram_limited, _ = self.apply_compliance(i_rram)

        # Step 6: Determine state transition (only during ACTIVE/HOLD phases)
        if phase in [OperationPhase.ACTIVE, OperationPhase.HOLD]:
            new_state, new_forming_done = self.determine_state_transition(
                current_state, v_rram, i_rram_limited, operation, forming_done
            )
        else:
            # No state change outside ACTIVE/HOLD phases
            new_state = current_state
            new_forming_done = forming_done

        # Step 7: Update resistance if state changed
        if new_state != current_state:
            r_rram = self.get_resistance_for_state(new_state)
            # Recompute current with new resistance
            i_rram_limited = self.compute_i_rram(v_rram, r_rram, transistor.on)
            i_rram_limited, _ = self.apply_compliance(i_rram_limited)

        # Step 8: Build RRAM state
        rram_state = RRAMState(
            v=v_rram,
            i=i_rram_limited,
            r=r_rram,
            state=new_state,
            formingDone=new_forming_done,
        )

        # Step 9: Compute sense (only in SENSE phase)
        sense = None
        if phase == OperationPhase.SENSE:
            sense = self.compute_sense(i_rram_limited, new_state)

        # Step 10: Build cell state
        cell = CellState(transistor=transistor, rram=rram_state)

        # Step 11: Build model metadata
        model = ModelMetadata(
            fidelity=self.fidelity,
            profileId=self.profile.id,
            profileVersion=self.profile.version,
            seed=self.seed,
        )

        # Step 12: Build frame (checks will be added by validation layer)
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
