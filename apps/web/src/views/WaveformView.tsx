/**
 * Waveform View Component — Visualizes time-domain waveforms.
 *
 * Displays:
 * - V_RRAM waveform (voltage across RRAM)
 * - I_RRAM waveform (current through RRAM)
 * - R_RRAM waveform (resistance)
 * - Current frame marker
 * - Phase labels
 *
 * This component ONLY renders data from the selector.
 * It does NOT modify state or perform physics calculations.
 */
import React from "react";
import type { WaveformData } from "../selectors/waveformSelector";

interface WaveformViewProps {
  data: WaveformData;
}

export const WaveformView: React.FC<WaveformViewProps> = ({ data }) => {
  const { points, currentTimeNs } = data;

  const width = 800;
  const height = 200;
  const padding = { top: 20, right: 20, bottom: 30, left: 50 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  if (points.length === 0) {
    return (
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <rect width={width} height={height} fill="#0f1117" rx="8" />
        <text x={width / 2} y={height / 2} textAnchor="middle" fill="#8b90a5" fontSize="12">
          等待操作 — 波形将在操作后显示
        </text>
      </svg>
    );
  }

  // Calculate scales
  const timeMin = points[0].timeNs;
  const timeMax = points[points.length - 1].timeNs;
  const timeRange = timeMax - timeMin || 1;

  // Voltage scale
  const voltages = points.map((p) => p.vRram);
  const vMax = Math.max(0.5, ...voltages.map(Math.abs)) * 1.2;

  // Current scale
  const currents = points.map((p) => p.iRram);
  const iMax = Math.max(5, ...currents.map(Math.abs)) * 1.2;

  // Resistance scale
  const resistances = points.map((p) => p.resistance / 1000); // kΩ
  const rMax = Math.max(10, ...resistances) * 1.1;

  // Helper functions
  const xScale = (timeNs: number) =>
    padding.left + ((timeNs - timeMin) / timeRange) * plotWidth;
  const yScaleV = (v: number) =>
    padding.top + plotHeight / 2 - (v / vMax) * (plotHeight / 2);
  const yScaleI = (i: number) =>
    padding.top + plotHeight / 2 - (i / iMax) * (plotHeight / 2);
  const yScaleR = (r: number) =>
    padding.top + plotHeight / 2 - (r / rMax) * (plotHeight / 2);

  // Generate paths
  const vPath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xScale(p.timeNs)} ${yScaleV(p.vRram)}`)
    .join(" ");

  const iPath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xScale(p.timeNs)} ${yScaleI(p.iRram)}`)
    .join(" ");

  const rPath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xScale(p.timeNs)} ${yScaleR(p.resistance / 1000)}`)
    .join(" ");

  // Current frame marker
  const currentX = xScale(currentTimeNs);

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      {/* Background */}
      <rect width={width} height={height} fill="#0f1117" rx="8" />

      {/* Grid */}
      {[0, 1, 2, 3, 4].map((i) => {
        const y = padding.top + (plotHeight / 4) * i;
        return (
          <line
            key={i}
            x1={padding.left}
            y1={y}
            x2={width - padding.right}
            y2={y}
            stroke="#1e2030"
            strokeWidth="0.5"
          />
        );
      })}

      {/* Waveforms */}
      <path d={vPath} fill="none" stroke="#6c8cff" strokeWidth="1.5" />
      <path d={iPath} fill="none" stroke="#4ade80" strokeWidth="1.5" />
      <path d={rPath} fill="none" stroke="#fbbf24" strokeWidth="1.5" strokeDasharray="4 3" />

      {/* Current frame marker */}
      <line
        x1={currentX}
        y1={padding.top}
        x2={currentX}
        y2={padding.top + plotHeight}
        stroke="#ffffff40"
        strokeWidth="1"
        strokeDasharray="3 3"
      />

      {/* Current frame dots */}
      {points.length > 0 && (
        <>
          <circle
            cx={currentX}
            cy={yScaleV(points[points.length - 1].vRram)}
            r="4"
            fill="#6c8cff"
          />
          <circle
            cx={currentX}
            cy={yScaleI(points[points.length - 1].iRram)}
            r="4"
            fill="#4ade80"
          />
        </>
      )}

      {/* Y-axis labels */}
      <text x={padding.left - 4} y={padding.top + 4} textAnchor="end" fill="#6c8cff" fontSize="9">
        +{vMax.toFixed(1)}V
      </text>
      <text x={padding.left - 4} y={padding.top + plotHeight} textAnchor="end" fill="#6c8cff" fontSize="9">
        -{vMax.toFixed(1)}V
      </text>
      <text x={padding.left - 4} y={padding.top + plotHeight / 2 + 3} textAnchor="end" fill="#8b90a5" fontSize="9">
        0
      </text>

      {/* X-axis labels */}
      {points.length > 0 &&
        [0, Math.floor(points.length / 4), Math.floor(points.length / 2), points.length - 1].map(
          (idx) => {
            const p = points[idx];
            if (!p) return null;
            const x = xScale(p.timeNs);
            return (
              <text key={idx} x={x} y={height - 8} textAnchor="middle" fill="#8b90a5" fontSize="9">
                {p.timeNs}ns
              </text>
            );
          }
        )}

      {/* Phase labels */}
      {points.map((p, i) => {
        const x = xScale(p.timeNs);
        return (
          <text key={i} x={x} y={padding.top - 6} textAnchor="middle" fill="#6b728080" fontSize="8">
            {p.phase.substring(0, 3)}
          </text>
        );
      })}

      {/* Legend */}
      <g transform={`translate(${width - 150}, 10)`}>
        <line x1="0" y1="0" x2="10" y2="0" stroke="#6c8cff" strokeWidth="2" />
        <text x="15" y="4" fill="#8b90a5" fontSize="9">
          V_RRAM (V)
        </text>
        <line x1="0" y1="12" x2="10" y2="12" stroke="#4ade80" strokeWidth="2" />
        <text x="15" y="16" fill="#8b90a5" fontSize="9">
          I_RRAM (µA)
        </text>
        <line x1="0" y1="24" x2="10" y2="24" stroke="#fbbf24" strokeWidth="2" strokeDasharray="4 3" />
        <text x="15" y="28" fill="#8b90a5" fontSize="9">
          R (kΩ)
        </text>
      </g>
    </svg>
  );
};
