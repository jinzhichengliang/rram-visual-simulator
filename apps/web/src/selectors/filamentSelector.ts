/**
 * Filament View Selector — Extract filament visualization data from FrameState.
 *
 * V0.5 S18: Visualizes the conductive filament based on gap_nm and filament_proxy.
 * - F0: Conceptual visualization (connected/disconnected)
 * - F1: Parameterized visualization (gap size, filament width)
 *
 * Pure function — no physics calculations, only data extraction.
 */
import type { FrameState } from "../../../../packages/contracts/types";

export interface FilamentViewData {
  // Core observables from FrameState
  gapNm: number | null; // Gap size in nanometers (F1+)
  filamentProxy: number | null; // Filament connectivity 0-1 (F1+)
  temperatureK: number | null; // Local temperature in Kelvin (F1+)

  // Derived visualization parameters
  filamentWidth: number; // Visual width of filament (0-1)
  filamentOpacity: number; // Visual opacity (0-1)
  filamentColor: string; // Color based on state

  // State context
  state: "PRISTINE" | "HRS" | "LRS";
  fidelity: "F0" | "F1" | "F2" | "F3";
  formingDone: boolean;

  // Visual hints
  showGap: boolean; // Whether to show gap visualization
  gapSize: number; // Normalized gap size for visualization (0-1)
}

/**
 * Extract filament view data from FrameState.
 * Pure function — no side effects, no physics calculations.
 */
export function selectFilamentViewData(frame: FrameState): FilamentViewData {
  const gapNm = frame.cell.rram.gapNm ?? null;
  const filamentProxy = frame.cell.rram.filamentProxy ?? null;
  const temperatureK = frame.cell.rram.temperatureK ?? null;
  const state = frame.cell.rram.state;
  const fidelity = frame.model.fidelity;
  const formingDone = frame.cell.rram.formingDone;

  // Derive visualization parameters based on fidelity level
  let filamentWidth: number;
  let filamentOpacity: number;
  let filamentColor: string;
  let showGap: boolean;
  let gapSize: number;

  if (fidelity === "F0") {
    // F0: Conceptual visualization based on discrete state
    filamentWidth = state === "LRS" ? 0.8 : state === "HRS" ? 0.2 : 0.4;
    filamentOpacity = state === "LRS" ? 0.9 : state === "HRS" ? 0.3 : 0.5;
    filamentColor = state === "LRS" ? "#4ade80" : state === "HRS" ? "#f87171" : "#6b7280";
    showGap = false;
    gapSize = 0;
  } else {
    // F1+: Parameterized visualization based on gap_nm
    if (gapNm !== null && filamentProxy !== null) {
      // Normalize gap for visualization (assuming gap range 0-10nm)
      const maxGapNm = 10.0;
      const normalizedGap = Math.min(1.0, gapNm / maxGapNm);

      // Filament width inversely proportional to gap
      filamentWidth = Math.max(0.1, 1.0 - normalizedGap);
      filamentOpacity = Math.max(0.2, filamentProxy);

      // Color gradient: green (LRS) → yellow (intermediate) → red (HRS)
      if (filamentProxy > 0.7) {
        filamentColor = "#4ade80"; // Green for LRS
      } else if (filamentProxy > 0.3) {
        filamentColor = "#fbbf24"; // Yellow for intermediate
      } else {
        filamentColor = "#f87171"; // Red for HRS
      }

      showGap = true;
      gapSize = normalizedGap;
    } else {
      // Fallback if observables are missing
      filamentWidth = 0.4;
      filamentOpacity = 0.5;
      filamentColor = "#6b7280";
      showGap = false;
      gapSize = 0;
    }
  }

  return {
    gapNm,
    filamentProxy,
    temperatureK,
    filamentWidth,
    filamentOpacity,
    filamentColor,
    state,
    fidelity,
    formingDone,
    showGap,
    gapSize,
  };
}
