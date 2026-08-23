/**
 * S01 — Schema validation tests for TypeScript.
 *
 * Verifies that canonical fixtures can be parsed and validated.
 */
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";
import {
  validateFrameState,
  type FrameState,
  type DeviceProfile,
} from "../../../packages/contracts/types";

const FIXTURES_DIR = resolve(__dirname, "../../../packages/contracts/fixtures");

describe("S01 Schema Validation", () => {
  describe("Valid Fixtures", () => {
    it("valid-frame-pristine.json must parse", () => {
      const data = readFileSync(
        resolve(FIXTURES_DIR, "valid-frame-pristine.json"),
        "utf-8"
      );
      const frame: FrameState = JSON.parse(data);
      expect(validateFrameState(frame)).toBe(true);
      expect(frame.frameId).toBe("frame-001");
      expect(frame.timeNs).toBe(0);
      expect(frame.operation).toBe("PRISTINE");
      expect(frame.cell.rram.state).toBe("PRISTINE");
    });

    it("valid-profile.json must parse", () => {
      const data = readFileSync(
        resolve(FIXTURES_DIR, "valid-profile.json"),
        "utf-8"
      );
      const profile: DeviceProfile = JSON.parse(data);
      expect(profile.id).toBe("bipolar_teaching_v1");
      expect(profile.version).toBe("1.0.0");
      expect(profile.setPolarity).toBe("V_RRAM > 0");
      expect(profile.logicMap.LRS).toBe(1);
    });
  });

  describe("Invalid Fixtures", () => {
    it("negative timeNs must fail validation", () => {
      const data = readFileSync(
        resolve(FIXTURES_DIR, "invalid-frame-negative-time.json"),
        "utf-8"
      );
      const frame = JSON.parse(data);
      expect(validateFrameState(frame)).toBe(false);
    });

    it("missing required fields must fail validation", () => {
      const frame = {
        frameId: "test",
        timeNs: 0,
        // missing operation, phase, nodes, cell, model, checks
      };
      expect(validateFrameState(frame)).toBe(false);
    });

    it("invalid operation type must fail validation", () => {
      const frame = {
        frameId: "test",
        timeNs: 0,
        operation: "INVALID_OP",
        phase: "PREPARE",
        nodes: { wl: [0], bl: [0], sl: [0] },
        cell: {
          transistor: { vg: 0, vs: 0, vd: 0, on: false },
          rram: { v: 0, i: 0, r: 1000, state: "PRISTINE", formingDone: false },
        },
        model: {
          fidelity: "F0",
          profileId: "test",
          profileVersion: "1.0.0",
          seed: 42,
        },
        checks: [],
      };
      expect(validateFrameState(frame)).toBe(false);
    });
  });

  describe("Type Safety", () => {
    it("FrameState type must be correctly inferred", () => {
      const frame: FrameState = {
        frameId: "test",
        timeNs: 0,
        operation: "READ",
        phase: "ACTIVE",
        nodes: { wl: [0], bl: [0], sl: [0] },
        cell: {
          transistor: { vg: 0, vs: 0, vd: 0, on: true },
          rram: { v: 0.1, i: 10, r: 10000, state: "HRS", formingDone: true },
        },
        model: {
          fidelity: "F0",
          profileId: "test",
          profileVersion: "1.0.0",
          seed: 42,
        },
        checks: [],
      };
      expect(frame.operation).toBe("READ");
      expect(frame.cell.rram.state).toBe("HRS");
    });
  });
});
