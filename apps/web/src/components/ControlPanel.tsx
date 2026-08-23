/**
 * Control Panel — Global simulation controls.
 *
 * Provides:
 * - Step: Execute one semantic step
 * - Play/Pause: Auto-advance through frames
 * - Reset: Return to initial state
 * - Operation buttons: Forming, Read, Set, Reset
 */
import React from "react";

interface ControlPanelProps {
  onForming: () => void;
  onRead: () => void;
  onSet: () => void;
  onReset: () => void;
  onStep: () => void;
  onPlay: () => void;
  onPause: () => void;
  onResetAll: () => void;
  isRunning: boolean;
  canStep: boolean;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  onForming,
  onRead,
  onSet,
  onReset,
  onStep,
  onPlay,
  onPause,
  onResetAll,
  isRunning,
  canStep,
}) => {
  return (
    <div style={{
      background: "#1a1d27",
      padding: "12px 24px",
      display: "flex",
      alignItems: "center",
      gap: "12px",
      flexWrap: "wrap",
      borderBottom: "1px solid #2e3348",
    }}>
      {/* Operation buttons */}
      <button
        onClick={onForming}
        style={{
          padding: "6px 16px",
          border: "1px solid #fb923c",
          borderRadius: "6px",
          background: "#242836",
          color: "#fb923c",
          fontFamily: "inherit",
          fontSize: "12px",
          cursor: "pointer",
        }}
      >
        Forming
      </button>
      <button
        onClick={onRead}
        style={{
          padding: "6px 16px",
          border: "1px solid #22d3ee",
          borderRadius: "6px",
          background: "#242836",
          color: "#22d3ee",
          fontFamily: "inherit",
          fontSize: "12px",
          cursor: "pointer",
        }}
      >
        Read
      </button>
      <button
        onClick={onSet}
        style={{
          padding: "6px 16px",
          border: "1px solid #4ade80",
          borderRadius: "6px",
          background: "#242836",
          color: "#4ade80",
          fontFamily: "inherit",
          fontSize: "12px",
          cursor: "pointer",
        }}
      >
        Set (Write 1)
      </button>
      <button
        onClick={onReset}
        style={{
          padding: "6px 16px",
          border: "1px solid #f87171",
          borderRadius: "6px",
          background: "#242836",
          color: "#f87171",
          fontFamily: "inherit",
          fontSize: "12px",
          cursor: "pointer",
        }}
      >
        Reset (Write 0)
      </button>

      <div style={{ width: "1px", height: "24px", background: "#2e3348" }} />

      {/* Playback controls */}
      <button
        onClick={onStep}
        disabled={!canStep}
        style={{
          padding: "6px 16px",
          border: "1px solid #2e3348",
          borderRadius: "6px",
          background: "#242836",
          color: "#e1e4ed",
          fontFamily: "inherit",
          fontSize: "12px",
          cursor: canStep ? "pointer" : "not-allowed",
          opacity: canStep ? 1 : 0.4,
        }}
      >
        ◂ Step
      </button>
      {isRunning ? (
        <button
          onClick={onPause}
          style={{
            padding: "6px 16px",
            border: "1px solid #2e3348",
            borderRadius: "6px",
            background: "#242836",
            color: "#e1e4ed",
            fontFamily: "inherit",
            fontSize: "12px",
            cursor: "pointer",
          }}
        >
          ⏸ Pause
        </button>
      ) : (
        <button
          onClick={onPlay}
          style={{
            padding: "6px 16px",
            border: "1px solid #2e3348",
            borderRadius: "6px",
            background: "#242836",
            color: "#e1e4ed",
            fontFamily: "inherit",
            fontSize: "12px",
            cursor: "pointer",
          }}
        >
          ▶ Play
        </button>
      )}
      <button
        onClick={onResetAll}
        style={{
          padding: "6px 16px",
          border: "1px solid #2e3348",
          borderRadius: "6px",
          background: "#242836",
          color: "#e1e4ed",
          fontFamily: "inherit",
          fontSize: "12px",
          cursor: "pointer",
        }}
      >
        ↺ Reset All
      </button>
    </div>
  );
};
