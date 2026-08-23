/**
 * S18: Filament View Selector Tests
 *
 * Tests:
 * 1. F0 mode: Conceptual visualization
 * 2. F1 mode: Parameterized visualization
 * 3. State-dependent visualization
 * 4. Observable extraction
 */
import { describe, it, expect } from "vitest";
import { selectFilamentViewData } from "./filamentSelector";
import type { FrameState } from "../../../../packages/contracts/types";

// Test fixtures
const f0LrsFrame: FrameState = {
  frameId: "f0-lrs",
  timeNs: 100,
  operation: "SET",
  phase: "ACTIVE",
  selectedCell: { row: 0, col: 0 },
  nodes: { wl: [1.8], bl: [2.0], sl: [0] },
  cell: {
    transistor: { vg: 1.8, vs: 0, vd: 2.0, on: true },
    rram: { v: 2.0, i: 50, r: 30000, state: "LRS", formingDone: true },
  },
  model: { fidelity: "F0", profileId: "test", profileVersion: "1.0.0", seed: 42 },
  checks: [],
};

const f1LrsFrame: FrameState = {
  frameId: "f1-lrs",
  timeNs: 100,
  operation: "SET",
  phase: "ACTIVE",
  selectedCell: { row: 0, col: 0 },
  nodes: { wl: [1.8], bl: [2.0], sl: [0] },
  cell: {
    transistor: { vg: 1.8, vs: 0, vd: 2.0, on: true },
    rram: {
      v: 2.0,
      i: 50,
      r: 30000,
      state: "LRS",
      formingDone: true,
      gapNm: 0.5,
      filamentProxy: 0.9,
      temperatureK: 350,
    },
  },
  model: { fidelity: "F1", profileId: "test", profileVersion: "1.0.0", seed: 42 },
  checks: [],
};

const f1HrsFrame: FrameState = {
  frameId: "f1-hrs",
  timeNs: 200,
  operation: "RESET",
  phase: "ACTIVE",
  selectedCell: { row: 0, col: 0 },
  nodes: { wl: [1.8], bl: [-2.0], sl: [0] },
  cell: {
    transistor: { vg: 1.8, vs: 0, vd: -2.0, on: true },
    rram: {
      v: -2.0,
      i: -0.5,
      r: 1000000,
      state: "HRS",
      formingDone: true,
      gapNm: 8.0,
      filamentProxy: 0.1,
      temperatureK: 320,
    },
  },
  model: { fidelity: "F1", profileId: "test", profileVersion: "1.0.0", seed: 42 },
  checks: [],
};

describe("Filament View Selector", () => {
  describe("F0 Mode", () => {
    it("extracts state correctly", () => {
      const data = selectFilamentViewData(f0LrsFrame);

      expect(data.state).toBe("LRS");
      expect(data.fidelity).toBe("F0");
      expect(data.formingDone).toBe(true);
    });

    it("sets conceptual visualization parameters", () => {
      const data = selectFilamentViewData(f0LrsFrame);

      expect(data.gapNm).toBeNull();
      expect(data.filamentProxy).toBeNull();
      expect(data.temperatureK).toBeNull();
      expect(data.showGap).toBe(false);
    });

    it("sets LRS visualization", () => {
      const data = selectFilamentViewData(f0LrsFrame);

      expect(data.filamentWidth).toBeGreaterThan(0.5);
      expect(data.filamentOpacity).toBeGreaterThan(0.7);
      expect(data.filamentColor).toBe("#4ade80"); // Green
    });
  });

  describe("F1 Mode", () => {
    it("extracts observables correctly", () => {
      const data = selectFilamentViewData(f1LrsFrame);

      expect(data.gapNm).toBe(0.5);
      expect(data.filamentProxy).toBe(0.9);
      expect(data.temperatureK).toBe(350);
    });

    it("enables gap visualization", () => {
      const data = selectFilamentViewData(f1LrsFrame);

      expect(data.showGap).toBe(true);
      expect(data.gapSize).toBeGreaterThan(0);
      expect(data.gapSize).toBeLessThanOrEqual(1);
    });

    it("sets LRS visualization for small gap", () => {
      const data = selectFilamentViewData(f1LrsFrame);

      expect(data.filamentWidth).toBeGreaterThan(0.5);
      expect(data.filamentOpacity).toBeGreaterThan(0.7);
      expect(data.filamentColor).toBe("#4ade80"); // Green
    });

    it("sets HRS visualization for large gap", () => {
      const data = selectFilamentViewData(f1HrsFrame);

      expect(data.filamentWidth).toBeLessThan(0.5);
      expect(data.filamentOpacity).toBeLessThan(0.5);
      expect(data.filamentColor).toBe("#f87171"); // Red
    });

    it("normalizes gap size correctly", () => {
      const data = selectFilamentViewData(f1LrsFrame);

      // gapNm = 0.5, maxGapNm = 10.0
      expect(data.gapSize).toBeCloseTo(0.05, 2);
    });
  });

  describe("State Transitions", () => {
    it("handles PRISTINE state", () => {
      const pristineFrame: FrameState = {
        ...f0LrsFrame,
        cell: {
          ...f0LrsFrame.cell,
          rram: { ...f0LrsFrame.cell.rram, state: "PRISTINE", formingDone: false },
        },
      };

      const data = selectFilamentViewData(pristineFrame);

      expect(data.state).toBe("PRISTINE");
      expect(data.formingDone).toBe(false);
      expect(data.filamentColor).toBe("#6b7280"); // Gray
    });

    it("handles intermediate filament proxy", () => {
      const intermediateFrame: FrameState = {
        ...f1LrsFrame,
        cell: {
          ...f1LrsFrame.cell,
          rram: { ...f1LrsFrame.cell.rram, filamentProxy: 0.5 },
        },
      };

      const data = selectFilamentViewData(intermediateFrame);

      expect(data.filamentColor).toBe("#fbbf24"); // Yellow
    });
  });
});
