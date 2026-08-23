/**
 * Global Store — Manages simulation state and frame history.
 *
 * This is the single source of truth for the frontend application.
 * It manages:
 * - Frame history (immutable list of FrameStates)
 * - Current frame cursor (which frame is being displayed)
 * - Simulation state (running, paused, etc.)
 */
import { useState, useCallback } from "react";
import type { FrameState } from "../../../../packages/contracts/types";

export interface SimulationStore {
  frames: FrameState[];
  currentFrameIndex: number;
  isRunning: boolean;
}

export function useSimulationStore() {
  const [frames, setFrames] = useState<FrameState[]>([]);
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [isRunning, setIsRunning] = useState(false);

  const addFrame = useCallback((frame: FrameState) => {
    setFrames((prev) => [...prev, frame]);
    setCurrentFrameIndex((prev) => prev + 1);
  }, []);

  const setCurrentFrame = useCallback((index: number) => {
    if (index >= 0 && index < frames.length) {
      setCurrentFrameIndex(index);
    }
  }, [frames.length]);

  const reset = useCallback(() => {
    setFrames([]);
    setCurrentFrameIndex(0);
    setIsRunning(false);
  }, []);

  const currentFrame = frames[currentFrameIndex] || null;

  return {
    frames,
    currentFrameIndex,
    currentFrame,
    isRunning,
    addFrame,
    setCurrentFrame,
    setIsRunning,
    reset,
  };
}
