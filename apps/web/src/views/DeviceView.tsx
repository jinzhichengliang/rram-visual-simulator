/**
 * Device View Component — Visualizes RRAM device state.
 *
 * Displays:
 * - Top/bottom electrodes
 * - Switching layer
 * - Filament visualization (conceptual)
 * - V_RRAM polarity indicator
 * - I_RRAM magnitude and direction
 * - R value
 * - State label (PRISTINE/HRS/LRS)
 * - Compliance indicator
 *
 * This component ONLY renders data from the selector.
 * It does NOT modify state or perform physics calculations.
 */
import React from "react";
import type { DeviceViewData } from "../selectors/deviceSelector";

interface DeviceViewProps {
  data: DeviceViewData;
}

export const DeviceView: React.FC<DeviceViewProps> = ({ data }) => {
  const {
    vRram,
    iRram,
    resistance,
    state,
    polarityPositive,
    currentFlowing,
    currentDirection,
    complianceActive,
    operation,
    phase,
    fidelity,
  } = data;

  // Visual parameters
  const width = 400;
  const height = 220;

  // Filament visualization (conceptual)
  const filamentOpacity = state === "LRS" ? 0.8 : state === "HRS" ? 0.2 : 0.4;
  const filamentColor = state === "LRS" ? "#4ade80" : state === "HRS" ? "#f87171" : "#6b7280";

  // Current flow animation
  const currentWidth = Math.min(4, Math.max(1, Math.abs(iRram) / 10));
  const currentColor = currentDirection === "forward" ? "#4ade80" : "#f87171";

  // Voltage polarity arrow
  const polarityArrow = polarityPositive ? "↓" : vRram < 0 ? "↑" : "—";
  const polarityColor = polarityPositive ? "#4ade80" : vRram < 0 ? "#f87171" : "#6b7280";

  // Resistance formatting
  const rDisplay = resistance >= 1e6
    ? `${(resistance / 1e6).toFixed(1)} MΩ`
    : `${(resistance / 1e3).toFixed(1)} kΩ`;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      {/* Background */}
      <rect width={width} height={height} fill="#0f1117" rx="8" />

      {/* Top electrode (BL) */}
      <rect x="150" y="20" width="100" height="16" rx="3" fill="#4b5563" stroke="#6b7280" strokeWidth="1" />
      <text x="200" y="14" textAnchor="middle" fill="#9ca3af" fontSize="10">
        BL (Top Electrode)
      </text>

      {/* Switching layer */}
      <rect x="155" y="46" width="90" height="50" rx="4" fill="#1e1b4b" stroke="#4338ca" strokeWidth="1" opacity="0.6" />
      <text x="200" y="68" textAnchor="middle" fill="#818cf8" fontSize="9">
        Switching Layer
      </text>

      {/* Filament visualization (conceptual) */}
      <line
        x1="200"
        y1="50"
        x2="200"
        y2="92"
        stroke={filamentColor}
        strokeWidth="8"
        opacity={filamentOpacity}
        strokeLinecap="round"
      />
      {state === "HRS" && (
        <circle cx="200" cy="72" r="5" fill="none" stroke="#f87171" strokeWidth="1.5" strokeDasharray="2 2" />
      )}

      {/* Bottom electrode */}
      <rect x="150" y="106" width="100" height="16" rx="3" fill="#4b5563" stroke="#6b7280" strokeWidth="1" />
      <text x="200" y="136" textAnchor="middle" fill="#9ca3af" fontSize="10">
        Bottom Electrode
      </text>

      {/* Current flow */}
      {currentFlowing && (
        <>
          <line
            x1="200"
            y1="30"
            x2="200"
            y2="75"
            stroke={currentColor}
            strokeWidth={currentWidth}
            opacity="0.8"
            strokeDasharray="6 4"
          >
            <animate
              attributeName="stroke-dashoffset"
              from={currentDirection === "forward" ? "20" : "0"}
              to={currentDirection === "forward" ? "0" : "20"}
              dur="0.6s"
              repeatCount="indefinite"
            />
          </line>
          <line
            x1="200"
            y1="105"
            x2="200"
            y2="155"
            stroke={currentColor}
            strokeWidth={currentWidth}
            opacity="0.8"
            strokeDasharray="6 4"
          >
            <animate
              attributeName="stroke-dashoffset"
              from={currentDirection === "forward" ? "20" : "0"}
              to={currentDirection === "forward" ? "0" : "20"}
              dur="0.6s"
              repeatCount="indefinite"
            />
          </line>
        </>
      )}

      {/* V_RRAM indicator */}
      <text x="280" y="72" fill={polarityColor} fontSize="14" fontWeight="bold">
        {polarityArrow}
      </text>
      <text x="300" y="68" fill={polarityColor} fontSize="10">
        V_RRAM
      </text>
      <text x="300" y="80" fill={polarityColor} fontSize="11" fontWeight="600">
        {vRram.toFixed(2)} V
      </text>

      {/* I_RRAM */}
      <text x="60" y="60" fill="#e1e4ed" fontSize="10">
        I_RRAM
      </text>
      <text x="60" y="74" fill="#4ade80" fontSize="12" fontWeight="600">
        {iRram.toFixed(1)} µA
      </text>

      {/* R_RRAM */}
      <text x="60" y="94" fill="#e1e4ed" fontSize="10">
        R_RRAM
      </text>
      <text x="60" y="108" fill="#fbbf24" fontSize="12" fontWeight="600">
        {rDisplay}
      </text>

      {/* State label */}
      <rect
        x="155"
        y="155"
        width="90"
        height="22"
        rx="4"
        fill={state === "LRS" ? "#14532d" : state === "HRS" ? "#7f1d1d" : "#374151"}
      />
      <text
        x="200"
        y="170"
        textAnchor="middle"
        fill={state === "LRS" ? "#86efac" : state === "HRS" ? "#fca5a5" : "#9ca3af"}
        fontSize="12"
        fontWeight="700"
      >
        {state}
      </text>

      {/* Compliance indicator */}
      {complianceActive && (
        <text x="340" y="170" fill="#fb923c" fontSize="10" fontWeight="600">
          ⚡ COMPLIANCE
        </text>
      )}

      {/* Operation and phase */}
      <text x="200" y="196" textAnchor="middle" fill="#8b90a5" fontSize="10">
        {operation} · {phase}
      </text>

      {/* Fidelity badge */}
      <text x="380" y="14" textAnchor="end" fill="#fb923c" fontSize="9" fontWeight="700">
        {fidelity}
      </text>
    </svg>
  );
};
