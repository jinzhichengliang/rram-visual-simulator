"""
Simulation Orchestrator — Manages operation state machine and event timeline.

The orchestrator coordinates:
1. Operation lifecycle (PREPARE → BIAS_RAMP → ACTIVE → ... → COMPLETE)
2. Frame generation at each phase
3. Event emission
4. State persistence across operations
"""
from __future__ import annotations

from typing import ClassVar

from packages.contracts.types import (
    DeviceProfile,
    DeviceState,
    FrameState,
    NodeVoltages,
    OperationPhase,
    OperationSpec,
    OperationType,
    SimulatorEvent,
)
from validation.invariants.physics_invariants import CheckEngine

from simulator.models.teaching_model import TeachingModelAdapter


class SimulationState:
    """Mutable state that persists across operations."""

    def __init__(self, profile: DeviceProfile, seed: int = 42):
        self.profile = profile
        self.seed = seed
        self.device_state = DeviceState.PRISTINE
        self.forming_done = False
        self.frame_counter = 0
        self.time_ns = 0.0
        self.frames: list[FrameState] = []
        self.events: list[SimulatorEvent] = []

    def next_frame_id(self) -> str:
        self.frame_counter += 1
        return f"frame-{self.frame_counter:06d}"

    def advance_time(self, delta_ns: float) -> float:
        self.time_ns += delta_ns
        return self.time_ns

    def add_frame(self, frame: FrameState) -> None:
        self.frames.append(frame)

    def add_event(self, event: SimulatorEvent) -> None:
        self.events.append(event)


class SimulationOrchestrator:
    """
    Orchestrates simulation operations.

    Manages the lifecycle of operations and generates FrameStates
    according to the causal chain defined in the architecture.
    """

    # Phase sequence for each operation type
    PHASE_SEQUENCES: ClassVar[dict] = {
        OperationType.PRISTINE: [OperationPhase.PREPARE, OperationPhase.COMPLETE],
        OperationType.FORMING: [
            OperationPhase.PREPARE,
            OperationPhase.BIAS_RAMP,
            OperationPhase.ACTIVE,
            OperationPhase.HOLD,
            OperationPhase.RELEASE,
            OperationPhase.COMPLETE,
        ],
        OperationType.READ: [
            OperationPhase.PREPARE,
            OperationPhase.BIAS_RAMP,
            OperationPhase.ACTIVE,
            OperationPhase.SENSE,
            OperationPhase.RELEASE,
            OperationPhase.COMPLETE,
        ],
        OperationType.SET: [
            OperationPhase.PREPARE,
            OperationPhase.BIAS_RAMP,
            OperationPhase.ACTIVE,
            OperationPhase.HOLD,
            OperationPhase.RELEASE,
            OperationPhase.COMPLETE,
        ],
        OperationType.RESET: [
            OperationPhase.PREPARE,
            OperationPhase.BIAS_RAMP,
            OperationPhase.ACTIVE,
            OperationPhase.HOLD,
            OperationPhase.RELEASE,
            OperationPhase.COMPLETE,
        ],
        OperationType.VERIFY: [
            OperationPhase.PREPARE,
            OperationPhase.BIAS_RAMP,
            OperationPhase.ACTIVE,
            OperationPhase.SENSE,
            OperationPhase.RELEASE,
            OperationPhase.COMPLETE,
        ],
    }

    def __init__(self, profile: DeviceProfile, seed: int = 42):
        self.profile = profile
        self.seed = seed
        self.model = TeachingModelAdapter(profile, seed)
        self.state = SimulationState(profile, seed)
        self.check_engine = CheckEngine(profile)

    def reset(self) -> None:
        """Reset simulation to initial state."""
        self.state = SimulationState(self.profile, self.seed)

    def compute_bias_for_operation(
        self,
        operation: OperationSpec,
        phase: OperationPhase,
    ) -> NodeVoltages:
        """
        Compute node voltages for given operation and phase.

        This is where bias policy is applied.
        """
        # Determine array size from profile (teaching: 1x1 for now)
        array_size = 1

        # Initialize all nodes to 0
        wl = [0.0] * array_size
        bl = [0.0] * array_size
        sl = [0.0] * array_size

        row = operation.target["row"]
        col = operation.target["col"]

        if phase == OperationPhase.PREPARE:
            # All nodes at 0
            pass

        elif phase == OperationPhase.BIAS_RAMP:
            # Ramp to target voltages
            # For teaching model, assume instant ramp
            wl[row] = self._get_wl_voltage(operation)
            bl[col] = self._get_bl_voltage(operation)
            sl[col] = self._get_sl_voltage(operation)

        elif phase in [
            OperationPhase.ACTIVE,
            OperationPhase.HOLD,
            OperationPhase.SENSE,
        ]:
            # Full bias applied
            wl[row] = self._get_wl_voltage(operation)
            bl[col] = self._get_bl_voltage(operation)
            sl[col] = self._get_sl_voltage(operation)

        elif phase == OperationPhase.RELEASE:
            # Release bias
            pass

        elif phase == OperationPhase.COMPLETE:
            # All released
            pass

        return NodeVoltages(wl=wl, bl=bl, sl=sl)

    def _get_wl_voltage(self, operation: OperationSpec) -> float:
        """Get WL voltage for operation (turn on transistor)."""
        # Teaching model: WL = 1.8V to turn on NMOS
        return 1.8

    def _get_bl_voltage(self, operation: OperationSpec) -> float:
        """Get BL voltage based on operation type and polarity."""
        amplitude = operation.pulse.amplitudeV

        if operation.type == OperationType.FORMING:
            # Forming uses positive voltage (teaching default)
            return amplitude
        elif operation.type == OperationType.SET:
            # SET polarity from profile
            if self.profile.setPolarity.value == "V_RRAM > 0":
                return amplitude
            else:
                return -amplitude
        elif operation.type == OperationType.RESET:
            # RESET polarity from profile
            if self.profile.resetPolarity.value == "V_RRAM < 0":
                return -amplitude
            else:
                return amplitude
        elif operation.type in [OperationType.READ, OperationType.VERIFY]:
            # Read uses small positive voltage
            v_read_min, v_read_max = self.profile.ranges.vRead
            return (v_read_min + v_read_max) / 2
        else:
            return 0.0

    def _get_sl_voltage(self, operation: OperationSpec) -> float:
        """Get SL voltage (ground for teaching model)."""
        return 0.0

    def execute_phase(
        self,
        operation: OperationSpec,
        phase: OperationPhase,
    ) -> FrameState:
        """
        Execute a single phase of an operation.

        Returns the generated FrameState with invariant check results.
        """
        # Compute bias
        nodes = self.compute_bias_for_operation(operation, phase)

        # Compute frame
        frame_id = self.state.next_frame_id()
        time_ns = self.state.advance_time(10.0)  # 10ns per phase

        frame = self.model.compute_frame(
            frame_id=frame_id,
            time_ns=time_ns,
            operation=operation.type,
            phase=phase,
            nodes=nodes,
            selected_cell=operation.target,
            current_state=self.state.device_state,
            forming_done=self.state.forming_done,
        )

        # Run invariant checks
        prev_frame = self.state.frames[-1] if self.state.frames else None
        check_results = self.check_engine.check_frame(frame, prev_frame)

        # Create new frame with check results attached
        frame = frame.model_copy(update={"checks": check_results})

        # Update simulation state
        self.state.device_state = frame.cell.rram.state
        self.state.forming_done = frame.cell.rram.formingDone
        self.state.add_frame(frame)

        # Emit event
        event = self._create_event(operation, phase, frame)
        self.state.add_event(event)

        return frame

    def _create_event(
        self,
        operation: OperationSpec,
        phase: OperationPhase,
        frame: FrameState,
    ) -> SimulatorEvent:
        """Create semantic event for phase transition."""
        from packages.contracts.types import EventType

        event_type_map = {
            OperationPhase.PREPARE: EventType.OPERATION_STARTED,
            OperationPhase.BIAS_RAMP: EventType.BIAS_APPLIED,
            OperationPhase.ACTIVE: EventType.DEVICE_STATE_CHANGED,
            OperationPhase.SENSE: EventType.SENSE_SAMPLED,
            OperationPhase.COMPLETE: EventType.OPERATION_COMPLETED,
        }

        event_type = event_type_map.get(phase, EventType.BIAS_APPLIED)

        # Check if transistor state changed
        if phase == OperationPhase.BIAS_RAMP:
            if frame.cell.transistor.on:
                event_type = EventType.TRANSISTOR_ON
            else:
                event_type = EventType.TRANSISTOR_OFF

        return SimulatorEvent(
            eventId=f"evt-{len(self.state.events) + 1:06d}",
            eventType=event_type,
            timeNs=frame.timeNs,
            frameId=frame.frameId,
            payload={
                "operation": operation.type.value,
                "phase": phase.value,
                "target": operation.target,
            },
        )

    def execute_operation(self, operation: OperationSpec) -> list[FrameState]:
        """
        Execute complete operation through all phases.

        Returns list of FrameStates generated.
        """
        phases = self.PHASE_SEQUENCES.get(operation.type, [])
        frames = []

        for phase in phases:
            frame = self.execute_phase(operation, phase)
            frames.append(frame)

        return frames

    def get_current_state(self) -> DeviceState:
        """Get current device state."""
        return self.state.device_state

    def get_frame_history(self) -> list[FrameState]:
        """Get all generated frames."""
        return self.state.frames.copy()

    def get_event_history(self) -> list[SimulatorEvent]:
        """Get all emitted events."""
        return self.state.events.copy()
