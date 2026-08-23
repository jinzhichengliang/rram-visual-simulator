"""
Peripheral Circuit Models — Decoder, Driver, Sense Amplifier.

V0.3: Implements the peripheral circuit causal chain:
  Command → Decoder → Driver → Cell → Sense → Verify
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from packages.contracts.types import (
    DeviceProfile,
    OperationType,
)


# ─── Decoder ──────────────────────────────────────────────────────────


class DecoderType(Enum):
    """Decoder types for array addressing."""
    ROW = "row"  # Selects WL
    COLUMN = "column"  # Selects BL/SL


@dataclass
class DecoderOutput:
    """Output from a decoder."""
    selected_line: int  # Which line is selected
    line_count: int  # Total number of lines
    voltages: list[float]  # Voltage on each line


class RowDecoder:
    """
    Row decoder — selects one WL line.

    Input: row address (0 to rows-1)
    Output: voltages on all WL lines (selected = V_gate, others = 0)
    """

    def __init__(self, rows: int, v_gate: float = 1.8):
        self.rows = rows
        self.v_gate = v_gate

    def decode(self, row: int) -> DecoderOutput:
        """Decode row address to WL voltages."""
        if not 0 <= row < self.rows:
            raise ValueError(f"Row {row} out of range [0, {self.rows})")

        voltages = [0.0] * self.rows
        voltages[row] = self.v_gate

        return DecoderOutput(
            selected_line=row,
            line_count=self.rows,
            voltages=voltages,
        )


class ColumnDecoder:
    """
    Column decoder — selects one BL/SL pair.

    Input: column address (0 to cols-1)
    Output: voltages on all BL/SL lines (selected = operation voltage, others = 0)
    """

    def __init__(self, cols: int):
        self.cols = cols

    def decode(
        self,
        col: int,
        operation: OperationType,
        pulse_amplitude: float,
        profile: DeviceProfile,
    ) -> tuple[DecoderOutput, DecoderOutput]:
        """
        Decode column address to BL/SL voltages.

        Returns (bl_output, sl_output).
        """
        if not 0 <= col < self.cols:
            raise ValueError(f"Column {col} out of range [0, {self.cols})")

        bl_voltages = [0.0] * self.cols
        sl_voltages = [0.0] * self.cols

        # Determine BL voltage based on operation
        if operation == OperationType.FORMING:
            bl_voltages[col] = pulse_amplitude
        elif operation == OperationType.SET:
            # SET polarity from profile
            if profile.setPolarity.value == "V_RRAM > 0":
                bl_voltages[col] = pulse_amplitude
            else:
                bl_voltages[col] = -pulse_amplitude
        elif operation == OperationType.RESET:
            # RESET polarity from profile
            if profile.resetPolarity.value == "V_RRAM < 0":
                bl_voltages[col] = -pulse_amplitude
            else:
                bl_voltages[col] = pulse_amplitude
        elif operation in [OperationType.READ, OperationType.VERIFY]:
            # Read uses small positive voltage
            v_read = (profile.ranges.vRead[0] + profile.ranges.vRead[1]) / 2
            bl_voltages[col] = v_read

        # SL is always ground
        sl_voltages[col] = 0.0

        bl_output = DecoderOutput(
            selected_line=col,
            line_count=self.cols,
            voltages=bl_voltages,
        )
        sl_output = DecoderOutput(
            selected_line=col,
            line_count=self.cols,
            voltages=sl_voltages,
        )

        return bl_output, sl_output


# ─── Driver ───────────────────────────────────────────────────────────


@dataclass
class DriverState:
    """State of a driver."""
    output_voltage: float
    current_limit_ua: Optional[float]  # Compliance limit if active
    is_active: bool


class WLDriver:
    """
    Word Line Driver — drives selected WL to gate voltage.

    Input: decoder output (WL voltages)
    Output: actual voltages on WL lines
    """

    def __init__(self, rows: int):
        self.rows = rows
        self.states = [DriverState(0.0, None, False) for _ in range(rows)]

    def drive(self, decoder_output: DecoderOutput) -> list[float]:
        """Drive WL lines based on decoder output."""
        voltages = []
        for i, v in enumerate(decoder_output.voltages):
            self.states[i] = DriverState(
                output_voltage=v,
                current_limit_ua=None,
                is_active=v > 0,
            )
            voltages.append(v)
        return voltages


class BLDriver:
    """
    Bit Line Driver — drives selected BL to operation voltage.

    Input: decoder output (BL voltages)
    Output: actual voltages on BL lines
    """

    def __init__(self, cols: int, compliance_ua: Optional[float] = None):
        self.cols = cols
        self.compliance_ua = compliance_ua
        self.states = [DriverState(0.0, compliance_ua, False) for _ in range(cols)]

    def drive(self, decoder_output: DecoderOutput) -> list[float]:
        """Drive BL lines based on decoder output."""
        voltages = []
        for i, v in enumerate(decoder_output.voltages):
            self.states[i] = DriverState(
                output_voltage=v,
                current_limit_ua=self.compliance_ua if abs(v) > 0 else None,
                is_active=abs(v) > 0,
            )
            voltages.append(v)
        return voltages


class SLDriver:
    """
    Source Line Driver — drives selected SL to ground.

    Input: decoder output (SL voltages)
    Output: actual voltages on SL lines
    """

    def __init__(self, cols: int):
        self.cols = cols
        self.states = [DriverState(0.0, None, False) for _ in range(cols)]

    def drive(self, decoder_output: DecoderOutput) -> list[float]:
        """Drive SL lines based on decoder output."""
        voltages = []
        for i, v in enumerate(decoder_output.voltages):
            self.states[i] = DriverState(
                output_voltage=v,
                current_limit_ua=None,
                is_active=True,  # SL is always connected to ground
            )
            voltages.append(v)
        return voltages


# ─── Sense Amplifier ──────────────────────────────────────────────────


@dataclass
class SenseResult:
    """Result from sense amplifier."""
    current_ua: float
    reference_ua: float
    decision: str  # "HRS" or "LRS"
    margin_ua: float
    passed: bool  # Whether margin is sufficient


class SenseAmplifier:
    """
    Sense Amplifier — compares read current with reference.

    Input: read current from selected cell
    Output: HRS/LRS decision with margin
    """

    def __init__(self, profile: DeviceProfile):
        self.profile = profile
        # Reference current = midpoint between HRS and LRS read currents
        v_read = (profile.ranges.vRead[0] + profile.ranges.vRead[1]) / 2
        r_lrs = (profile.ranges.rLrs[0] + profile.ranges.rLrs[1]) / 2
        r_hrs = (profile.ranges.rHrs[0] + profile.ranges.rHrs[1]) / 2
        i_lrs = (v_read / r_lrs) * 1e6  # µA
        i_hrs = (v_read / r_hrs) * 1e6  # µA
        self.reference_ua = (i_lrs + i_hrs) / 2
        self.min_margin_ua = (i_lrs - i_hrs) * 0.1  # 10% of full swing

    def sense(self, read_current_ua: float) -> SenseResult:
        """
        Sense the state of a cell.

        Args:
            read_current_ua: Current through the cell during read

        Returns:
            SenseResult with decision and margin
        """
        decision = "LRS" if abs(read_current_ua) > self.reference_ua else "HRS"
        margin_ua = abs(abs(read_current_ua) - self.reference_ua)
        passed = margin_ua >= self.min_margin_ua

        return SenseResult(
            current_ua=read_current_ua,
            reference_ua=self.reference_ua,
            decision=decision,
            margin_ua=margin_ua,
            passed=passed,
        )


# ─── Peripheral Circuit Controller ────────────────────────────────────


class PeripheralCircuit:
    """
    Peripheral Circuit Controller — orchestrates decoder, drivers, and sense.

    Manages the full causal chain:
      Command → RowDecoder → WLDriver
             → ColumnDecoder → BLDriver/SLDriver
             → Cell (via ArrayOrchestrator)
             → SenseAmplifier (for READ/VERIFY)
    """

    def __init__(self, rows: int, cols: int, profile: DeviceProfile):
        self.rows = rows
        self.cols = cols
        self.profile = profile

        # Decoders
        self.row_decoder = RowDecoder(rows)
        self.col_decoder = ColumnDecoder(cols)

        # Drivers
        self.wl_driver = WLDriver(rows)
        self.bl_driver = BLDriver(cols, profile.complianceUa)
        self.sl_driver = SLDriver(cols)

        # Sense amplifier
        self.sense_amp = SenseAmplifier(profile)

    def execute_phase(
        self,
        row: int,
        col: int,
        operation: OperationType,
        phase: str,
        pulse_amplitude: float,
    ) -> tuple[list[float], list[float], list[float]]:
        """
        Execute one phase of an operation.

        Returns (wl_voltages, bl_voltages, sl_voltages).
        """
        # PREPARE/RELEASE/COMPLETE: all voltages to 0
        if phase in ["PREPARE", "RELEASE", "COMPLETE"]:
            wl_out = DecoderOutput(row, self.rows, [0.0] * self.rows)
            bl_out = DecoderOutput(col, self.cols, [0.0] * self.cols)
            sl_out = DecoderOutput(col, self.cols, [0.0] * self.cols)
        else:
            # Decode
            wl_out = self.row_decoder.decode(row)
            bl_out, sl_out = self.col_decoder.decode(col, operation, pulse_amplitude, self.profile)

        # Drive
        wl_voltages = self.wl_driver.drive(wl_out)
        bl_voltages = self.bl_driver.drive(bl_out)
        sl_voltages = self.sl_driver.drive(sl_out)

        return wl_voltages, bl_voltages, sl_voltages

    def sense(self, read_current_ua: float) -> SenseResult:
        """Sense the state of a cell."""
        return self.sense_amp.sense(read_current_ua)
