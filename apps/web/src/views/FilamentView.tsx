/**
 * Filament View Component — Visualizes the conductive filament.
 *
 * V0.5 S18: Shows the physical state of the RRAM device.
 * - F0: Conceptual visualization (connected/disconnected)
 * - F1: Parameterized visualization (gap size, filament width, temperature)
 *
 * This component ONLY renders data from the selector.
 * It does NOT modify state or perform physics calculations.
 */
import React from "react";
import type { FilamentViewData } from "../selectors/filamentSelector";

interface FilamentViewProps {
  data: FilamentViewData;
}

export const FilamentView: React.FC<FilamentViewProps> = ({ data }) => {
  const {
    gapNm,
    filamentProxy,
    temperatureK,
    filamentWidth,
    filamentOpacity,
    filamentColor,
    state,
    fidelity,
    formingDone,
    showGap,
    gapSize,
  } = data;

  const width = 400;
  const height = 220;

  // Electrode dimensions
  const electrodeWidth = 120;
  const electrodeHeight = 20;
  const electrodeX = (width - electrodeWidth) / 2;
  const topElectrodeY = 30;
  const bottomElectrodeY = height - 50;

  // Switching layer dimensions
  const layerWidth = 100;
  const layerHeight = bottomElectrodeY - topElectrodeY - electrodeHeight;
  const layerX = (width - layerWidth) / 2;
  const layerY = topElectrodeY + electrodeHeight;

  // Filament dimensions
  const filamentMaxWidth = 30;
  const filamentActualWidth = filamentMaxWidth * filamentWidth;
  const filamentX = width / 2 - filamentActualWidth / 2;

  // Gap visualization (F1 only)
  const gapHeight = showGap ? layerHeight * gapSize * 0.3 : 0;
  const gapY = layerY + layerHeight / 2 - gapHeight / 2;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      {/* Background */}
      <rect width={width} height={height} fill="#0f1117" rx="8" />

      {/* Top electrode (BL) */}
      <rect
        x={electrodeX}
        y={topElectrodeY}
        width={electrodeWidth}
        height={electrodeHeight}
        rx="3"
        fill="#4b5563"
        stroke="#6b7280"
        strokeWidth="1"
      />
      <text
        x={width / 2}
        y={topElectrodeY - 8}
        textAnchor="middle"
        fill="#9ca3af"
        fontSize="10"
      >
        Top Electrode (BL)
      </text>

      {/* Switching layer */}
      <rect
        x={layerX}
        y={layerY}
        width={layerWidth}
        height={layerHeight}
        rx="4"
        fill="#1e1b4b"
        stroke="#4338ca"
        strokeWidth="1"
        opacity="0.6"
      />
      <text
        x={width / 2}
        y={layerY + 15}
        textAnchor="middle"
        fill="#818cf8"
        fontSize="9"
      >
        Switching Layer
      </text>

      {/* Conductive filament */}
      <rect
        x={filamentX}
        y={layerY}
        width={filamentActualWidth}
        height={layerHeight}
        rx="2"
        fill={filamentColor}
        opacity={filamentOpacity}
      />

      {/* Gap visualization (F1 only) */}
      {showGap && gapHeight > 2 && (
        <>
          <rect
            x={layerX + 10}
            y={gapY}
            width={layerWidth - 20}
            height={gapHeight}
            fill="#0f1117"
            opacity="0.8"
          />
          <text
            x={width / 2}
            y={gapY + gapHeight / 2 + 3}
            textAnchor="middle"
            fill="#f87171"
            fontSize="8"
            fontWeight="600"
          >
            Gap: {gapNm?.toFixed(1)}nm
          </text>
        </>
      )}

      {/* Bottom electrode (SL) */}
      <rect
        x={electrodeX}
        y={bottomElectrodeY}
        width={electrodeWidth}
        height={electrodeHeight}
        rx="3"
        fill="#4b5563"
        stroke="#6b7280"
        strokeWidth="1"
      />
      <text
        x={width / 2}
        y={bottomElectrodeY + electrodeHeight + 15}
        textAnchor="middle"
        fill="#9ca3af"
        fontSize="10"
      >
        Bottom Electrode (SL)
      </text>

      {/* State label */}
      <text
        x={width / 2}
        y={height - 10}
        textAnchor="middle"
        fill={state === "LRS" ? "#4ade80" : state === "HRS" ? "#f87171" : "#6b7280"}
        fontSize="12"
        fontWeight="700"
      >
        {state} {formingDone ? "(Formed)" : "(Unformed)"}
      </text>

      {/* Fidelity badge */}
      <rect
        x={width - 50}
        y={10}
        width={40}
        height={18}
        rx="3"
        fill={fidelity === "F0" ? "#422006" : "#14532d"}
      />
      <text
        x={width - 30}
        y={23}
        textAnchor="middle"
        fill={fidelity === "F0" ? "#fb923c" : "#4ade80"}
        fontSize="10"
        fontWeight="700"
      >
        {fidelity}
      </text>

      {/* Observables (F1 only) */}
      {fidelity !== "F0" && (
        <g>
          <text x={20} y={30} fill="#8b90a5" fontSize="9">
            gap_nm:
          </text>
          <text x={70} y={30} fill="#e1e4ed" fontSize="9" fontWeight="600">
            {gapNm?.toFixed(2) ?? "N/A"} nm
          </text>

          <text x={20} y={45} fill="#8b90a5" fontSize="9">
            filament:
          </text>
          <text x={70} y={45} fill="#e1e4ed" fontSize="9" fontWeight="600">
            {filamentProxy?.toFixed(2) ?? "N/A"}
          </text>

          {temperatureK !== null && (
            <>
              <text x={20} y={60} fill="#8b90a5" fontSize="9">
                temp:
              </text>
              <text x={70} y={60} fill="#e1e4ed" fontSize="9" fontWeight="600">
                {temperatureK.toFixed(0)} K
              </text>
            </>
          )}
        </g>
      )}

      {/* F0 disclaimer */}
      {fidelity === "F0" && (
        <text
          x={width / 2}
          y={height - 25}
          textAnchor="middle"
          fill="#6b7280"
          fontSize="8"
          fontStyle="italic"
        >
          Conceptual visualization — not to physical scale
        </text>
      )}
    </svg>
  );
};
