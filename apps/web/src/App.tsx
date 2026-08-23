/**
 * RRAM Visual Simulator — Root Application Component (V0.2)
 *
 * Integrates all views, selectors, and controls.
 * Includes 4×4 array support.
 */
import { useState, useCallback } from "react";
import type { FrameState, OperationType } from "../../../packages/contracts/types";
import { ControlPanel } from "./components/ControlPanel";
import { DeviceView } from "./views/DeviceView";
import { CellView } from "./views/CellView";
import { WaveformView } from "./views/WaveformView";
import { ExplanationView } from "./views/ExplanationView";
import { ArrayView } from "./views/ArrayView";
import { selectDeviceViewData } from "./selectors/deviceSelector";
import { selectCellViewData } from "./selectors/cellSelector";
import { selectWaveformData } from "./selectors/waveformSelector";
import { selectExplanation } from "./selectors/explanationSelector";
import { selectArrayViewData } from "./selectors/arraySelector";
import * as api from "./api/client";

// Initial frame for empty state
const initialFrame: FrameState = {
  frameId: "initial",
  timeNs: 0,
  operation: "PRISTINE",
  phase: "PREPARE",
  selectedCell: { row: 0, col: 0 },
  nodes: { wl: [0], bl: [0], sl: [0] },
  cell: {
    transistor: { vg: 0, vs: 0, vd: 0, on: false },
    rram: { v: 0, i: 0, r: 1e9, state: "PRISTINE", formingDone: false },
  },
  model: { fidelity: "F0", profileId: "bipolar_teaching_v1", profileVersion: "1.0.0", seed: 42 },
  checks: [],
};

function App() {
  const [frames, setFrames] = useState<FrameState[]>([]);
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedCell, setSelectedCell] = useState({ row: 0, col: 0 });

  const currentFrame = frames[currentFrameIndex] || initialFrame;

  // Execute operation on selected cell
  const executeOperation = useCallback(async (operation: string) => {
    try {
      const newFrames = await api.executeOperation(operation as OperationType, selectedCell);
      setFrames((prev) => [...prev, ...newFrames]);
      setCurrentFrameIndex((prev) => prev + newFrames.length);
    } catch (error) {
      console.error("Operation failed:", error);
    }
  }, []);

  // Reset simulation
  const resetSimulation = useCallback(async () => {
    try {
      await api.resetSimulation();
      setFrames([]);
      setCurrentFrameIndex(0);
      setIsRunning(false);
    } catch (error) {
      console.error("Reset failed:", error);
    }
  }, []);

  // Step back
  const stepBack = useCallback(() => {
    if (currentFrameIndex > 0) {
      setCurrentFrameIndex((prev) => prev - 1);
    }
  }, [currentFrameIndex]);

  // Play/Pause
  const togglePlay = useCallback(() => {
    setIsRunning((prev) => !prev);
  }, []);

  // Selectors
  const deviceData = selectDeviceViewData(currentFrame);
  const cellData = selectCellViewData(currentFrame);
  const waveformData = selectWaveformData(frames, currentFrame.frameId);
  const prevFrame = currentFrameIndex > 0 ? frames[currentFrameIndex - 1] : null;
  const explanationCards = selectExplanation(currentFrame, prevFrame);
  const arrayData = selectArrayViewData(currentFrame);

  // Handle cell click in array
  const handleCellClick = useCallback((row: number, col: number) => {
    setSelectedCell({ row, col });
  }, []);

  return (
    <div style={{ fontFamily: "'SF Mono', 'Cascadia Code', 'Fira Code', monospace", background: "#0f1117", color: "#e1e4ed", minHeight: "100vh" }}>
      {/* Header */}
      <header style={{ background: "#1a1d27", borderBottom: "1px solid #2e3348", padding: "12px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <h1 style={{ fontSize: "16px", fontWeight: 600, margin: 0 }}>RRAM Visual Simulator</h1>
          <span style={{ background: "#4a6ae0", color: "white", padding: "2px 8px", borderRadius: "4px", fontSize: "11px" }}>V0.1 · F0 Teaching Model</span>
          <span style={{ display: "inline-block", padding: "2px 6px", borderRadius: "3px", fontSize: "9px", fontWeight: 700, background: "#422006", color: "#fb923c" }}>CONCEPTUAL</span>
        </div>
        <div style={{ fontSize: "12px", color: "#8b90a5" }}>
          {currentFrame.operation} · {currentFrame.phase} · Frame #{currentFrameIndex + 1}
        </div>
      </header>

      {/* Control Panel */}
      <ControlPanel
        onForming={() => executeOperation("FORMING")}
        onRead={() => executeOperation("READ")}
        onSet={() => executeOperation("SET")}
        onReset={() => executeOperation("RESET")}
        onStep={stepBack}
        onPlay={togglePlay}
        onPause={togglePlay}
        onResetAll={resetSimulation}
        isRunning={isRunning}
        canStep={currentFrameIndex > 0}
      />

      {/* Timeline */}
      <div style={{ background: "#1a1d27", padding: "8px 24px", display: "flex", alignItems: "center", gap: "12px", borderBottom: "1px solid #2e3348" }}>
        <span style={{ fontSize: "11px", color: "#8b90a5" }}>Timeline</span>
        <input
          type="range"
          min="0"
          max={Math.max(0, frames.length - 1)}
          value={currentFrameIndex}
          onChange={(e) => setCurrentFrameIndex(parseInt(e.target.value))}
          style={{ flex: 1 }}
        />
        <span style={{ fontSize: "11px", color: "#8b90a5", minWidth: "100px", textAlign: "right" }}>
          Frame {currentFrameIndex + 1} / {frames.length}
        </span>
      </div>

      {/* Main Views */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1px", background: "#2e3348" }}>
        {/* Device View */}
        <div style={{ background: "#1a1d27", padding: "16px" }}>
          <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "1.5px", color: "#8b90a5", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#4ade80" }}></span>
            Device View — RRAM 两端发生了什么
          </div>
          <DeviceView data={deviceData} />
        </div>

        {/* Cell View */}
        <div style={{ background: "#1a1d27", padding: "16px" }}>
          <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "1.5px", color: "#8b90a5", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#4ade80" }}></span>
            1T1R Cell View — BL / WL / SL 如何控制一个 bit
          </div>
          <CellView data={cellData} />
        </div>

        {/* Array View */}
        <div style={{ background: "#1a1d27", padding: "16px" }}>
          <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "1.5px", color: "#8b90a5", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#4ade80" }}></span>
            Array View — 4×4 阵列选择
          </div>
          <ArrayView data={arrayData} onCellClick={handleCellClick} />
        </div>

        {/* Waveform View */}
        <div style={{ background: "#1a1d27", padding: "16px", gridColumn: "1 / -1" }}>
          <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "1.5px", color: "#8b90a5", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#4ade80" }}></span>
            Waveform View — 时间维度上的因果证据
          </div>
          <WaveformView data={waveformData} />
        </div>

        {/* Explanation */}
        <div style={{ background: "#1a1d27", padding: "16px", gridColumn: "1 / -1" }}>
          <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "1.5px", color: "#8b90a5", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#4ade80" }}></span>
            三问解释器 — 每一步同时回答
          </div>
          <ExplanationView cards={explanationCards} />
        </div>
      </div>
    </div>
  );
}

export default App;
