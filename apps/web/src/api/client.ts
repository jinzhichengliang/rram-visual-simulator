/**
 * API Client — Communicates with Python backend.
 *
 * Provides typed API calls to the simulation backend.
 */
import type { FrameState, OperationType } from "../../../../packages/contracts/types";

const API_BASE = "http://localhost:8000";

export async function executeOperation(
  operation: OperationType,
  target: { row: number; col: number }
): Promise<FrameState[]> {
  const response = await fetch(`${API_BASE}/api/operation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ operation, target }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

export async function resetSimulation(): Promise<void> {
  const response = await fetch(`${API_BASE}/api/reset`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
}

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  return response.json();
}
