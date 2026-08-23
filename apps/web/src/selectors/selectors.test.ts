/**
 * S04 — Selector tests for Device View and Cell View.
 *
 * Tests that selectors:
 * 1. Extract correct data from FrameState
 * 2. Do not perform physics calculations
 * 3. Handle all states correctly
 */
import { describe, it, expect } from "vitest";
import { selectDeviceViewData } from "../selectors/deviceSelector";
import { selectCellViewData } from "../selectors/cellSelector";
import type { FrameState } from "../../../../packages/contracts/types";

// Test fixture: PRISTINE state
const pristineFrame: FrameState = {
  frameId: "test-001",
  timeNs: 0,
  operation: "PRISTINE",
  phase: "PREPARE",
  selectedCell: { row: 0, col: 0 },
  nodes: { wl: [0], bl: [0], sl: [0] },
  cell: {
    transistor: { vg: 0, vs: 0, vd: 0, on: false },
    rram: { v: 0, i: 0, r: 1e9, state: "PRISTINE", formingDone: false },
  },
  model: { fidelity: "F0", profileId: "test", profileVersion: "1.0.0", seed: 42 },
  checks: [],
};

// Test fixture: LRS state with current
const lrsFrame: FrameState = {
  frameId: "test-002",
  timeNs: 100,
  operation: "SET",
  phase: "ACTIVE",
  selectedCell: { row: 0, col: 0 },
  nodes: { wl: [1.8], bl: [2.0], sl: [0] },
  cell: {
    transistor: { vg: 1.8, vs: 0, vd: 2.0, on: true },
    rram: { v: 2.0, i: 50, r: 40000, state: "LRS", formingDone: true },
  },
  model: { fidelity: "F0", profileId: "test", profileVersion: "1.0.0", seed: 42 },
  checks: [],
};

// Test fixture: HRS state
const hrsFrame: FrameState = {
  frameId: "test-003",
  timeNs: 200,
  operation: "RESET",
  phase: "ACTIVE",
  selectedCell: { row: 0, col: 0 },
  nodes: { wl: [1.8], bl: [-2.0], sl: [0] },
  cell: {
    transistor: { vg: 1.8, vs: 0, vd: -2.0, on: true },
    rram: { v: -2.0, i: -4, r: 1e6, state: "HRS", formingDone: true },
  },
  model: { fidelity: "F0", profileId: "test", profileVersion: "1.0.0", seed: 42 },
  checks: [],
};

describe("Device View Selector", () => {
  it("extracts PRISTINE state correctly", () => {
    const data = selectDeviceViewData(pristineFrame);
    expect(data.state).toBe("PRISTINE");
    expect(data.vRram).toBe(0);
    expect(data.iRram).toBe(0);
    expect(data.resistance).toBe(1e9);
    expect(data.currentFlowing).toBe(false);
    expect(data.formingDone).toBe(false);
  });

  it("extracts LRS state with current correctly", () => {
    const data = selectDeviceViewData(lrsFrame);
    expect(data.state).toBe("LRS");
    expect(data.vRram).toBe(2.0);
    expect(data.iRram).toBe(50);
    expect(data.resistance).toBe(40000);
    expect(data.currentFlowing).toBe(true);
    expect(data.currentDirection).toBe("forward");
    expect(data.polarityPositive).toBe(true);
    expect(data.formingDone).toBe(true);
  });

  it("extracts HRS state with negative voltage correctly", () => {
    const data = selectDeviceViewData(hrsFrame);
    expect(data.state).toBe("HRS");
    expect(data.vRram).toBe(-2.0);
    expect(data.iRram).toBe(-4);
    expect(data.currentFlowing).toBe(true);
    expect(data.currentDirection).toBe("reverse");
    expect(data.polarityPositive).toBe(false);
  });

  it("detects compliance when current near limit", () => {
    const data = selectDeviceViewData(lrsFrame);
    expect(data.complianceActive).toBe(true); // 50 µA near 50 µA limit
  });

  it("does not detect compliance when current low", () => {
    const data = selectDeviceViewData(hrsFrame);
    expect(data.complianceActive).toBe(false); // -4 µA far from limit
  });

  it("preserves operation and phase", () => {
    const data = selectDeviceViewData(lrsFrame);
    expect(data.operation).toBe("SET");
    expect(data.phase).toBe("ACTIVE");
  });

  it("preserves fidelity level", () => {
    const data = selectDeviceViewData(lrsFrame);
    expect(data.fidelity).toBe("F0");
  });
});

describe("Cell View Selector", () => {
  it("extracts node voltages correctly", () => {
    const data = selectCellViewData(lrsFrame);
    expect(data.wlVoltage).toBe(1.8);
    expect(data.blVoltage).toBe(2.0);
    expect(data.slVoltage).toBe(0);
  });

  it("extracts transistor state correctly", () => {
    const data = selectCellViewData(lrsFrame);
    expect(data.transistorOn).toBe(true);
    expect(data.vgs).toBe(1.8); // 1.8 - 0
    expect(data.vds).toBe(2.0); // 2.0 - 0
  });

  it("detects current direction BL-to-SL", () => {
    const data = selectCellViewData(lrsFrame);
    expect(data.currentFlowing).toBe(true);
    expect(data.currentDirection).toBe("BL-to-SL");
  });

  it("detects current direction SL-to-BL", () => {
    const data = selectCellViewData(hrsFrame);
    expect(data.currentFlowing).toBe(true);
    expect(data.currentDirection).toBe("SL-to-BL");
  });

  it("detects no current when transistor off", () => {
    const data = selectCellViewData(pristineFrame);
    expect(data.currentFlowing).toBe(false);
    expect(data.currentDirection).toBe("none");
    expect(data.transistorOn).toBe(false);
  });

  it("preserves operation and phase", () => {
    const data = selectCellViewData(lrsFrame);
    expect(data.operation).toBe("SET");
    expect(data.phase).toBe("ACTIVE");
  });

  it("throws error when selectedCell is missing", () => {
    const frameWithoutCell = { ...lrsFrame, selectedCell: undefined };
    expect(() => selectCellViewData(frameWithoutCell as FrameState)).toThrow();
  });
});

describe("Cross-View Consistency", () => {
  it("Device and Cell selectors return same V_RRAM", () => {
    const deviceData = selectDeviceViewData(lrsFrame);
    const cellData = selectCellViewData(lrsFrame);
    expect(deviceData.vRram).toBe(cellData.vRram);
  });

  it("Device and Cell selectors return same I_RRAM", () => {
    const deviceData = selectDeviceViewData(lrsFrame);
    const cellData = selectCellViewData(lrsFrame);
    expect(deviceData.iRram).toBe(cellData.iRram);
  });

  it("Device and Cell selectors return same state", () => {
    const deviceData = selectDeviceViewData(lrsFrame);
    const cellData = selectCellViewData(lrsFrame);
    expect(deviceData.state).toBe(cellData.state);
  });

  it("Device and Cell selectors return same resistance", () => {
    const deviceData = selectDeviceViewData(lrsFrame);
    const cellData = selectCellViewData(lrsFrame);
    expect(deviceData.resistance).toBe(cellData.resistance);
  });

  it("Device and Cell selectors agree on current flowing", () => {
    const deviceData = selectDeviceViewData(lrsFrame);
    const cellData = selectCellViewData(lrsFrame);
    expect(deviceData.currentFlowing).toBe(cellData.currentFlowing);
  });

  it("Device and Cell selectors agree on compliance", () => {
    const deviceData = selectDeviceViewData(lrsFrame);
    const cellData = selectCellViewData(lrsFrame);
    expect(deviceData.complianceActive).toBe(cellData.complianceActive);
  });
});
