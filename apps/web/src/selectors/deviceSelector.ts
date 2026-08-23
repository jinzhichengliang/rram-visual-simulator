/**
 * Device View Selector — Pure function to extract Device View presentation data.
 *
 * This selector reads from FrameState and returns only the data needed
 * for Device View rendering. It performs NO physics calculations.
 */
import type { FrameState } from "../../../../packages/contracts/types";

export interface DeviceViewData {
  // Core measurements (from FrameState)
  vRram: number; // Voltage across RRAM in volts
  iRram: number; // Current through RRAM in microamps
  resistance: number; // RRAM resistance in ohms
  state: "PRISTINE" | "HRS" | "LRS";
  formingDone: boolean;

  // Visual indicators
  polarityPositive: boolean; // V_RRAM > 0
  currentFlowing: boolean; // |I_RRAM| > threshold
  currentDirection: "forward" | "reverse" | "none";

  // Compliance
  complianceActive: boolean;

  // Operation context
  operation: string;
  phase: string;

  // Fidelity
  fidelity: "F0" | "F1" | "F2" | "F3";
}

/**
 * Extract Device View data from FrameState.
 * Pure function — no side effects, no physics calculations.
 */
export function selectDeviceViewData(frame: FrameState): DeviceViewData {
  const vRram = frame.cell.rram.v;
  const iRram = frame.cell.rram.i;
  const resistance = frame.cell.rram.r;
  const state = frame.cell.rram.state;
  const formingDone = frame.cell.rram.formingDone;

  // Determine polarity
  const polarityPositive = vRram > 0;

  // Determine current flow (threshold: 0.1 µA)
  const currentThreshold = 0.1;
  const currentFlowing = Math.abs(iRram) > currentThreshold;
  const currentDirection =
    Math.abs(iRram) <= currentThreshold
      ? "none"
      : iRram > 0
        ? "forward"
        : "reverse";

  // Check compliance (if current near limit)
  // Note: We don't have compliance limit in FrameState, so we check if
  // the model metadata indicates compliance was active
  // For now, we infer from current magnitude
  const complianceActive = Math.abs(iRram) >= 49.9; // Near 50µA limit

  return {
    vRram,
    iRram,
    resistance,
    state,
    formingDone,
    polarityPositive,
    currentFlowing,
    currentDirection,
    complianceActive,
    operation: frame.operation,
    phase: frame.phase,
    fidelity: frame.model.fidelity,
  };
}
