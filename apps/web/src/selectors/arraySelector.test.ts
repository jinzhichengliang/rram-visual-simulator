/**
 * S08 — Array View tests.
 *
 * Tests:
 * 1. Array selector extracts correct data
 * 2. Selected cell highlighting
 * 3. Voltage display
 * 4. Current flow conditions
 */
import { describe, it, expect } from "vitest";
import { selectArrayViewData } from "../selectors/arraySelector";
import type { FrameState } from "../../../../packages/contracts/types";

// Test fixture: selected cell (1, 2) in LRS state
const arrayFrame: FrameState = {
  frameId: "array-001",
  timeNs: 100,
  operation: "READ",
  phase: "ACTIVE",
  selectedCell: { row: 1, col: 2 },
  nodes: {
    wl: [0, 1.8, 0, 0],
    bl: [0, 0, 0.15, 0],
    sl: [0, 0, 0, 0],
  },
  cell: {
    transistor: { vg: 1.8, vs: 0, vd: 0.15, on: true },
    rram: { v: 0.15, i: 3.75, r: 40000, state: "LRS", formingDone: true },
  },
  model: { fidelity: "F0", profileId: "test", profileVersion: "1.0.0", seed: 42 },
  checks: [],
};

// Test fixture: no current flowing
const noCurrentFrame: FrameState = {
  ...arrayFrame,
  cell: {
    transistor: { vg: 1.8, vs: 0, vd: 0.15, on: true },
    rram: { v: 0.15, i: 0.05, r: 1e6, state: "HRS", formingDone: true },
  },
};

describe("Array View Selector", () => {
  it("extracts 4×4 grid correctly", () => {
    const data = selectArrayViewData(arrayFrame);

    expect(data.rows).toBe(4);
    expect(data.cols).toBe(4);
    expect(data.cells).toHaveLength(4);
    expect(data.cells[0]).toHaveLength(4);
  });

  it("marks selected cell correctly", () => {
    const data = selectArrayViewData(arrayFrame);

    expect(data.selectedRow).toBe(1);
    expect(data.selectedCol).toBe(2);

    // Selected cell
    const selectedCell = data.cells[1][2];
    expect(selectedCell.isSelected).toBe(true);
    expect(selectedCell.state).toBe("LRS");
    expect(selectedCell.transistorOn).toBe(true);
    expect(selectedCell.vRram).toBe(0.15);
    expect(selectedCell.iRram).toBe(3.75);

    // Unselected cells
    const unselectedCell = data.cells[0][0];
    expect(unselectedCell.isSelected).toBe(false);
    expect(unselectedCell.transistorOn).toBe(false);
    expect(unselectedCell.iRram).toBe(0);
  });

  it("extracts WL/BL/SL voltages correctly", () => {
    const data = selectArrayViewData(arrayFrame);

    expect(data.wlVoltages).toEqual([0, 1.8, 0, 0]);
    expect(data.blVoltages).toEqual([0, 0, 0.15, 0]);
    expect(data.slVoltages).toEqual([0, 0, 0, 0]);
  });

  it("preserves operation and phase", () => {
    const data = selectArrayViewData(arrayFrame);

    expect(data.operation).toBe("READ");
    expect(data.phase).toBe("ACTIVE");
  });

  it("handles different selected positions", () => {
    const frame00: FrameState = {
      ...arrayFrame,
      selectedCell: { row: 0, col: 0 },
    };
    const data = selectArrayViewData(frame00);

    expect(data.selectedRow).toBe(0);
    expect(data.selectedCol).toBe(0);
    expect(data.cells[0][0].isSelected).toBe(true);
    expect(data.cells[1][2].isSelected).toBe(false);
  });

  it("handles missing selectedCell", () => {
    const frameNoSelection: FrameState = {
      ...arrayFrame,
      selectedCell: undefined,
    };
    const data = selectArrayViewData(frameNoSelection);

    expect(data.selectedRow).toBe(0);
    expect(data.selectedCol).toBe(0);
  });
});

describe("Array View Current Flow", () => {
  it("detects current flowing when |I| > 0.1 µA", () => {
    const data = selectArrayViewData(arrayFrame);
    const selectedCell = data.cells[data.selectedRow][data.selectedCol];

    expect(Math.abs(selectedCell.iRram)).toBeGreaterThan(0.1);
  });

  it("detects no current when |I| < 0.1 µA", () => {
    const data = selectArrayViewData(noCurrentFrame);
    const selectedCell = data.cells[data.selectedRow][data.selectedCol];

    expect(Math.abs(selectedCell.iRram)).toBeLessThan(0.1);
  });

  it("unselected cells never have current", () => {
    const data = selectArrayViewData(arrayFrame);

    for (let r = 0; r < data.rows; r++) {
      for (let c = 0; c < data.cols; c++) {
        if (r !== data.selectedRow || c !== data.selectedCol) {
          expect(data.cells[r][c].iRram).toBe(0);
        }
      }
    }
  });
});

describe("Array View State Colors", () => {
  it("returns correct color for LRS", () => {
    const data = selectArrayViewData(arrayFrame);
    const selectedCell = data.cells[data.selectedRow][data.selectedCol];

    expect(selectedCell.state).toBe("LRS");
  });

  it("returns correct color for HRS", () => {
    const data = selectArrayViewData(noCurrentFrame);
    const selectedCell = data.cells[data.selectedRow][data.selectedCol];

    expect(selectedCell.state).toBe("HRS");
  });

  it("unselected cells default to PRISTINE", () => {
    const data = selectArrayViewData(arrayFrame);

    for (let r = 0; r < data.rows; r++) {
      for (let c = 0; c < data.cols; c++) {
        if (r !== data.selectedRow || c !== data.selectedCol) {
          expect(data.cells[r][c].state).toBe("PRISTINE");
        }
      }
    }
  });
});
