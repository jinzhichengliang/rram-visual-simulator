/**
 * 1T1R Cell View Selector — Pure function to extract Cell View presentation data.
 *
 * This selector reads from FrameState and returns only the data needed
 * for 1T1R Cell View rendering. It performs NO physics calculations.
 */
import type { FrameState } from "../../../../packages/contracts/types";

export interface CellViewData {
  // Node voltages (from FrameState)
  wlVoltage: number; // Word line voltage in volts
  blVoltage: number; // Bit line voltage in volts
  slVoltage: number; // Source line voltage in volts

  // Transistor state
  transistorOn: boolean;
  vgs: number; // Gate-source voltage
  vds: number; // Drain-source voltage

  // RRAM state
  vRram: number;
  iRram: number;
  resistance: number;
  state: "PRISTINE" | "HRS" | "LRS";

  // Current path
  currentFlowing: boolean;
  currentDirection: "BL-to-SL" | "SL-to-BL" | "none";

  // Compliance
  complianceActive: boolean;

  // Operation context
  operation: string;
  phase: string;
}

/**
 * Extract 1T1R Cell View data from FrameState.
 * Pure function — no side effects, no physics calculations.
 */
export function selectCellViewData(frame: FrameState): CellViewData {
  // Get node voltages
  const selectedCell = frame.selectedCell;
  if (!selectedCell) {
    throw new Error("FrameState must have selectedCell for Cell View");
  }

  const wlVoltage = frame.nodes.wl[selectedCell.row] || 0;
  const blVoltage = frame.nodes.bl[selectedCell.col] || 0;
  const slVoltage = frame.nodes.sl[selectedCell.col] || 0;

  // Transistor state
  const transistorOn = frame.cell.transistor.on;
  const vgs = frame.cell.transistor.vg - frame.cell.transistor.vs;
  const vds = frame.cell.transistor.vd - frame.cell.transistor.vs;

  // RRAM state
  const vRram = frame.cell.rram.v;
  const iRram = frame.cell.rram.i;
  const resistance = frame.cell.rram.r;
  const state = frame.cell.rram.state;

  // Current path
  const currentThreshold = 0.1;
  const currentFlowing = Math.abs(iRram) > currentThreshold;
  const currentDirection =
    Math.abs(iRram) <= currentThreshold
      ? "none"
      : iRram > 0
        ? "BL-to-SL"
        : "SL-to-BL";

  // Compliance
  const complianceActive = Math.abs(iRram) >= 49.9;

  return {
    wlVoltage,
    blVoltage,
    slVoltage,
    transistorOn,
    vgs,
    vds,
    vRram,
    iRram,
    resistance,
    state,
    currentFlowing,
    currentDirection,
    complianceActive,
    operation: frame.operation,
    phase: frame.phase,
  };
}
