"""
Canonical data contracts for RRAM Visual Simulator.

These Pydantic models are the single source of truth for all data structures
shared between Python backend and TypeScript frontend. Field names include
units where applicable (e.g., timeNs, currentUa, voltageV).

S01: Contract Lock — these schemas must be versioned and backward-compatible.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ─── Enums ─────────────────────────────────────────────────────────────


class OperationType(str, Enum):
    """RRAM operation types."""
    PRISTINE = "PRISTINE"
    FORMING = "FORMING"
    READ = "READ"
    SET = "SET"
    RESET = "RESET"
    VERIFY = "VERIFY"


class OperationPhase(str, Enum):
    """Phases within an operation."""
    PREPARE = "PREPARE"
    BIAS_RAMP = "BIAS_RAMP"
    ACTIVE = "ACTIVE"
    HOLD = "HOLD"
    RELEASE = "RELEASE"
    SENSE = "SENSE"
    COMPLETE = "COMPLETE"


class DeviceState(str, Enum):
    """RRAM device states."""
    PRISTINE = "PRISTINE"
    HRS = "HRS"
    LRS = "LRS"


class FidelityLevel(str, Enum):
    """Model fidelity levels."""
    F0 = "F0"  # Teaching model
    F1 = "F1"  # Parameterized compact
    F2 = "F2"  # SPICE/Verilog-A
    F3 = "F3"  # TCAD/experimental


class SeverityLevel(str, Enum):
    """Check result severity."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventType(str, Enum):
    """Semantic event types."""
    OPERATION_STARTED = "OPERATION_STARTED"
    BIAS_APPLIED = "BIAS_APPLIED"
    TRANSISTOR_ON = "TRANSISTOR_ON"
    TRANSISTOR_OFF = "TRANSISTOR_OFF"
    COMPLIANCE_ACTIVE = "COMPLIANCE_ACTIVE"
    DEVICE_STATE_CHANGED = "DEVICE_STATE_CHANGED"
    SENSE_SAMPLED = "SENSE_SAMPLED"
    VERIFY_DECIDED = "VERIFY_DECIDED"
    CHECK_FAILED = "CHECK_FAILED"
    OPERATION_COMPLETED = "OPERATION_COMPLETED"


class StackOrientation(str, Enum):
    """Physical stack orientation."""
    BL_RRAM_NMOS_SL = "BL-RRAM-NMOS-SL"
    BL_NMOS_RRAM_SL = "BL-NMOS-RRAM-SL"


class Polarity(str, Enum):
    """Polarity conditions."""
    POSITIVE = "V_RRAM > 0"
    NEGATIVE = "V_RRAM < 0"


# ─── Core Models ───────────────────────────────────────────────────────


class CheckResult(BaseModel):
    """Single physics invariant check result."""
    ruleId: str = Field(..., pattern=r"^INV-[0-9]{3}$")
    passed: bool
    severity: SeverityLevel
    message: str
    details: dict | None = None

    class Config:
        extra = "forbid"


class TransistorState(BaseModel):
    """Access transistor state."""
    vg: float = Field(..., description="Gate voltage in volts")
    vs: float = Field(..., description="Source voltage in volts")
    vd: float = Field(..., description="Drain voltage in volts")
    on: bool = Field(..., description="Whether transistor is conducting")
    complianceLimitUa: float | None = Field(None, ge=0)

    class Config:
        extra = "forbid"


class RRAMState(BaseModel):
    """RRAM device state."""
    v: float = Field(..., description="Voltage across RRAM in volts")
    i: float = Field(..., description="Current through RRAM in microamps")
    r: float = Field(..., gt=0, description="Resistance in ohms")
    state: DeviceState
    formingDone: bool
    gapNm: float | None = Field(None, ge=0, description="Filament gap in nm (F1+)")
    filamentProxy: float | None = Field(None, ge=0, le=1, description="Connectivity proxy (F1+)")
    temperatureK: float | None = Field(None, ge=0, description="Temperature in K (F1+)")

    class Config:
        extra = "forbid"


class CellState(BaseModel):
    """Complete cell state (transistor + RRAM)."""
    transistor: TransistorState
    rram: RRAMState

    class Config:
        extra = "forbid"


class NodeVoltages(BaseModel):
    """Array node voltages."""
    wl: list[float] = Field(..., description="Word line voltages in volts")
    bl: list[float] = Field(..., description="Bit line voltages in volts")
    sl: list[float] = Field(..., description="Source line voltages in volts")
    internal: dict[str, float] | None = None

    class Config:
        extra = "forbid"


class SenseState(BaseModel):
    """Sense amplifier state."""
    currentUa: float = Field(..., description="Sense current in microamps")
    referenceUa: float = Field(..., description="Reference current in microamps")
    decision: str | None = Field(None, pattern=r"^(HRS|LRS|UNKNOWN)$")
    marginUa: float | None = None

    class Config:
        extra = "forbid"


class ModelMetadata(BaseModel):
    """Model provenance and configuration."""
    fidelity: FidelityLevel
    profileId: str
    profileVersion: str
    seed: int

    class Config:
        extra = "forbid"


class FrameState(BaseModel):
    """
    Immutable snapshot of the complete simulator state.

    This is the single source of truth for all views, explanations, and waveforms.
    All field names include units where applicable.
    """
    frameId: str
    timeNs: float = Field(..., ge=0)
    operation: OperationType
    phase: OperationPhase
    selectedCell: dict[str, int] | None = None  # {row, col}
    nodes: NodeVoltages
    cell: CellState
    sense: SenseState | None = None
    model: ModelMetadata
    checks: list[CheckResult] = []

    class Config:
        extra = "forbid"

    @field_validator("selectedCell")
    @classmethod
    def validate_selected_cell(cls, v):
        if v is not None:
            if "row" not in v or "col" not in v:
                raise ValueError("selectedCell must have 'row' and 'col'")
            if v["row"] < 0 or v["col"] < 0:
                raise ValueError("selectedCell indices must be non-negative")
        return v


# ─── Operation & Profile ───────────────────────────────────────────────


class PulseSpec(BaseModel):
    """Pulse specification."""
    amplitudeV: float = Field(..., description="Pulse amplitude in volts")
    widthNs: float = Field(..., ge=0, description="Pulse width in nanoseconds")
    rampNs: float = Field(..., ge=0, description="Ramp time in nanoseconds")

    class Config:
        extra = "forbid"


class OperationSpec(BaseModel):
    """Specification for a single RRAM operation."""
    type: OperationType
    target: dict[str, int]  # {row, col}
    biasPolicyId: str
    pulse: PulseSpec
    complianceUa: float | None = Field(None, ge=0)
    verifyPolicyId: str | None = None

    class Config:
        extra = "forbid"

    @field_validator("target")
    @classmethod
    def validate_target(cls, v):
        if "row" not in v or "col" not in v:
            raise ValueError("target must have 'row' and 'col'")
        if v["row"] < 0 or v["col"] < 0:
            raise ValueError("target indices must be non-negative")
        return v


class DeviceRanges(BaseModel):
    """Operating ranges for device parameters."""
    vRead: list[float] = Field(..., min_length=2, max_length=2)
    vSet: list[float] = Field(..., min_length=2, max_length=2)
    vReset: list[float] = Field(..., min_length=2, max_length=2)
    vForm: list[float] = Field(..., min_length=2, max_length=2)
    rLrs: list[float] = Field(..., min_length=2, max_length=2)
    rHrs: list[float] = Field(..., min_length=2, max_length=2)

    class Config:
        extra = "forbid"


class DeviceTolerances(BaseModel):
    """Tolerance thresholds for validation."""
    readDisturbPct: float = Field(..., ge=0)
    currentConservationPct: float = Field(..., ge=0)
    crossViewAbs: float = Field(..., ge=0)

    class Config:
        extra = "forbid"


class LogicMap(BaseModel):
    """Mapping from device state to logic value."""
    LRS: Literal[0, 1]
    HRS: Literal[0, 1]

    class Config:
        extra = "forbid"


class DeviceProfile(BaseModel):
    """
    RRAM device configuration.

    Defines polarity, thresholds, operating ranges, and tolerances.
    Must be versioned; changes require golden scenario regression.
    """
    id: str
    version: str
    stackOrientation: StackOrientation
    vRramSignConvention: str = Field(..., pattern=r"^V\((top|bottom)\)-V\((top|bottom)\)$")
    setPolarity: Polarity
    resetPolarity: Polarity
    logicMap: LogicMap
    ranges: DeviceRanges
    complianceUa: float = Field(..., gt=0)
    tolerances: DeviceTolerances

    class Config:
        extra = "forbid"


# ─── Events ────────────────────────────────────────────────────────────


class SimulatorEvent(BaseModel):
    """Semantic event emitted during simulation."""
    eventId: str
    eventType: EventType
    timeNs: float = Field(..., ge=0)
    frameId: str
    payload: dict | None = None

    class Config:
        extra = "forbid"
