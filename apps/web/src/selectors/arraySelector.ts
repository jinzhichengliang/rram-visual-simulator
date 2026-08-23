/**
 * Array View Selector — Extract array presentation data from FrameState.
 *
 * For V0.2, extracts:
 * - Selected cell position
 * - All cell states (for coloring)
 * - WL/BL/SL voltages (for line highlighting)
 * - Current path (for animation)
 *
 * Pure function — no physics calculations.
 */
import type { FrameState } from "../../../../packages/contracts/types";

export interface ArrayCellData {
  row: number;
  col: number;
  state: "PRISTINE" | "HRS" | "LRS";
  isSelected: boolean;
  transistorOn: boolean;
  vRram: number;
  iRram: number;
}

export interface ArrayViewData {
  rows: number;
  cols: number;
  selectedRow: number;
  selectedCol: number;
  cells: ArrayCellData[][];
  wlVoltages: number[];
  blVoltages: number[];
  slVoltages: number[];
  operation: string;
  phase: string;
}

/**
 * Extract array view data from FrameState.
 *
 * Note: V0.2 uses a simplified model where FrameState only contains
 * the selected cell. We expand it to a 4×4 grid for visualization.
 */
export function selectArrayViewData(frame: FrameState): ArrayViewData {
  const selectedCell = frame.selectedCell;
  const selectedRow = selectedCell?.row ?? 0;
  const selectedCol = selectedCell?.col ?? 0;

  // V0.2: 4×4 array
  const rows = 4;
  const cols = 4;

  // Build cell grid
  const cells: ArrayCellData[][] = [];
  for (let r = 0; r < rows; r++) {
    const row: ArrayCellData[] = [];
    for (let c = 0; c < cols; c++) {
      const isSelected = r === selectedRow && c === selectedCol;

      // Only selected cell has real data
      if (isSelected) {
        row.push({
          row: r,
          col: c,
          state: frame.cell.rram.state,
          isSelected: true,
          transistorOn: frame.cell.transistor.on,
          vRram: frame.cell.rram.v,
          iRram: frame.cell.rram.i,
        });
      } else {
        // Unselected cells: transistor OFF, no current
        // State is unknown in V0.2 (would need array state tracking)
        row.push({
          row: r,
          col: c,
          state: "PRISTINE", // Default for unselected
          isSelected: false,
          transistorOn: false,
          vRram: 0,
          iRram: 0,
        });
      }
    }
    cells.push(row);
  }

  return {
    rows,
    cols,
    selectedRow,
    selectedCol,
    cells,
    wlVoltages: frame.nodes.wl,
    blVoltages: frame.nodes.bl,
    slVoltages: frame.nodes.sl,
    operation: frame.operation,
    phase: frame.phase,
  };
}
