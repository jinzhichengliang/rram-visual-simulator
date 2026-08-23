"""
Array Domain Model — 4×4 1T1R Array with decoder and bias policy.

Key design rules:
- Every cell uses the SAME TeachingModelAdapter (no duplicate models)
- Array only handles topology, selection, bias distribution, and aggregation
- Unselected cell bias policy is configurable
"""
from __future__ import annotations

from dataclasses import dataclass, field

from packages.contracts.types import (
    CellState,
    DeviceProfile,
    DeviceState,
    FrameState,
    ModelMetadata,
    NodeVoltages,
    OperationPhase,
    OperationType,
    RRAMState,
    TransistorState,
)
from simulator.models.teaching_model import TeachingModelAdapter


# ─── Bias Policy ──────────────────────────────────────────────────────


@dataclass
class ArrayBiasPolicy:
    """
    Defines how voltages are assigned to selected/unselected lines.

    For 1T1R array:
    - Selected WL gets V_gate (turns ON access transistor)
    - Unselected WL gets 0V (keeps transistors OFF)
    - Selected BL gets operation voltage
    - Selected SL gets 0V (ground)
    - Unselected BL/SL get 0V (V0.2 simplified)
    """
    v_gate: float = 1.8  # WL voltage to turn ON NMOS
    v_unselected_wl: float = 0.0
    v_unselected_bl: float = 0.0
    v_unselected_sl: float = 0.0


# ─── Cell Summary ─────────────────────────────────────────────────────


@dataclass
class CellSummary:
    """Summary of a single cell's state for array-level queries."""
    row: int
    col: int
    transistor_on: bool
    rram_state: DeviceState
    rram_r: float
    v_rram: float
    i_rram: float
    forming_done: bool
    is_selected: bool


# ─── Array State ──────────────────────────────────────────────────────


class ArrayState:
    """
    Manages the 4×4 1T1R array state.

    Each cell maintains its own device state independently.
    The array provides decoder logic and bias distribution.
    """

    def __init__(self, rows: int = 4, cols: int = 4):
        self.rows = rows
        self.cols = cols

        # Per-cell device state (independent)
        self.cell_states: list[list[DeviceState]] = [
            [DeviceState.PRISTINE for _ in range(cols)] for _ in range(rows)
        ]
        self.cell_forming_done: list[list[bool]] = [
            [False for _ in range(cols)] for _ in range(rows)
        ]

    def get_state(self, row: int, col: int) -> DeviceState:
        return self.cell_states[row][col]

    def set_state(self, row: int, col: int, state: DeviceState):
        self.cell_states[row][col] = state

    def get_forming_done(self, row: int, col: int) -> bool:
        return self.cell_forming_done[row][col]

    def set_forming_done(self, row: int, col: int, done: bool):
        self.cell_forming_done[row][col] = done

    def reset(self):
        """Reset all cells to PRISTINE."""
        for r in range(self.rows):
            for c in range(self.cols):
                self.cell_states[r][c] = DeviceState.PRISTINE
                self.cell_forming_done[r][c] = False


# ─── Array Decoder ────────────────────────────────────────────────────


class ArrayDecoder:
    """
    Decodes target (row, col) into node voltage arrays.

    Implements the bias policy for selected/unselected lines.
    """

    def __init__(self, rows: int, cols: int, bias_policy: ArrayBiasPolicy | None = None):
        self.rows = rows
        self.cols = cols
        self.bias_policy = bias_policy or ArrayBiasPolicy()

    def decode(
        self,
        target_row: int,
        target_col: int,
        operation: OperationType,
        phase: OperationPhase,
        pulse_amplitude: float,
    ) -> NodeVoltages:
        """
        Decode target cell into node voltage arrays.

        Returns NodeVoltages with voltages for all WL/BL/SL lines.
        """
        wl = [self.bias_policy.v_unselected_wl] * self.rows
        bl = [self.bias_policy.v_unselected_bl] * self.cols
        sl = [self.bias_policy.v_unselected_sl] * self.cols

        # No bias in PREPARE/RELEASE/COMPLETE phases
        if phase in [OperationPhase.PREPARE, OperationPhase.RELEASE, OperationPhase.COMPLETE]:
            return NodeVoltages(wl=wl, bl=bl, sl=sl)

        # Selected WL: turn ON access transistor
        wl[target_row] = self.bias_policy.v_gate

        # Selected BL: operation voltage
        if phase in [OperationPhase.BIAS_RAMP, OperationPhase.ACTIVE, OperationPhase.HOLD, OperationPhase.SENSE]:
            if operation == OperationType.FORMING:
                bl[target_col] = pulse_amplitude
            elif operation == OperationType.SET:
                bl[target_col] = pulse_amplitude
            elif operation == OperationType.RESET:
                bl[target_col] = -pulse_amplitude
            elif operation in [OperationType.READ, OperationType.VERIFY]:
                # Use midpoint of read range
                bl[target_col] = pulse_amplitude

        # Selected SL: ground
        sl[target_col] = 0.0

        return NodeVoltages(wl=wl, bl=bl, sl=sl)


# ─── Array Orchestrator ───────────────────────────────────────────────


class ArrayOrchestrator:
    """
    Orchestrates operations on a 4×4 1T1R array.

    Uses a single TeachingModelAdapter for all cells.
    Array only handles topology, selection, and bias distribution.
    """

    def __init__(self, profile: DeviceProfile, rows: int = 4, cols: int = 4, seed: int = 42):
        self.profile = profile
        self.rows = rows
        self.cols = cols
        self.seed = seed

        # Single model adapter shared by all cells
        self.model = TeachingModelAdapter(profile, seed)

        # Array state
        self.array_state = ArrayState(rows, cols)

        # Decoder
        self.decoder = ArrayDecoder(rows, cols)

        # Frame history
        self.frames: list[FrameState] = []
        self.frame_counter = 0
        self.time_ns = 0.0

    def reset(self):
        """Reset entire array to initial state."""
        self.array_state.reset()
        self.frames = []
        self.frame_counter = 0
        self.time_ns = 0.0

    def _next_frame_id(self) -> str:
        self.frame_counter += 1
        return f"frame-{self.frame_counter:06d}"

    def execute_operation(
        self,
        operation: OperationType,
        target_row: int,
        target_col: int,
        pulse_amplitude: float,
    ) -> list[FrameState]:
        """
        Execute operation on target cell.

        Only the target cell undergoes state transitions.
        Unselected cells remain unchanged (their transistors are OFF).
        """
        # Phase sequence
        if operation == OperationType.FORMING:
            phases = [
                OperationPhase.PREPARE,
                OperationPhase.BIAS_RAMP,
                OperationPhase.ACTIVE,
                OperationPhase.HOLD,
                OperationPhase.RELEASE,
                OperationPhase.COMPLETE,
            ]
        elif operation == OperationType.READ:
            phases = [
                OperationPhase.PREPARE,
                OperationPhase.BIAS_RAMP,
                OperationPhase.ACTIVE,
                OperationPhase.SENSE,
                OperationPhase.RELEASE,
                OperationPhase.COMPLETE,
            ]
        else:
            phases = [
                OperationPhase.PREPARE,
                OperationPhase.BIAS_RAMP,
                OperationPhase.ACTIVE,
                OperationPhase.HOLD,
                OperationPhase.RELEASE,
                OperationPhase.COMPLETE,
            ]

        frames = []
        for phase in phases:
            frame = self._execute_phase(operation, target_row, target_col, pulse_amplitude, phase)
            frames.append(frame)

        return frames

    def _execute_phase(
        self,
        operation: OperationType,
        target_row: int,
        target_col: int,
        pulse_amplitude: float,
        phase: OperationPhase,
    ) -> FrameState:
        """Execute a single phase and return FrameState."""
        # Decode bias
        nodes = self.decoder.decode(target_row, target_col, operation, phase, pulse_amplitude)

        # Advance time
        self.time_ns += 10.0
        frame_id = self._next_frame_id()

        # Compute target cell state using shared model
        target_cell_state = self.array_state.get_state(target_row, target_col)
        target_forming_done = self.array_state.get_forming_done(target_row, target_col)

        target_frame = self.model.compute_frame(
            frame_id=frame_id,
            time_ns=self.time_ns,
            operation=operation,
            phase=phase,
            nodes=nodes,
            selected_cell={"row": target_row, "col": target_col},
            current_state=target_cell_state,
            forming_done=target_forming_done,
        )

        # Update target cell state
        self.array_state.set_state(target_row, target_col, target_frame.cell.rram.state)
        self.array_state.set_forming_done(target_row, target_col, target_frame.cell.rram.formingDone)

        # Build array-level frame (target cell data + all cell summaries)
        self.frames.append(target_frame)
        return target_frame

    def get_cell_summaries(self) -> list[list[CellSummary]]:
        """Get summary of all cells in the array."""
        summaries = []
        for r in range(self.rows):
            row_summaries = []
            for c in range(self.cols):
                state = self.array_state.get_state(r, c)
                forming_done = self.array_state.get_forming_done(r, c)
                r_val = self.model.get_resistance_for_state(state)

                row_summaries.append(CellSummary(
                    row=r,
                    col=c,
                    transistor_on=False,  # Only true during operation
                    rram_state=state,
                    rram_r=r_val,
                    v_rram=0.0,
                    i_rram=0.0,
                    forming_done=forming_done,
                    is_selected=False,
                ))
            summaries.append(row_summaries)
        return summaries

    def get_current_frame(self) -> FrameState | None:
        """Get the most recent frame."""
        return self.frames[-1] if self.frames else None

    def get_frame_history(self) -> list[FrameState]:
        """Get all frames."""
        return self.frames.copy()

    def compute_port_current(self) -> float:
        """
        Compute total array port current (sum of all cell branch currents).

        For INV-010: port current should equal sum of branch currents.
        """
        if not self.frames:
            return 0.0

        last_frame = self.frames[-1]
        # In V0.2 simplified model, only selected cell has current
        return last_frame.cell.rram.i
