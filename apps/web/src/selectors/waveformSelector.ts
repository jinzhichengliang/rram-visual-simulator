/**
 * Waveform View Selector — Extract waveform data from FrameState history.
 *
 * This selector reads from an array of FrameStates and returns time-series data
 * for waveform visualization. It performs NO physics calculations.
 */
import type { FrameState } from "../../../../packages/contracts/types";

export interface WaveformPoint {
  timeNs: number;
  frameId: string;
  operation: string;
  phase: string;

  // Node voltages
  wlVoltage: number;
  blVoltage: number;
  slVoltage: number;

  // Device measurements
  vRram: number;
  iRram: number;
  resistance: number;
  state: "PRISTINE" | "HRS" | "LRS";

  // Transistor
  transistorOn: boolean;
}

export interface WaveformData {
  points: WaveformPoint[];
  currentTimeNs: number;
  currentFrameId: string;
}

/**
 * Extract waveform data from FrameState history.
 * Pure function — no side effects, no physics calculations.
 */
export function selectWaveformData(
  frames: FrameState[],
  currentFrameId?: string
): WaveformData {
  const points: WaveformPoint[] = frames.map((frame) => {
    const selectedCell = frame.selectedCell;
    const row = selectedCell?.row ?? 0;
    const col = selectedCell?.col ?? 0;

    return {
      timeNs: frame.timeNs,
      frameId: frame.frameId,
      operation: frame.operation,
      phase: frame.phase,

      // Node voltages
      wlVoltage: frame.nodes.wl[row] || 0,
      blVoltage: frame.nodes.bl[col] || 0,
      slVoltage: frame.nodes.sl[col] || 0,

      // Device measurements
      vRram: frame.cell.rram.v,
      iRram: frame.cell.rram.i,
      resistance: frame.cell.rram.r,
      state: frame.cell.rram.state,

      // Transistor
      transistorOn: frame.cell.transistor.on,
    };
  });

  const currentFrame = currentFrameId
    ? frames.find((f) => f.frameId === currentFrameId)
    : frames[frames.length - 1];

  return {
    points,
    currentTimeNs: currentFrame?.timeNs ?? 0,
    currentFrameId: currentFrame?.frameId ?? "",
  };
}
