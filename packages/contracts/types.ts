/**
 * Canonical data contracts for RRAM Visual Simulator.
 *
 * These TypeScript types are the single source of truth for all data structures
 * shared between Python backend and TypeScript frontend. Field names include
 * units where applicable (e.g., timeNs, currentUa, voltageV).
 *
 * S01: Contract Lock — these schemas must be versioned and backward-compatible.
 */

// ─── Enums ─────────────────────────────────────────────────────────────

export type OperationType =
  | "PRISTINE"
  | "FORMING"
  | "READ"
  | "SET"
  | "RESET"
  | "VERIFY";

export type OperationPhase =
  | "PREPARE"
  | "BIAS_RAMP"
  | "ACTIVE"
  | "HOLD"
  | "RELEASE"
  | "SENSE"
  | "COMPLETE";

export type DeviceState = "PRISTINE" | "HRS" | "LRS";

export type FidelityLevel = "F0" | "F1" | "F2" | "F3";

export type SeverityLevel = "info" | "warning" | "error" | "critical";

export type EventType =
  | "OPERATION_STARTED"
  | "BIAS_APPLIED"
  | "TRANSISTOR_ON"
  | "TRANSISTOR_OFF"
  | "COMPLIANCE_ACTIVE"
  | "DEVICE_STATE_CHANGED"
  | "SENSE_SAMPLED"
  | "VERIFY_DECIDED"
  | "CHECK_FAILED"
  | "OPERATION_COMPLETED";

export type StackOrientation = "BL-RRAM-NMOS-SL" | "BL-NMOS-RRAM-SL";

export type Polarity = "V_RRAM > 0" | "V_RRAM < 0";

// ─── Core Models ───────────────────────────────────────────────────────

export interface CheckResult {
  ruleId: string; // Pattern: INV-NNN
  passed: boolean;
  severity: SeverityLevel;
  message: string;
  details?: Record<string, unknown>;
}

export interface TransistorState {
  vg: number; // Gate voltage in volts
  vs: number; // Source voltage in volts
  vd: number; // Drain voltage in volts
  on: boolean; // Whether transistor is conducting
  complianceLimitUa?: number; // Compliance current limit in microamps
}

export interface RRAMState {
  v: number; // Voltage across RRAM in volts
  i: number; // Current through RRAM in microamps
  r: number; // Resistance in ohms (>0)
  state: DeviceState;
  formingDone: boolean;
  gapNm?: number; // Filament gap in nm (F1+ models, >=0)
  filamentProxy?: number; // Connectivity proxy (F1+ models, 0-1)
  temperatureK?: number; // Temperature in K (F1+ models, >=0)
}

export interface CellState {
  transistor: TransistorState;
  rram: RRAMState;
}

export interface NodeVoltages {
  wl: number[]; // Word line voltages in volts
  bl: number[]; // Bit line voltages in volts
  sl: number[]; // Source line voltages in volts
  internal?: Record<string, number>;
}

export interface SenseState {
  currentUa: number; // Sense current in microamps
  referenceUa: number; // Reference current in microamps
  decision?: "HRS" | "LRS" | "UNKNOWN";
  marginUa?: number;
}

export interface ModelMetadata {
  fidelity: FidelityLevel;
  profileId: string;
  profileVersion: string;
  seed: number;
}

export interface SelectedCell {
  row: number;
  col: number;
}

export interface FrameState {
  frameId: string;
  timeNs: number; // >=0
  operation: OperationType;
  phase: OperationPhase;
  selectedCell?: SelectedCell;
  nodes: NodeVoltages;
  cell: CellState;
  sense?: SenseState;
  model: ModelMetadata;
  checks: CheckResult[];
}

// ─── Operation & Profile ───────────────────────────────────────────────

export interface PulseSpec {
  amplitudeV: number; // Pulse amplitude in volts
  widthNs: number; // Pulse width in nanoseconds (>=0)
  rampNs: number; // Ramp time in nanoseconds (>=0)
}

export interface OperationTarget {
  row: number;
  col: number;
}

export interface OperationSpec {
  type: OperationType;
  target: OperationTarget;
  biasPolicyId: string;
  pulse: PulseSpec;
  complianceUa?: number; // >=0
  verifyPolicyId?: string;
}

export interface DeviceRanges {
  vRead: [number, number];
  vSet: [number, number];
  vReset: [number, number];
  vForm: [number, number];
  rLrs: [number, number];
  rHrs: [number, number];
}

export interface DeviceTolerances {
  readDisturbPct: number; // >=0
  currentConservationPct: number; // >=0
  crossViewAbs: number; // >=0
}

export interface LogicMap {
  LRS: 0 | 1;
  HRS: 0 | 1;
}

export interface DeviceProfile {
  id: string;
  version: string;
  stackOrientation: StackOrientation;
  vRramSignConvention: string; // Pattern: V(top)-V(bottom) or V(bottom)-V(top)
  setPolarity: Polarity;
  resetPolarity: Polarity;
  logicMap: LogicMap;
  ranges: DeviceRanges;
  complianceUa: number; // >0
  tolerances: DeviceTolerances;
}

// ─── Events ────────────────────────────────────────────────────────────

export interface SimulatorEvent {
  eventId: string;
  eventType: EventType;
  timeNs: number; // >=0
  frameId: string;
  payload?: Record<string, unknown>;
}

// ─── Validation Utilities ──────────────────────────────────────────────

/**
 * Validate that a FrameState has all required fields.
 * This is a runtime check; TypeScript provides compile-time safety.
 */
export function validateFrameState(frame: unknown): frame is FrameState {
  if (!frame || typeof frame !== "object") return false;
  const f = frame as Record<string, unknown>;

  // Required fields
  if (typeof f.frameId !== "string") return false;
  if (typeof f.timeNs !== "number" || f.timeNs < 0) return false;
  if (
    typeof f.operation !== "string" ||
    !["PRISTINE", "FORMING", "READ", "SET", "RESET", "VERIFY"].includes(
      f.operation as string
    )
  )
    return false;
  if (
    typeof f.phase !== "string" ||
    !["PREPARE", "BIAS_RAMP", "ACTIVE", "HOLD", "RELEASE", "SENSE", "COMPLETE"].includes(
      f.phase as string
    )
  )
    return false;
  if (!f.nodes || typeof f.nodes !== "object") return false;
  if (!f.cell || typeof f.cell !== "object") return false;
  if (!f.model || typeof f.model !== "object") return false;
  if (!Array.isArray(f.checks)) return false;

  return true;
}
