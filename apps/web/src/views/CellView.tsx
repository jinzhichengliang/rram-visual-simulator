/**
 * 1T1R Cell View Component — Visualizes 1T1R cell structure and current path.
 *
 * Displays:
 * - BL, WL, SL lines with voltages
 * - RRAM element
 * - NMOS transistor
 * - Current path animation
 * - Transistor ON/OFF state
 * - V_RRAM and I_RRAM values
 *
 * This component ONLY renders data from the selector.
 * It does NOT modify state or perform physics calculations.
 */
import React from "react";
import type { CellViewData } from "../selectors/cellSelector";

interface CellViewProps {
  data: CellViewData;
}

export const CellView: React.FC<CellViewProps> = ({ data }) => {
  const {
    wlVoltage,
    blVoltage,
    slVoltage,
    transistorOn,
    vRram,
    iRram,
    currentFlowing,
    currentDirection,
    complianceActive,
    operation,
    phase,
  } = data;

  // Visual parameters
  const width = 400;
  const height = 220;

  // Colors
  const nmColor = transistorOn ? "#4ade80" : "#6b7280";
  const wireColor = "#4b5563";
  const activeColor = currentFlowing ? "#4ade80" : "#4b5563";

  // Current animation
  const currentWidth = Math.min(3, Math.max(1, Math.abs(iRram) / 15));
  const currentAnimColor = currentDirection === "BL-to-SL" ? "#4ade80" : "#f87171";

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      {/* Background */}
      <rect width={width} height={height} fill="#0f1117" rx="8" />

      {/* BL line */}
      <line x1="40" y1="50" x2="160" y2="50" stroke={wireColor} strokeWidth="2" />
      <text x="30" y="54" fill="#9ca3af" fontSize="11" textAnchor="end">
        BL
      </text>
      <text x="30" y="66" fill={blVoltage !== 0 ? "#fbbf24" : "#6b7280"} fontSize="10" textAnchor="end">
        {blVoltage.toFixed(1)}V
      </text>

      {/* RRAM symbol */}
      <rect x="140" y="72" width="40" height="36" rx="4" fill="#1e1b4b" stroke="#4338ca" strokeWidth="1.5" />
      <text x="160" y="94" textAnchor="middle" fill="#818cf8" fontSize="10" fontWeight="600">
        RRAM
      </text>

      {/* Internal node */}
      <line x1="160" y1="50" x2="160" y2="72" stroke={wireColor} strokeWidth="2" />
      <circle cx="160" cy="50" r="3" fill={activeColor} />

      {/* NMOS transistor */}
      <line x1="160" y1="108" x2="160" y2="130" stroke={wireColor} strokeWidth="2" />
      <rect x="138" y="126" width="44" height="28" rx="4" fill="#1a1d27" stroke={nmColor} strokeWidth="1.5" />
      <text x="160" y="144" textAnchor="middle" fill={nmColor} fontSize="10" fontWeight="600">
        NMOS
      </text>

      {/* WL line */}
      <line x1="80" y1="140" x2="138" y2="140" stroke={wireColor} strokeWidth="2" />
      <text x="30" y="144" fill="#9ca3af" fontSize="11" textAnchor="end">
        WL
      </text>
      <text x="30" y="156" fill={wlVoltage !== 0 ? "#fbbf24" : "#6b7280"} fontSize="10" textAnchor="end">
        {wlVoltage.toFixed(1)}V
      </text>

      {/* Gate indicator */}
      <line x1="138" y1="140" x2="148" y2="140" stroke={nmColor} strokeWidth="2" />
      <circle cx="138" cy="140" r={transistorOn ? 4 : 3} fill={transistorOn ? "#4ade80" : "#6b7280"} />

      {/* SL line */}
      <line x1="160" y1="154" x2="260" y2="154" stroke={wireColor} strokeWidth="2" />
      <line x1="260" y1="130" x2="260" y2="154" stroke={wireColor} strokeWidth="2" />
      <text x="280" y="145" fill="#9ca3af" fontSize="11">
        SL
      </text>
      <text x="280" y="157" fill={slVoltage !== 0 ? "#fbbf24" : "#6b7280"} fontSize="10">
        {slVoltage.toFixed(1)}V
      </text>

      {/* Current flow animation */}
      {currentFlowing && (
        <>
          <line
            x1="80"
            y1="50"
            x2="160"
            y2="50"
            stroke={currentAnimColor}
            strokeWidth={currentWidth}
            opacity="0.7"
            strokeDasharray="6 4"
          >
            <animate
              attributeName="stroke-dashoffset"
              from={currentDirection === "BL-to-SL" ? "20" : "0"}
              to={currentDirection === "BL-to-SL" ? "0" : "20"}
              dur="0.6s"
              repeatCount="indefinite"
            />
          </line>
          <line
            x1="160"
            y1="50"
            x2="160"
            y2="75"
            stroke={currentAnimColor}
            strokeWidth={currentWidth}
            opacity="0.7"
            strokeDasharray="6 4"
          >
            <animate
              attributeName="stroke-dashoffset"
              from={currentDirection === "BL-to-SL" ? "20" : "0"}
              to={currentDirection === "BL-to-SL" ? "0" : "20"}
              dur="0.6s"
              repeatCount="indefinite"
            />
          </line>
          <line
            x1="160"
            y1="105"
            x2="160"
            y2="130"
            stroke={currentAnimColor}
            strokeWidth={currentWidth}
            opacity="0.7"
            strokeDasharray="6 4"
          >
            <animate
              attributeName="stroke-dashoffset"
              from={currentDirection === "BL-to-SL" ? "20" : "0"}
              to={currentDirection === "BL-to-SL" ? "0" : "20"}
              dur="0.6s"
              repeatCount="indefinite"
            />
          </line>
          <line
            x1="160"
            y1="130"
            x2="260"
            y2="130"
            stroke={currentAnimColor}
            strokeWidth={currentWidth}
            opacity="0.7"
            strokeDasharray="6 4"
          >
            <animate
              attributeName="stroke-dashoffset"
              from={currentDirection === "BL-to-SL" ? "20" : "0"}
              to={currentDirection === "BL-to-SL" ? "0" : "20"}
              dur="0.6s"
              repeatCount="indefinite"
            />
          </line>
        </>
      )}

      {/* Status indicators */}
      <rect x="240" y="30" width="70" height="20" rx="4" fill={transistorOn ? "#14532d" : "#374151"} />
      <text x="275" y="44" textAnchor="middle" fill={transistorOn ? "#86efac" : "#9ca3af"} fontSize="10" fontWeight="600">
        {transistorOn ? "NMOS ON" : "NMOS OFF"}
      </text>

      {/* V_RRAM */}
      <text x="240" y="70" fill="#e1e4ed" fontSize="10">
        V_RRAM:
      </text>
      <text x="300" y="70" fill={vRram > 0 ? "#4ade80" : vRram < 0 ? "#f87171" : "#6b7280"} fontSize="11" fontWeight="600">
        {vRram.toFixed(2)} V
      </text>

      {/* I_RRAM */}
      <text x="240" y="88" fill="#e1e4ed" fontSize="10">
        I_RRAM:
      </text>
      <text x="300" y="88" fill="#4ade80" fontSize="11" fontWeight="600">
        {iRram.toFixed(1)} µA
      </text>

      {/* Topology label */}
      <text x="200" y="188" textAnchor="middle" fill="#8b90a5" fontSize="9">
        BL → RRAM → NMOS → SL · WL → Gate
      </text>

      {/* Compliance indicator */}
      {complianceActive && (
        <text x="340" y="170" fill="#fb923c" fontSize="10" fontWeight="600">
          ⚡ COMPLIANCE
        </text>
      )}

      {/* Operation and phase */}
      <text x="200" y="206" textAnchor="middle" fill="#8b90a5" fontSize="10">
        {operation} · {phase}
      </text>
    </svg>
  );
};
