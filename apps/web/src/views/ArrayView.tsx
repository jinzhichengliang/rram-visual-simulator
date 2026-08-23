/**
 * Array View Component — Visualizes 4×4 1T1R array.
 *
 * Displays:
 * - 4×4 cell grid with state colors
 * - Selected cell highlight
 * - WL/BL/SL lines with voltages
 * - Current path animation (only for selected cell with current)
 *
 * This component ONLY renders data from the selector.
 * It does NOT modify state or perform physics calculations.
 */
import React from "react";
import type { ArrayViewData } from "../selectors/arraySelector";

interface ArrayViewProps {
  data: ArrayViewData;
  onCellClick?: (row: number, col: number) => void;
}

export const ArrayView: React.FC<ArrayViewProps> = ({ data, onCellClick }) => {
  const { rows, cols, selectedRow, selectedCol, cells, wlVoltages, blVoltages, slVoltages, operation, phase } = data;

  const width = 500;
  const height = 400;
  const cellSize = 60;
  const padding = { top: 40, left: 60, right: 40, bottom: 40 };

  // Calculate grid position
  const cellX = (col: number) => padding.left + col * (cellSize + 10);
  const cellY = (row: number) => padding.top + row * (cellSize + 10);

  // State colors
  const getStateColor = (state: string) => {
    switch (state) {
      case "LRS": return "#4ade80";
      case "HRS": return "#f87171";
      case "PRISTINE": return "#6b7280";
      default: return "#6b7280";
    }
  };

  // Check if current is flowing
  const selectedCell = cells[selectedRow]?.[selectedCol];
  const currentFlowing = selectedCell && Math.abs(selectedCell.iRram) > 0.1;
  const currentDirection = selectedCell && selectedCell.iRram > 0 ? "down" : "up";

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      {/* Background */}
      <rect width={width} height={height} fill="#0f1117" rx="8" />

      {/* WL lines (horizontal, top) */}
      {Array.from({ length: rows }).map((_, row) => {
        const y = cellY(row) + cellSize / 2;
        const isSelected = row === selectedRow;
        const voltage = wlVoltages[row] || 0;

        return (
          <g key={`wl-${row}`}>
            <line
              x1={padding.left - 20}
              y1={y}
              x2={cellX(cols - 1) + cellSize}
              y2={y}
              stroke={isSelected ? "#fbbf24" : "#4b5563"}
              strokeWidth={isSelected ? 2 : 1}
              opacity={isSelected ? 1 : 0.5}
            />
            <text
              x={padding.left - 25}
              y={y + 4}
              textAnchor="end"
              fill={isSelected ? "#fbbf24" : "#8b90a5"}
              fontSize="10"
              fontWeight={isSelected ? "600" : "400"}
            >
              WL{row}
            </text>
            {isSelected && (
              <text
                x={padding.left - 25}
                y={y + 16}
                textAnchor="end"
                fill="#fbbf24"
                fontSize="9"
              >
                {voltage.toFixed(1)}V
              </text>
            )}
          </g>
        );
      })}

      {/* BL lines (vertical, right) */}
      {Array.from({ length: cols }).map((_, col) => {
        const x = cellX(col) + cellSize / 2;
        const isSelected = col === selectedCol;
        const voltage = blVoltages[col] || 0;

        return (
          <g key={`bl-${col}`}>
            <line
              x1={x}
              y1={padding.top - 20}
              x2={x}
              y2={cellY(rows - 1) + cellSize}
              stroke={isSelected ? "#22d3ee" : "#4b5563"}
              strokeWidth={isSelected ? 2 : 1}
              opacity={isSelected ? 1 : 0.5}
            />
            <text
              x={x}
              y={padding.top - 25}
              textAnchor="middle"
              fill={isSelected ? "#22d3ee" : "#8b90a5"}
              fontSize="10"
              fontWeight={isSelected ? "600" : "400"}
            >
              BL{col}
            </text>
            {isSelected && (
              <text
                x={x + 15}
                y={padding.top - 25}
                fill="#22d3ee"
                fontSize="9"
              >
                {voltage.toFixed(1)}V
              </text>
            )}
          </g>
        );
      })}

      {/* SL lines (vertical, left, shared with BL for simplicity) */}
      {Array.from({ length: cols }).map((_, col) => {
        const x = cellX(col) + cellSize / 2;
        const isSelected = col === selectedCol;
        const voltage = slVoltages[col] || 0;

        return (
          <g key={`sl-${col}`}>
            {isSelected && (
              <text
                x={x - 15}
                y={cellY(rows - 1) + cellSize + 20}
                fill="#a78bfa"
                fontSize="9"
                textAnchor="middle"
              >
                SL{col}: {voltage.toFixed(1)}V
              </text>
            )}
          </g>
        );
      })}

      {/* Cells */}
      {Array.from({ length: rows }).map((_, row) =>
        Array.from({ length: cols }).map((_, col) => {
          const cell = cells[row][col];
          const x = cellX(col);
          const y = cellY(row);
          const isSelected = row === selectedRow && col === selectedCol;

          return (
            <g
              key={`cell-${row}-${col}`}
              onClick={() => onCellClick?.(row, col)}
              style={{ cursor: onCellClick ? "pointer" : "default" }}
            >
              {/* Cell background */}
              <rect
                x={x}
                y={y}
                width={cellSize}
                height={cellSize}
                rx="4"
                fill={isSelected ? "#1e293b" : "#181c25"}
                stroke={isSelected ? "#6c8cff" : "#2e3348"}
                strokeWidth={isSelected ? 2 : 1}
              />

              {/* State indicator */}
              <circle
                cx={x + cellSize / 2}
                cy={y + cellSize / 2 - 8}
                r="8"
                fill={getStateColor(cell.state)}
                opacity={isSelected ? 1 : 0.6}
              />

              {/* State label */}
              <text
                x={x + cellSize / 2}
                y={y + cellSize / 2 + 8}
                textAnchor="middle"
                fill={isSelected ? "#e1e4ed" : "#8b90a5"}
                fontSize="9"
                fontWeight={isSelected ? "600" : "400"}
              >
                {cell.state}
              </text>

              {/* Transistor indicator */}
              {cell.transistorOn && (
                <circle
                  cx={x + cellSize - 8}
                  cy={y + 8}
                  r="3"
                  fill="#4ade80"
                />
              )}

              {/* Selection highlight */}
              {isSelected && (
                <rect
                  x={x - 2}
                  y={y - 2}
                  width={cellSize + 4}
                  height={cellSize + 4}
                  rx="6"
                  fill="none"
                  stroke="#6c8cff"
                  strokeWidth="1"
                  strokeDasharray="4 2"
                  opacity="0.5"
                />
              )}
            </g>
          );
        })
      )}

      {/* Current flow animation (only for selected cell) */}
      {currentFlowing && selectedCell && (
        <g>
          {/* BL to cell */}
          <line
            x1={cellX(selectedCol) + cellSize / 2}
            y1={padding.top - 20}
            x2={cellX(selectedCol) + cellSize / 2}
            y2={cellY(selectedRow)}
            stroke={currentDirection === "down" ? "#4ade80" : "#f87171"}
            strokeWidth="2"
            strokeDasharray="6 4"
            opacity="0.8"
          >
            <animate
              attributeName="stroke-dashoffset"
              from={currentDirection === "down" ? "20" : "0"}
              to={currentDirection === "down" ? "0" : "20"}
              dur="0.6s"
              repeatCount="indefinite"
            />
          </line>

          {/* Cell to SL */}
          <line
            x1={cellX(selectedCol) + cellSize / 2}
            y1={cellY(selectedRow) + cellSize}
            x2={cellX(selectedCol) + cellSize / 2}
            y2={cellY(rows - 1) + cellSize + 10}
            stroke={currentDirection === "down" ? "#4ade80" : "#f87171"}
            strokeWidth="2"
            strokeDasharray="6 4"
            opacity="0.8"
          >
            <animate
              attributeName="stroke-dashoffset"
              from={currentDirection === "down" ? "20" : "0"}
              to={currentDirection === "down" ? "0" : "20"}
              dur="0.6s"
              repeatCount="indefinite"
            />
          </line>
        </g>
      )}

      {/* Operation info */}
      <text x={width / 2} y={height - 10} textAnchor="middle" fill="#8b90a5" fontSize="10">
        {operation} · {phase} · Selected: ({selectedRow}, {selectedCol})
      </text>
    </svg>
  );
};
