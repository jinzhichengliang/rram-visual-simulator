/**
 * S05 — Waveform + Explanation Engine tests.
 *
 * Tests:
 * 1. Waveform selector extracts time-series data correctly
 * 2. Explanation selector generates state-driven explanations
 * 3. Cursor sync — waveform sample matches FrameState
 * 4. Explanation token assertions — key facts are present
 * 5. G-04 text reversal — explanations change with polarity
 */
import { describe, it, expect } from "vitest";
import { selectWaveformData } from "../selectors/waveformSelector";
import { selectExplanation } from "../selectors/explanationSelector";
import type { FrameState } from "../../../../packages/contracts/types";

// Test fixtures
const pristineFrame: FrameState = {
  frameId: "f1",
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

const formingFrame: FrameState = {
  frameId: "f2",
  timeNs: 50,
  operation: "FORMING",
  phase: "ACTIVE",
  selectedCell: { row: 0, col: 0 },
  nodes: { wl: [1.8], bl: [3.5], sl: [0] },
  cell: {
    transistor: { vg: 1.8, vs: 0, vd: 3.5, on: true },
    rram: { v: 3.5, i: 50, r: 30000, state: "LRS", formingDone: true },
  },
  model: { fidelity: "F0", profileId: "test", profileVersion: "1.0.0", seed: 42 },
  checks: [],
};

const readFrame: FrameState = {
  frameId: "f3",
  timeNs: 100,
  operation: "READ",
  phase: "ACTIVE",
  selectedCell: { row: 0, col: 0 },
  nodes: { wl: [1.8], bl: [0.15], sl: [0] },
  cell: {
    transistor: { vg: 1.8, vs: 0, vd: 0.15, on: true },
    rram: { v: 0.15, i: 3.75, r: 40000, state: "LRS", formingDone: true },
  },
  model: { fidelity: "F0", profileId: "test", profileVersion: "1.0.0", seed: 42 },
  checks: [],
};

const readSenseFrame: FrameState = {
  frameId: "f4",
  timeNs: 150,
  operation: "READ",
  phase: "SENSE",
  selectedCell: { row: 0, col: 0 },
  nodes: { wl: [1.8], bl: [0.15], sl: [0] },
  cell: {
    transistor: { vg: 1.8, vs: 0, vd: 0.15, on: true },
    rram: { v: 0.15, i: 3.75, r: 40000, state: "LRS", formingDone: true },
  },
  sense: {
    currentUa: 3.75,
    referenceUa: 2.5,
    decision: "LRS",
    marginUa: 1.25,
  },
  model: { fidelity: "F0", profileId: "test", profileVersion: "1.0.0", seed: 42 },
  checks: [],
};

describe("Waveform Selector", () => {
  it("extracts time-series data from frame history", () => {
    const frames = [pristineFrame, formingFrame, readFrame];
    const data = selectWaveformData(frames);

    expect(data.points).toHaveLength(3);
    expect(data.points[0].timeNs).toBe(0);
    expect(data.points[1].timeNs).toBe(50);
    expect(data.points[2].timeNs).toBe(100);
  });

  it("extracts correct voltages for each frame", () => {
    const frames = [pristineFrame, formingFrame, readFrame];
    const data = selectWaveformData(frames);

    expect(data.points[0].wlVoltage).toBe(0);
    expect(data.points[0].blVoltage).toBe(0);

    expect(data.points[1].wlVoltage).toBe(1.8);
    expect(data.points[1].blVoltage).toBe(3.5);

    expect(data.points[2].wlVoltage).toBe(1.8);
    expect(data.points[2].blVoltage).toBe(0.15);
  });

  it("extracts correct device measurements", () => {
    const frames = [pristineFrame, formingFrame];
    const data = selectWaveformData(frames);

    expect(data.points[0].vRram).toBe(0);
    expect(data.points[0].iRram).toBe(0);
    expect(data.points[0].state).toBe("PRISTINE");

    expect(data.points[1].vRram).toBe(3.5);
    expect(data.points[1].iRram).toBe(50);
    expect(data.points[1].state).toBe("LRS");
  });

  it("tracks current frame correctly", () => {
    const frames = [pristineFrame, formingFrame, readFrame];
    const data = selectWaveformData(frames, "f2");

    expect(data.currentFrameId).toBe("f2");
    expect(data.currentTimeNs).toBe(50);
  });

  it("defaults to last frame when no currentFrameId", () => {
    const frames = [pristineFrame, formingFrame, readFrame];
    const data = selectWaveformData(frames);

    expect(data.currentFrameId).toBe("f3");
    expect(data.currentTimeNs).toBe(100);
  });
});

describe("Explanation Selector", () => {
  it("generates voltage explanation for PRISTINE state", () => {
    const cards = selectExplanation(pristineFrame, null);

    expect(cards.voltage).toContain("WL=0V");
    expect(cards.voltage).toContain("BL=0V");
    expect(cards.voltage).toContain("无有效偏置");
  });

  it("generates voltage explanation for FORMING operation", () => {
    const cards = selectExplanation(formingFrame, pristineFrame);

    expect(cards.voltage).toContain("WL=1.8V");
    expect(cards.voltage).toContain("BL=3.5V");
    expect(cards.voltage).toContain("V_RRAM = 3.50V");
    expect(cards.voltage).toContain("Forming");
  });

  it("generates current explanation when transistor OFF", () => {
    const cards = selectExplanation(pristineFrame, null);

    expect(cards.current).toContain("NMOS 截止");
    expect(cards.current).toContain("无有效电流路径");
  });

  it("generates current explanation when transistor ON", () => {
    const cards = selectExplanation(formingFrame, pristineFrame);

    expect(cards.current).toContain("BL → RRAM → NMOS → SL");
    expect(cards.current).toContain("50.0 µA");
  });

  it("generates physics explanation for FORMING with state transition", () => {
    // formingFrame has state=LRS, prevFrame (pristineFrame) has state=PRISTINE
    const cards = selectExplanation(formingFrame, pristineFrame);

    expect(cards.physics).toContain("Forming 完成");
    expect(cards.physics).toContain("PRISTINE → LRS");
  });

  it("generates physics explanation for READ (non-destructive)", () => {
    // readFrame has state=LRS, prevFrame should also have state=LRS (no change)
    const prevReadFrame = { ...readFrame, cell: { ...readFrame.cell, rram: { ...readFrame.cell.rram, state: "LRS" as const } } };
    const cards = selectExplanation(readFrame, prevReadFrame);

    expect(cards.physics).toContain("低于写入阈值");
    expect(cards.physics).toContain("非破坏性读取");
  });

  it("generates sense explanation when sense data present", () => {
    const cards = selectExplanation(readSenseFrame, null);

    expect(cards.sense).toContain("I_read = 3.75 µA");
    expect(cards.sense).toContain("I_ref = 2.50 µA");
    expect(cards.sense).toContain("Margin = 1.25 µA");
    expect(cards.sense).toContain("LRS");
  });

  it("generates sense explanation when no sense data", () => {
    const cards = selectExplanation(readFrame, null);

    expect(cards.sense).toContain("尚未进入 SENSE");
  });

  it("generates sense explanation for non-READ operations", () => {
    const cards = selectExplanation(formingFrame, pristineFrame);

    expect(cards.sense).toContain("不执行 Sense");
  });
});

describe("Cursor Sync", () => {
  it("waveform sample matches FrameState at cursor", () => {
    const frames = [pristineFrame, formingFrame, readFrame];
    const data = selectWaveformData(frames, "f2");

    // Find the frame at cursor
    const frameAtCursor = frames.find((f) => f.frameId === data.currentFrameId);
    expect(frameAtCursor).toBeDefined();

    // Verify waveform point matches frame
    const pointAtCursor = data.points.find((p) => p.frameId === data.currentFrameId);
    expect(pointAtCursor).toBeDefined();
    expect(pointAtCursor!.vRram).toBe(frameAtCursor!.cell.rram.v);
    expect(pointAtCursor!.iRram).toBe(frameAtCursor!.cell.rram.i);
  });

  it("explanation matches frame at cursor", () => {
    const frames = [pristineFrame, formingFrame, readFrame];
    const data = selectWaveformData(frames, "f2");

    const frameAtCursor = frames.find((f) => f.frameId === data.currentFrameId)!;
    const prevFrameAtCursor = pristineFrame; // frame before f2 is f1 (pristine)
    const explanation = selectExplanation(frameAtCursor, prevFrameAtCursor);

    // Explanation should be for FORMING operation with state transition
    expect(explanation.voltage).toContain("Forming");
    expect(explanation.physics).toContain("Forming 完成");
  });
});

describe("Explanation Token Assertions", () => {
  it("voltage explanation contains key tokens", () => {
    const cards = selectExplanation(formingFrame, pristineFrame);

    // Must contain voltage values
    expect(cards.voltage).toMatch(/WL=[\d.]+V/);
    expect(cards.voltage).toMatch(/BL=[\d.]+V/);
    expect(cards.voltage).toMatch(/V_RRAM = [\d.]+V/);
  });

  it("current explanation contains path and magnitude", () => {
    const cards = selectExplanation(formingFrame, pristineFrame);

    // Must contain current path
    expect(cards.current).toMatch(/BL → RRAM → NMOS → SL/);
    // Must contain current magnitude
    expect(cards.current).toMatch(/[\d.]+ µA/);
  });

  it("physics explanation contains state transition when state actually changed", () => {
    // formingFrame state=LRS, pristineFrame state=PRISTINE → actual transition
    const cards = selectExplanation(formingFrame, pristineFrame);

    // Must contain state transition
    expect(cards.physics).toMatch(/PRISTINE → LRS|HRS → LRS|LRS → HRS/);
  });

  it("physics explanation shows no change when state is same", () => {
    // Same state in both frames → no transition
    const sameFrame = { ...readFrame, cell: { ...readFrame.cell, rram: { ...readFrame.cell.rram, state: "LRS" as const } } };
    const cards = selectExplanation(readFrame, sameFrame);

    // Should NOT contain state transition
    expect(cards.physics).not.toMatch(/PRISTINE → LRS|HRS → LRS|LRS → HRS/);
    // Should mention state is maintained
    expect(cards.physics).toContain("保持");
  });

  it("sense explanation contains decision", () => {
    const cards = selectExplanation(readSenseFrame, null);

    // Must contain sense decision
    expect(cards.sense).toMatch(/LRS|HRS/);
  });
});

describe("G-04 Polarity Reversal Text", () => {
  it("voltage explanation reflects polarity", () => {
    // Positive polarity
    const posFrame = formingFrame;
    const posCards = selectExplanation(posFrame, pristineFrame);
    expect(posCards.voltage).toContain("正向");

    // Negative polarity (simulated by negative V_RRAM)
    const negFrame: FrameState = {
      ...formingFrame,
      cell: {
        ...formingFrame.cell,
        rram: { ...formingFrame.cell.rram, v: -3.5 },
      },
    };
    const negCards = selectExplanation(negFrame, pristineFrame);
    expect(negCards.voltage).toContain("反向");
  });

  it("current explanation reflects direction", () => {
    // Positive current
    const posCards = selectExplanation(formingFrame, pristineFrame);
    expect(posCards.current).toContain("BL → RRAM → NMOS → SL");

    // Negative current (simulated)
    const negFrame: FrameState = {
      ...formingFrame,
      cell: {
        ...formingFrame.cell,
        rram: { ...formingFrame.cell.rram, i: -50 },
      },
    };
    const negCards = selectExplanation(negFrame, pristineFrame);
    expect(negCards.current).toContain("SL → NMOS → RRAM → BL");
  });
});
